from datetime import date
import re,json,time,urllib.request,urllib.parse,gzip,csv,io,threading
from functools import lru_cache
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
import httpx
from fastapi.staticfiles import StaticFiles
from .repository import Repository, ROOT
from .models import ValuationRequest
from .valuation import value_property
from .evidence import EvidenceDiscovery
from pydantic import BaseModel, Field
from .intelligence import Intelligence, IntelligenceRequest
from .geometry import MeasurementRequest, measure

repository=Repository()
discovery=EvidenceDiscovery(repository)
intelligence=Intelligence(discovery, ROOT)
app=FastAPI(title='AVM · residential evidence')
@app.post('/measurements')
def measurement(request:MeasurementRequest):
    try:result=measure(request)
    except ValueError as exc:raise HTTPException(422,str(exc))
    path=ROOT/'data/measurements';path.mkdir(exist_ok=True)
    (path/(result['measurement_id']+'.json')).write_text(json.dumps(result))
    return result

@app.get('/measurements/{key}')
def measurement_receipt(key:str):
    if not re.fullmatch('[a-f0-9]{64}',key):raise HTTPException(404)
    path=ROOT/'data/measurements'/(key+'.json')
    if not path.exists():raise HTTPException(404)
    return json.loads(path.read_text())
class EvidenceRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

@app.post('/evidence/discover')
def discover_evidence(request: EvidenceRequest):
    return discovery.discover(request.latitude, request.longitude)

@app.post('/intelligence')
def property_intelligence(request: IntelligenceRequest):
    if request.property_id and request.property_id not in repository.properties:
        raise HTTPException(404, 'Property not found')
    if request.property_id:
        target=repository.properties[request.property_id]
        from .valuation import distance_m
        if distance_m(request.latitude,request.longitude,target.latitude,target.longitude)>100:
            raise HTTPException(422,'Selected profile does not match this map location')
        if request.currency != target.currency:
            raise HTTPException(422,'Currency must match the supported property currency')
    result=intelligence.run(request)
    if request.property_id:
        estimate=valuation(ValuationRequest(property_id=request.property_id,valuation_date=date.today(),area_sqm=request.area_sqm))
        result['transaction_valuation']=estimate
        result.update({k:estimate[k] for k in ('status','estimated_value','lower_bound','upper_bound','forecasts')})
        result['confidence']=estimate['confidence_label']
        result['confidence_score']=estimate['confidence']
        result['confidence_reason']='Supported transaction model; web asking/rental indications are shown separately and do not create independent model votes.'
        result['evidence_scope']=estimate['evidence_scope']
        # Persist the final response including transaction receipt linkage.
        import hashlib
        result.pop('receipt_id',None)
        key=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
        result['receipt_id']=key
        (ROOT/'data/intelligence-receipts'/(key+'.json')).write_text(json.dumps(result))
    return result

@app.get('/intelligence/{key}')
def intelligence_receipt(key:str):
    if not re.fullmatch('[a-f0-9]{64}',key): raise HTTPException(404)
    path=ROOT/'data/intelligence-receipts'/(key+'.json')
    if not path.exists(): raise HTTPException(404)
    return json.loads(path.read_text())
@app.get('/health')
def health(): return {'status':'ok','storage':'postgis' if repository.url else 'snapshot'}
@app.get('/metadata')
def metadata(): return {**{k:v for k,v in repository.snapshot.items() if k not in ('properties','sales')},'property_count':len(repository.properties),'data_version':repository.version,'historical_records_archived':sum(a['rows'] for a in repository.archives),'history_start':'1990-01' if repository.archives else '2017-01'}
@app.get('/coverage')
def coverage(): return json.loads((ROOT/'data/coverage.json').read_text())
@app.get('/benchmark')
def benchmark():
    path=ROOT/'data/benchmark.json'
    return json.loads(path.read_text()) if path.exists() else {'status':'not yet evaluated'}
@lru_cache(maxsize=512)
def official_tile(z,x,y):
    # TLS remains verified. Relay only fixed official basemap URLs, not arbitrary destinations.
    response=httpx.get(f'https://www.onemap.gov.sg/maps/tiles/Default/{z}/{x}/{y}.png',timeout=20)
    response.raise_for_status()
    if not response.headers.get('content-type','').startswith('image/png'):raise ValueError('Unexpected tile format')
    return response.content
@app.get('/basemap/sg/{z}/{x}/{y}.png')
def basemap(z:int,x:int,y:int):
    if not 9<=z<=18 or not 0<=x<2**z or not 0<=y<2**z:raise HTTPException(404)
    try:return Response(official_tile(z,x,y),media_type='image/png',headers={'Cache-Control':'public, max-age=14400'})
    except Exception:raise HTTPException(502,'Official basemap temporarily unavailable')

@lru_cache(maxsize=1024)
def osm_tile(z,x,y):
    response=httpx.get(f'https://tile.openstreetmap.org/{z}/{x}/{y}.png',timeout=15,
        headers={'User-Agent':'AVM-ResearchPreview/1.0 (https://github.com/Intellora-ai/AVM)'})
    response.raise_for_status()
    if not response.headers.get('content-type','').startswith('image/png'):raise ValueError('Unexpected tile format')
    return response.content

@app.get('/basemap/world/{z}/{x}/{y}.png')
def world_basemap(z:int,x:int,y:int):
    if not 0<=z<=19 or not 0<=x<2**z or not 0<=y<2**z:raise HTTPException(404)
    try:return Response(osm_tile(z,x,y),media_type='image/png',headers={'Cache-Control':'public, max-age=604800'})
    except Exception:raise HTTPException(502,'OpenStreetMap basemap temporarily unavailable')
@app.get('/source-records/{sale_id}')
def source_record(sale_id:str):
    if not re.fullmatch(r'(hdb|d_[a-f0-9]{32})-row-[0-9]+',sale_id):raise HTTPException(404)
    prefix,number=sale_id.rsplit('-row-',1);line=int(number)
    if prefix=='hdb':
        digest=repository.snapshot['source_hashes']['sales'];source=repository.snapshot['sources']['sales'];filename='sales-'+digest+'.csv.gz'
    else:
        entry=next((a for a in repository.archives if a['dataset_id']==prefix),None)
        if entry is None:raise HTTPException(404)
        digest=entry['sha256'];source=entry['source'];filename=entry['file']
    path=ROOT/'data'/filename
    if not path.exists():raise HTTPException(404)
    with gzip.open(path,'rt') as stream:
        for n,row in enumerate(csv.DictReader(stream),2):
            if n==line:return {'data_version':repository.version,'source_hash':digest,'csv_row':line,'source':source,'original_record':row}
    raise HTTPException(404)
last_place_request=0.
place_lock=threading.Lock()
@lru_cache(maxsize=256)
def fetch_places(query):
    global last_place_request
    # User-triggered address search only; respect Nominatim's one request/second policy.
    with discovery.lock:
        delay=1-(time.monotonic()-discovery.last_request)
        if delay>0: time.sleep(delay)
        discovery.last_request=time.monotonic()
        url='https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':query,'format':'jsonv2','limit':5})
        req=urllib.request.Request(url,headers={'User-Agent':'AVM-ResearchPreview/1.0 (https://github.com/Intellora-ai/AVM)'})
        with urllib.request.urlopen(req,timeout=15) as response: return json.load(response)
@app.get('/places')
def places(q:str):
    if not 3<=len(q)<=200: raise HTTPException(422,'Enter an address with 3–200 characters')
    try: return fetch_places(q)
    except Exception: raise HTTPException(503,'Global address lookup is currently unavailable. Navigate the map or search supported properties.')
@app.get('/properties')
def properties(q:str='',limit:int=Query(default=20000,ge=1,le=20000)):
    return [p for p in repository.properties.values() if q.lower() in (p.address+' '+p.property_id+' '+p.property_type).lower()][:limit]
@app.post('/valuations')
def valuation(request:ValuationRequest):
    target=repository.properties.get(request.property_id)
    if target is None: raise HTTPException(404,'Property not found')
    if request.valuation_date>date.today(): raise HTTPException(422,'Use a current or historical valuation date')
    # Full local sample calibrates the market; candidate selection also uses PostGIS.
    nearby=repository.nearby(target,request.valuation_date)
    archival=repository.historical_sales(target.neighbourhood,target.property_type)
    history=[s for s in archival+repository.groups.get((target.neighbourhood,target.property_type),[]) if s.property_id==target.property_id and s.sale_date<request.valuation_date]
    if request.area_sqm is not None:
        target=target.model_copy(update={'area_sqm':request.area_sqm})
    elif history:
        from statistics import median
        target=target.model_copy(update={'area_sqm':median(s.area_sqm for s in history)})
    else:
        target=target.model_copy(update={'area_sqm':None})
    market_sales=archival+repository.groups.get((target.neighbourhood,target.property_type),[])
    result=value_property(target,market_sales,request.valuation_date,candidates=[s for s in nearby+archival if s.property_type==target.property_type],data_version=repository.version,data_date=date.fromisoformat(repository.snapshot['data_date']))
    result.historical_transactions=history
    result.input_assumptions=['Representative block/type area from strictly earlier records.' if request.area_sqm is None else 'Area supplied by user.','Historical estimates are reconstructed from this snapshot, not proof of what was known on that date.']
    result.model_training_data_version=repository.snapshot['data_version']
    from .ml import apply_challenger
    result=apply_challenger(result,request,history)
    return repository.save(result)
@app.get('/valuations/{key}')
def receipt(key:str):
    if not re.fullmatch('[a-f0-9]{64}',key): raise HTTPException(404)
    value=repository.receipt(key)
    if value is None: raise HTTPException(404)
    return value
if (ROOT/'frontend/dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'frontend/dist',html=True),name='frontend')
