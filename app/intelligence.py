"""Small, deterministic web-evidence pipeline; no paid inference/search dependency.

Generic webpages can establish asking/rental evidence, never verified sales.
Market-value outputs require separately validated transaction adapters.
"""
import hashlib
import ipaddress
import json
import math
import socket
import statistics
import tempfile
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
import httpx
from pydantic import BaseModel, Field, model_validator
from .models import normalize_floor_area

VERSION = 'web-evidence-2'
RELIABILITY = {'registered_transaction': .95, 'closed_sale': .8,
    'asking_price': .45, 'rental_price': .45, 'auction': .35,
    'historical_asking_price': .25, 'historical_rental_price': .25,
    'government_assessment': .65, 'external_estimate': .3, 'unknown': .1}

def save_json(path, payload):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        json.dump(payload, stream)
        temporary = Path(stream.name)
    temporary.replace(path)

class IntelligenceRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str = Field(default='', max_length=300)
    property_type: str = Field(default='residential', max_length=80)
    area_sqm: float | None = Field(default=None, gt=0, le=100000)
    area_sqft: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: float | None = Field(default=None, ge=0, le=100)
    land_area_sqm: float | None = Field(default=None, gt=0)
    year_built: int | None = Field(default=None, ge=1000, le=2100)
    condition: str | None = Field(default=None, max_length=100)
    currency: str = Field(default='USD', pattern='^[A-Z]{3}$')
    source_urls: list[str] = Field(default_factory=list, max_length=8)
    property_id: str | None = Field(default=None, max_length=100)
    annual_gross_yield: float | None = Field(default=None, ge=.005, le=.3)
    @model_validator(mode='after')
    def normalize_area(self):
        self.area_sqm=normalize_floor_area(self.area_sqm,self.area_sqft,100000)
        return self

class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.parts = []; self.documents = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type', '').lower() == 'application/ld+json':
            self.active = True; self.parts = []
    def handle_data(self, data):
        if self.active: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            try: self.documents.append(json.loads(''.join(self.parts)))
            except (ValueError, TypeError): pass
            self.active = False

def nodes(document):
    if isinstance(document, list):
        for item in document: yield from nodes(item)
    elif isinstance(document, dict):
        yield document
        for value in document.values():
            if isinstance(value, (list, dict)): yield from nodes(value)

def number(value):
    if isinstance(value, dict): value = value.get('value')
    try:
        value = float(value)
        return value if math.isfinite(value) and value > 0 else None
    except (ValueError, TypeError): return None

def canonical_url(url):
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, '', ''))

def extract(html, url, retrieved_at):
    parser = StructuredData(); parser.feed(html)
    records = []
    for document in parser.documents:
        for node in nodes(document):
            kind = node.get('@type', '')
            kinds = kind if isinstance(kind, list) else [kind]
            if not set(kinds) & {'Apartment', 'House', 'Residence', 'SingleFamilyResidence', 'RealEstateListing', 'Product'}: continue
            offers = node.get('offers', [])
            if isinstance(offers, dict): offers = [offers]
            if not isinstance(offers, list): continue
            for offer in offers:
                if not isinstance(offer, dict): continue
                price = number(offer.get('price'))
                specification = offer.get('priceSpecification') or {}
                if isinstance(specification, list): specification = next((s for s in specification if isinstance(s, dict)), {})
                if not isinstance(specification, dict): specification = {}
                price = price or number(specification.get('price'))
                currency = offer.get('priceCurrency') or specification.get('priceCurrency')
                if not price or not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha(): continue
                # Products need an explicit residential identity; avoid ordinary retail prices.
                item = node.get('itemOffered', node.get('about', node))
                if not isinstance(item, dict): item = node
                types = item.get('@type', [])
                types = types if isinstance(types, list) else [types]
                if 'Product' in kinds and not set(types) & {'Apartment', 'House', 'Residence', 'SingleFamilyResidence'}: continue
                function = str(offer.get('businessFunction', ''))
                rental = function.endswith('LeaseOut') or specification.get('unitText') in ('MONTH', 'month', 'monthly')
                evidence_type = 'rental_price' if rental else 'asking_price'
                availability = str(offer.get('availability', '')).rsplit('/', 1)[-1]
                expired = availability in ('SoldOut', 'Discontinued', 'OutOfStock')
                try: expired = expired or date.fromisoformat(str(offer.get('validThrough', ''))[:10]) < date.today()
                except ValueError: pass
                if expired: evidence_type = 'historical_rental_price' if rental else 'historical_asking_price'
                if str(offer.get('category', node.get('category', ''))).lower() == 'auction': evidence_type = 'auction'
                unit = str(specification.get('unitText', '')).lower()
                # No unspecified rental period is assumed to mean monthly.
                period = 'month' if unit in ('month', 'monthly') else 'year' if unit in ('year', 'annual', 'yearly') else None
                floor = item.get('floorSize', node.get('floorSize'))
                area = number(floor)
                if isinstance(floor, dict):
                    units = str(floor.get('unitCode', floor.get('unitText', ''))).lower()
                    if units in ('ftk', 'sqft', 'ft2', 'square feet') and area: area *= .09290304
                    elif units not in ('mtk', 'm2', 'sqm', 'square metres', 'square meters'): area = None
                address = item.get('address', node.get('address'))
                if isinstance(address, dict): address = ', '.join(str(address[k]) for k in ('streetAddress', 'addressLocality', 'postalCode', 'addressCountry') if address.get(k))
                geo = item.get('geo', node.get('geo')) or {}
                if not isinstance(geo, dict): geo = {}
                source = canonical_url(url)
                identity = str(address or item.get('@id') or source)
                record = {'type': evidence_type, 'price': price, 'currency': currency.upper(), 'period': period,
                    'property_type': 'apartment' if 'Apartment' in types else 'house' if set(types)&{'House','SingleFamilyResidence'} else 'unknown',
                    'area_sqm': area, 'address': address, 'property_identity': identity,
                    'bedrooms': number(item.get('numberOfBedrooms')), 'latitude': geo.get('latitude'), 'longitude': geo.get('longitude'),
                    'source_url': source, 'source_host': urlsplit(source).hostname,
                    'retrieved_at': retrieved_at, 'source_date': node.get('datePosted'),
                    'reliability': RELIABILITY[evidence_type], 'verified_transaction': False,
                    'classification_basis': 'Published structured offer; sale completion is not established.'}
                record['evidence_id'] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
                records.append(record)
    return records

def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Only public HTTPS source URLs are supported')
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Local/private network sources are not supported')
    return url

def fetch_page(url):
    # TLS verified; redirects individually checked; no supplied cookies/auth; bounded body.
    for _ in range(4):
        public_url(url)
        with httpx.stream('GET', url, headers={'User-Agent': 'AVM-ResearchPreview/1.0 (https://github.com/Intellora-ai/AVM)'}, timeout=12, follow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers['location']); continue
            response.raise_for_status()
            if 'text/html' not in response.headers.get('content-type', ''): raise ValueError('Source is not an HTML page')
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000: raise ValueError('Source page exceeds 2 MB')
            return bytes(body).decode('utf-8', errors='replace'), url
    raise ValueError('Too many redirects')

def deduplicate(records):
    unique = {}; duplicates = []
    for record in records:
        # Same identity/type/price is one observation even if syndicated to another host.
        identity = ' '.join(record['property_identity'].lower().split())
        key = (identity, record['type'], record['currency'], record.get('source_date') if record['type'] == 'registered_transaction' else None)
        if key in unique:
            duplicates.append({'evidence_id': record['evidence_id'], 'duplicate_of': unique[key]['evidence_id']})
        else: unique[key] = record
    return list(unique.values()), duplicates

def signals_for(request, records):
    from .valuation import distance_m
    eligible = []; rejected = []
    for r in records:
        reason = None
        if r['currency'] != request.currency: reason = 'Currency differs; no implicit FX conversion.'
        elif request.property_type not in ('house','apartment') or r.get('property_type') != request.property_type: reason = 'Comparable residential type is unconfirmed or differs.'
        elif not request.area_sqm or not r['area_sqm']: reason = 'Target/source floor area unavailable.'
        elif min(request.area_sqm, r['area_sqm']) / max(request.area_sqm, r['area_sqm']) < .65: reason = 'Floor areas are insufficiently similar.'
        try:
            lat,lon=float(r['latitude']),float(r['longitude'])
            if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError('Invalid coordinates')
            distance = distance_m(request.latitude, request.longitude, lat, lon)
            if distance > 2000: reason = 'Outside the 2 km comparison radius.'
        except (TypeError, ValueError): reason = 'Comparable coordinates unavailable; location relevance unconfirmed.'
        if not reason:
            try:
                age = (date.today() - date.fromisoformat(str(r['source_date'])[:10])).days
                if age < 0 or age > 180: reason = 'Listing date is future or older than 180 days.'
            except (TypeError, ValueError): reason = 'Listing date unavailable; freshness unconfirmed.'
        if reason: rejected.append({'evidence_id': r['evidence_id'], 'reason': reason}); continue
        similarity = min(request.area_sqm, r['area_sqm']) / max(request.area_sqm, r['area_sqm'])
        weight = r['reliability'] * similarity * math.exp(-distance / 1500) * math.exp(-age / 180)
        if r['type'] not in ('asking_price', 'rental_price'):
            rejected.append({'evidence_id': r['evidence_id'], 'reason': 'Official transactions require a separately validated market adapter.'}); continue
        eligible.append({**r, 'weight': weight, 'distance_m': round(distance), 'similarity': similarity})
    signals = []
    for kind in ('asking_price', 'rental_price'):
        # One vote per property and domain; repeated listings cannot manufacture confidence.
        group = list({r['property_identity']: r for r in eligible if r['type'] == kind}.values())
        independent_properties = len({r['property_identity'] for r in group})
        hosts = len({r['source_host'] for r in group})
        if independent_properties < 3 or hosts < 2: continue
        values = []
        for r in group:
            value = r['price'] / r['area_sqm'] * request.area_sqm
            if kind == 'rental_price':
                if request.annual_gross_yield is None or r['period'] not in ('month', 'year'): continue
                value *= (12 if r['period'] == 'month' else 1) / request.annual_gross_yield
            values.append((value, r['weight'], r['evidence_id']))
        if len(values) < 3: continue
        centre = sum(v*w for v,w,_ in values) / sum(w for _,w,_ in values)
        signals.append({'method': 'listing market indication' if kind == 'asking_price' else 'gross rental/yield indication',
            'value': round(centre), 'observed_low': round(min(v for v,_,_ in values)), 'observed_high': round(max(v for v,_,_ in values)),
            'evidence_ids': [id for _,_,id in values], 'property_count': independent_properties, 'source_hosts': hosts,
            'assumption': 'Asking prices are not achieved sale prices.' if kind == 'asking_price' else f'User-assumed gross annual yield {request.annual_gross_yield:.2%}; expenses excluded.',
            'validated': False})
    disagreement = None
    if len(signals) >= 2:
        values = [s['value'] for s in signals]
        disagreement = (max(values) - min(values)) / statistics.median(values)
    return signals, eligible, rejected, disagreement

class Intelligence:
    def __init__(self, discovery, root):
        self.discovery = discovery; self.root = Path(root)
    def run(self, request):
        location = self.discovery.discover(request.latitude, request.longitude)
        from .integrations import search_address
        resolved=location.get('address') or {}
        parts=resolved.get('address') or {}
        address=request.address if request.address and request.address!='Selected map location' else resolved.get('display_name','')
        search=search_address(address,parts.get('neighbourhood',parts.get('suburb','')))
        records = []; source_results = []
        now = datetime.now(timezone.utc).isoformat()
        directory = self.root / 'data/web-evidence'; directory.mkdir(parents=True, exist_ok=True)
        from .sources import nyc_sales
        try:
            address_parts = ((location.get('address') or {}).get('address') or {})
            official_key = hashlib.sha256(('nyc|' + json.dumps(address_parts,sort_keys=True) + '|' + date.today().isoformat()).encode()).hexdigest()
            official_cache = directory / (official_key + '.json')
            official_hit = official_cache.exists() and datetime.now(timezone.utc).timestamp() - official_cache.stat().st_mtime < 21600
            if official_hit:
                saved = json.loads(official_cache.read_text())
                official, source_status = saved['records'], saved['source']
                official_retrieved_at = saved['retrieved_at']
            else:
                official, source_status = nyc_sales(location)
                official_retrieved_at = now
                if source_status:
                    save_json(official_cache, {'records': official, 'source': source_status, 'retrieved_at': now})
            for record in official:
                record['retrieved_at'] = official_retrieved_at
                record['evidence_id'] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
            records.extend(official)
            if source_status: source_results.append({**source_status, 'cache_hit': official_hit})
        except (httpx.HTTPError, ValueError, OSError):
            source_results.append({'url': 'https://data.cityofnewyork.us/resource/usep-8jbt.json', 'status': 'official source unavailable'})
        for url in dict.fromkeys(request.source_urls):
            try:
                cache_key = hashlib.sha256(url.encode()).hexdigest()
                cache = directory / (cache_key + '.json')
                hit = cache.exists() and datetime.now(timezone.utc).timestamp() - cache.stat().st_mtime < 21600
                if hit: payload = json.loads(cache.read_text())
                else:
                    html, resolved = fetch_page(url)
                    digest = hashlib.sha256(html.encode()).hexdigest()
                    # Original bounded response retained by digest, never rendered as HTML.
                    original = directory / (digest + '.html')
                    if not original.exists(): original.write_text(html)
                    payload = {'records': extract(html, resolved, now), 'content_hash': digest, 'retrieved_at': now}
                    save_json(cache, payload)
                records.extend(payload['records'])
                source_results.append({'url': url, 'status': 'extracted' if payload['records'] else 'no usable structured residential offers', 'cache_hit': hit, 'content_hash': payload['content_hash'], 'retrieved_at': payload['retrieved_at']})
            except (httpx.HTTPError, ValueError, OSError) as exc:
                source_results.append({'url': url, 'status': 'unavailable', 'error': type(exc).__name__})
        unique, duplicates = deduplicate(records)
        signals, eligible, rejected, disagreement = signals_for(request, unique)
        result = {'status': 'insufficient evidence', 'estimated_value': None, 'lower_bound': None, 'upper_bound': None,
            'confidence': 'unavailable', 'confidence_score': None, 'confidence_reason': 'No independently validated transaction valuation for this resolved property. Web offers are supporting signals only.',
            'property': request.model_dump(), 'location_evidence': location, 'evidence': unique,
            'duplicates': duplicates, 'eligible_comparables': eligible, 'rejected_evidence': rejected,
            'signals': signals, 'signal_disagreement': disagreement,
            'historical_value': None, 'forecasts': [],
            'source_results': source_results, 'web_search':search,'valuation_date': date.today().isoformat(), 'retrieved_at': now,
            'model_version': VERSION, 'data_version': self.discovery.repository.version,
            'limitations': ['Automatic search requires a configured Brave Search key. Search snippets are discovery links, not verified prices. Only supplied URLs are fetched for structured extraction.',
                'No rental yield, local appreciation rate or transaction completion is inferred from an advertisement.',
                'Signal ranges describe observed dispersion, not calibrated valuation intervals.',
                'Nearby block/type choices require explicit selection; they do not resolve an individual apartment.']}
        if disagreement is not None and disagreement > .2:
            result['confidence_reason'] += ' Supporting signals disagree by more than 20%.'
        key = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        result['receipt_id'] = key
        receipts = self.root / 'data/intelligence-receipts'; receipts.mkdir(parents=True, exist_ok=True)
        save_json(receipts / (key + '.json'), result)
        return result
