import json
from datetime import date
from types import SimpleNamespace
import pytest
from app.intelligence import extract, deduplicate, signals_for, IntelligenceRequest, Intelligence, public_url
from app.sources import nyc_sales

def page(address='10 Test Street', price=100000, host='https://example.com/one', currency='USD', function='Sell', period=None):
    item={'@type':'House','address':address,'floorSize':{'value':100,'unitCode':'MTK'},'geo':{'latitude':40.7,'longitude':-74}}
    offer={'price':price,'priceCurrency':currency,'businessFunction':'https://purl.org/goodrelations/v1#'+function}
    if period:offer['priceSpecification']={'unitText':period}
    node={'@type':'RealEstateListing','itemOffered':item,'offers':offer,'datePosted':date.today().isoformat()}
    return '<script type="application/ld+json">'+json.dumps(node)+'</script>',host

def test_extraction_classifies_offers_without_fabricating_sales():
    html,url=page();records=extract(html,url,'now')
    assert records[0]['type']=='asking_price' and not records[0]['verified_transaction']
    assert records[0]['area_sqm']==100
    html,url=page(function='LeaseOut',period='MONTH')
    assert extract(html,url,'now')[0]['period']=='month'
    product='<script type="application/ld+json">{"@type":"Product","name":"Chair","offers":{"price":20,"priceCurrency":"USD"}}</script>'
    assert extract(product,url,'now')==[]
    html,url=page()
    html=html.replace('"price": 100000','"availability": "https://schema.org/SoldOut", "price": 100000')
    assert extract(html,url,'now')[0]['type']=='historical_asking_price'

def test_syndication_and_repricing_cannot_create_votes():
    records=[]
    for price,host in [(100000,'https://a.test/1'),(105000,'https://b.test/2')]:
        html,url=page(price=price,host=host);records+=extract(html,url,'now')
    unique,duplicates=deduplicate(records)
    assert len(unique)==1 and len(duplicates)==1
    request=IntelligenceRequest(latitude=40.7,longitude=-74,property_type="house",area_sqm=100)
    assert signals_for(request,unique)[0]==[]

def test_distinct_listing_signal_currency_and_freshness_guards():
    records=[]
    for i in range(3):
        html,url=page(address=f'{i} Test Street',price=100000+i*10000,host=f'https://source{i}.test/a')
        records+=extract(html,url,'now')
    request=IntelligenceRequest(latitude=40.7,longitude=-74,property_type="house",area_sqm=100)
    signals,eligible,rejected,_=signals_for(request,records)
    assert len(signals)==1 and signals[0]['value']==110000
    assert not signals[0]['validated'] and len(eligible)==3 and not rejected
    records[0]['currency']='EUR';records[1]['source_date']=None
    assert signals_for(request,records)[0]==[]

def test_unknown_rental_period_yield_not_assumed():
    records=[]
    for i in range(3):
        html,url=page(address=f'{i} Test Street',host=f'https://source{i}.test/a',function='LeaseOut')
        records+=extract(html,url,'now')
    request=IntelligenceRequest(latitude=40.7,longitude=-74,property_type="house",area_sqm=100,annual_gross_yield=.05)
    assert signals_for(request,records)[0]==[]

def test_private_source_rejected(monkeypatch):
    monkeypatch.setattr('app.intelligence.socket.getaddrinfo',lambda *a,**k:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError):public_url('https://internal.example')
    with pytest.raises(ValueError):public_url('http://example.com')

def test_official_nyc_excludes_multiunit_and_nonmarket_prices(monkeypatch):
    rows=[{'sale_price':'600000','gross_square_feet':'1000','total_units':'1','building_class_category':'01 ONE FAMILY DWELLINGS','address':'10 TEST STREET','borough':'5','block':'1','lot':'1','sale_date':'2026-06-01T00:00:00'},
          {'sale_price':'900000','gross_square_feet':'1000','total_units':'8','building_class_category':'07 RENTALS - WALKUP APARTMENTS'}]
    class Response:
        def raise_for_status(self):pass
        def json(self):return rows
    monkeypatch.setattr('app.sources.httpx.get',lambda *a,**k:Response())
    records,status=nyc_sales({'address':{'address':{'country_code':'us','city':'New York','postcode':'10314'}}})
    assert len(records)==1 and records[0]['verified_transaction']
    assert records[0]['area_sqm']==pytest.approx(92.90304)
    assert records[0]['original_record']==rows[0]

def test_complete_request_retains_evidence_and_abstains(tmp_path,monkeypatch):
    discovery=SimpleNamespace(repository=SimpleNamespace(version='test'),discover=lambda *a:{'address':None,'matches':[]})
    html,url=page()
    monkeypatch.setattr('app.intelligence.fetch_page',lambda u:(html,u))
    service=Intelligence(discovery,tmp_path)
    result=service.run(IntelligenceRequest(latitude=40.7,longitude=-74,source_urls=[url],area_sqm=100))
    assert result['estimated_value'] is None and result['status']=='insufficient evidence'
    assert len(result['evidence'])==1
    saved=json.loads((tmp_path/'data/intelligence-receipts'/(result['receipt_id']+'.json')).read_text())
    assert saved==result
    again=service.run(IntelligenceRequest(latitude=40.7,longitude=-74,source_urls=[url],area_sqm=100))
    assert again['source_results'][0]['cache_hit']

def test_api_supported_transaction_receipt_and_location_guard(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from app import main
    property = next(iter(main.repository.properties.values()))
    service=Intelligence(SimpleNamespace(repository=main.repository,discover=lambda *a:{'address':None,'matches':[]}),tmp_path)
    monkeypatch.setattr(main,'intelligence',service)
    client=TestClient(main.app)
    request={'latitude':property.latitude,'longitude':property.longitude,'property_id':property.property_id,'currency':'SGD'}
    response=client.post('/intelligence',json=request)
    assert response.status_code==200
    body=response.json()
    assert body['transaction_valuation']['valuation_id']
    assert body['estimated_value']==body['transaction_valuation']['estimated_value']
    assert client.get('/intelligence/'+body['receipt_id']).json()==body
    request['latitude']=0
    assert client.post('/intelligence',json=request).status_code==422
