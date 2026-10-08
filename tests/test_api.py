from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_properties_search_receipt_and_current_abstention():
    props=client.get('/properties').json()
    assert props and client.get('/properties',params={'q':props[0]['address']}).json()
    r=client.post('/valuations',json={'property_id':props[0]['property_id'],'valuation_date':'2026-10-08'})
    assert r.status_code==200
    body=r.json()
    assert body['status']=='insufficient evidence'
    assert client.get('/valuations/'+body['valuation_id']).json()==body
    assert client.post('/valuations',json={'property_id':'missing','valuation_date':'2025-10-01'}).status_code==404
