from fastapi.testclient import TestClient
from app.main import app,repository
from datetime import date,timedelta
client=TestClient(app)
def test_properties_search_and_receipt():
    props=client.get('/properties').json()
    assert props and client.get('/properties',params={'q':props[0]['address']}).json()
    assert len(client.get('/properties',params={'q':props[0]['address'],'limit':1}).json())==1
    assert client.get('/properties',params={'limit':0}).status_code==422
    on=(date.fromisoformat(repository.snapshot['data_date'])+timedelta(days=1)).isoformat()
    r=client.post('/valuations',json={'property_id':props[0]['property_id'],'valuation_date':on})
    assert r.status_code==200
    body=r.json()
    assert body['status'] in ('ok','insufficient evidence')
    assert client.get('/valuations/'+body['valuation_id']).json()==body
    assert client.post('/valuations',json={'property_id':'missing','valuation_date':'2025-10-01'}).status_code==404
