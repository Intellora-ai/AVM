from datetime import date
from fastapi.testclient import TestClient
from app.main import app,repository
client=TestClient(app)
def target():
    return next(p for p in repository.properties.values() if p.address=='173 ANG MO KIO AVE 4, Singapore' and p.property_type=='4 ROOM')
def test_official_current_and_historical_values():
    p=target()
    for when in ['2005-10-01','2020-10-01','2026-10-08']:
        r=client.post('/valuations',json={'property_id':p.property_id,'valuation_date':when}).json()
        assert r['status']=='ok'
        assert all(s['sale_date']<when for s in r['comparable_sales_used'])
        assert len(r['forecasts'])==3 and r['data_version']==repository.version
        assert all(s['verified'] for s in r['historical_transactions'])
def test_original_record_provenance():
    sale=repository.sales[0]
    r=client.get('/source-records/'+sale.sale_id).json()
    assert float(r['original_record']['resale_price'])==sale.price
    assert r['source_hash']==repository.snapshot['source_hashes']['sales']
def test_challenger_needs_explicit_features_and_preserves_earlier_date_gate():
    p=target()
    payload={'property_id':p.property_id,'valuation_date':'2026-10-08','area_sqm':91,'storey_range':'07 TO 09','flat_model':'New Generation'}
    r=client.post('/valuations',json=payload).json()
    assert r['status']=='ok'
    assert r['valuation_method'].startswith('histogram')
    old=client.post('/valuations',json={**payload,'valuation_date':'2020-10-01'}).json()
    assert old['valuation_method']=='comparable sales'
