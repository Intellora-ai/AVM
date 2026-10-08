from app.integrations import search_address,imagery,_cache
from app.footprints import fetch_footprints
from app.main import app
from fastapi.testclient import TestClient

def test_missing_keys_fallback_no_invented_search(monkeypatch):
    for name in ('BRAVE_SEARCH_API_KEY','GOOGLE_MAPS_API_KEY','GOOGLE_MAPS_SERVER_KEY','GOOGLE_MAPS_BROWSER_KEY'):monkeypatch.delenv(name,raising=False)
    assert search_address('10 Example Street')['results']==[]
    value=imagery(1,2)
    assert value['street_view']=='not configured' and 'three_d_enabled' not in value
    assert 'OpenStreetMap' in value['fallbacks']

def test_brave_queries_rank_deduplicate_and_cache(monkeypatch):
    monkeypatch.setenv('BRAVE_SEARCH_API_KEY','unit-test-key');_cache.clear();calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'web':{'results':[{'url':'https://example.com/house','title':'Property','description':'An advertisement'},{'url':'https://example.com/house?tracking=1','title':'Duplicate'},{'url':'file:///etc/passwd','title':'Bad'}]}}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,url,params,headers):calls.append(params['q']);return Response()
    monkeypatch.setattr('app.integrations.httpx.Client',Client)
    result=search_address('10 Example Street','Sector 9')
    assert len(calls)==4 and len(result['results'])==1
    assert len(result['results'][0]['queries'])==4
    assert result['results'][0]['evidence_type']=='search result; unverified'
    assert search_address('10 Example Street','Sector 9')['cache_hit'] and len(calls)==4

def test_street_view_metadata_hides_server_key(monkeypatch):
    monkeypatch.setenv('GOOGLE_MAPS_SERVER_KEY','private-server-key')
    monkeypatch.setenv('GOOGLE_MAPS_BROWSER_KEY','public-restricted-key')
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'status':'OK','pano_id':'abc','date':'2025-01'}
    monkeypatch.setattr('app.integrations.httpx.get',lambda *a,**k:Response())
    result=imagery(1,2)
    assert result['street_view']=='available' and 'three_d_enabled' not in result
    assert 'private-server-key' not in str(result)
    assert TestClient(app).get('/imagery?latitude=91&longitude=0').status_code==422

def test_osm_footprint_measurement_cache_not_parcel(tmp_path,monkeypatch):
    import json
    (tmp_path/'data').mkdir()
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def raise_for_status(self):pass
        def iter_bytes(self):yield json.dumps({'elements':[{'id':1,'tags':{'building':'yes'},'geometry':[{'lon':0,'lat':0},{'lon':.0001,'lat':0},{'lon':.0001,'lat':.0001},{'lon':0,'lat':.0001},{'lon':0,'lat':0}]}]}).encode()
    monkeypatch.setattr('app.footprints.httpx.stream',lambda *a,**k:Response())
    result=fetch_footprints(0,0,tmp_path)
    assert result['features'][0]['properties']['area_sqm']>100
    assert not result['features'][0]['properties']['verified_parcel']
    assert fetch_footprints(0,0,tmp_path)['cache_hit']
