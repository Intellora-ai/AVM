"""Small on-demand OSM outline query, not a global building/parcel import."""
import hashlib,json,time
from datetime import datetime,timezone
import httpx
from .geometry import MeasurementRequest,measure

def fetch_footprints(latitude,longitude,root):
    directory=root/'data/footprint-cache';directory.mkdir(exist_ok=True)
    key=hashlib.sha256(f'{latitude:.6f},{longitude:.6f}|osm-1'.encode()).hexdigest()
    path=directory/(key+'.json')
    if path.exists() and time.time()-path.stat().st_mtime<86400:return {**json.loads(path.read_text()),'cache_hit':True}
    query=f'[out:json][timeout:8];way["building"](around:125,{latitude},{longitude});out meta geom;'
    try:
        with httpx.stream('POST','https://overpass-api.de/api/interpreter',data={'data':query},timeout=12,headers={'User-Agent':'AVM-ResearchPreview/1.0 (https://github.com/Intellora-ai/AVM)'}) as response:
            response.raise_for_status();body=bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body)>2000000:raise ValueError('Footprint response exceeds limit')
        payload=json.loads(body);features=[]
        for element in payload.get('elements',[])[:100]:
            points=[(p['lon'],p['lat']) for p in element.get('geometry',[])]
            if len(points)<4 or len(points)>200 or points[0]!=points[-1]:continue
            source=f'https://www.openstreetmap.org/way/{element["id"]}'
            try:metrics=measure(MeasurementRequest(coordinates=points,source=source))
            except ValueError:continue
            features.append({'type':'Feature','geometry':metrics['geometry'],'properties':{'id':str(element['id']),'source':source,'source_version':element.get('version'),'source_edit_date':element.get('timestamp'),'tags':element.get('tags',{}),'area_sqm':metrics['area_sqm'],'area_sqft':metrics['area_sqft'],'area_kind':'building footprint','verified_parcel':False}})
        result={'status':'ok' if features else 'no mapped footprints','type':'FeatureCollection','features':features,'cache_hit':False,'source':'OpenStreetMap / Overpass','license':'ODbL','retrieved_at':datetime.now(timezone.utc).isoformat(),'limits':'Building outlines only; no legal parcels, floor area, corner frontage or survey accuracy is inferred.'}
        from .intelligence import save_json
        save_json(path,result);return result
    except (httpx.HTTPError,ValueError,KeyError,TypeError):
        return {'status':'source unavailable','type':'FeatureCollection','features':[],'cache_hit':False,'source':'OpenStreetMap / Overpass','limits':'Draw or import an outline instead. No boundary was inferred.'}
