"""On-demand official source adapters, normalized without a country-sized import."""
import re
from datetime import date
import httpx

NYC_URL = 'https://data.cityofnewyork.us/resource/usep-8jbt.json'

def nyc_sales(location, on=None):
    address = (location.get('address') or {}).get('address') or {}
    postcode = str(address.get('postcode', ''))
    city = ' '.join(str(address.get(k, '')) for k in ('city', 'state', 'county')).lower()
    if address.get('country_code') != 'us' or 'new york' not in city or not re.fullmatch(r'\d{5}', postcode):
        return [], None
    on = on or date.today()
    response = httpx.get(NYC_URL, params={
        '$where': f"zip_code='{postcode}' AND sale_price > 10000 AND sale_date < '{on.isoformat()}T00:00:00'",
        '$order': 'sale_date DESC', '$limit': 400}, timeout=15)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list): raise ValueError('Unexpected official sales response')
    records = []
    for row in rows:
        try:
            price = float(row['sale_price'].replace(',', ''))
            area = float(row.get('gross_square_feet', '0').replace(',', '')) * .09290304
            units = int(row.get('total_units', '0'))
        except (ValueError, KeyError, TypeError): continue
        # A multiple-apartment building sale is not a household comparable.
        if price <= 10000 or units != 1 or not str(row.get('building_class_category', '')).startswith('01 '): continue
        identity = '/'.join(str(row.get(k, '')) for k in ('borough', 'block', 'lot'))
        records.append({'type': 'registered_transaction', 'price': price, 'currency': 'USD', 'period': None,
            'area_sqm': area if area > 0 else None, 'address': row.get('address'),
            'property_identity': 'NYC-BBL/' + identity, 'property_type': 'one-family dwelling',
            'bedrooms': None, 'latitude': None, 'longitude': None,
            'source_url': NYC_URL, 'source_host': 'data.cityofnewyork.us',
            'source_date': row.get('sale_date', '')[:10], 'reliability': .95,
            'verified_transaction': True, 'classification_basis': 'NYC Department of Finance published rolling sales; arms-length status is not guaranteed.',
            'original_record': row, 'location_scope': 'same postal code; exact distance not established'})
    return records, {'url': NYC_URL, 'status': 'official sales fetched', 'rows_received': len(rows),
        'usable_one_family_records': len(records), 'postcode': postcode,
        'limits': 'Rolling sales, not complete historical registry. Non-arms-length sales may remain. Individual coordinates unavailable.'}
