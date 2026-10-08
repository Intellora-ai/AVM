from datetime import date,timedelta
import pytest
from pydantic import ValidationError
from app.models import ValuationRequest
from app.intelligence import IntelligenceRequest
from app.main import app,repository
from fastapi.testclient import TestClient

def test_exact_international_square_foot_conversion_and_conflicts():
    r=ValuationRequest(property_id='x',valuation_date=date.today(),area_sqft=1000)
    assert r.area_sqm==pytest.approx(92.90304)
    assert IntelligenceRequest(latitude=0,longitude=0,area_sqft=1000).area_sqm==pytest.approx(92.90304)
    for values in ({'area_sqm':100,'area_sqft':1000},{'area_sqft':-1},{'area_sqft':30000}):
        with pytest.raises(ValidationError):ValuationRequest(property_id='x',valuation_date=date.today(),**values)

def test_sqft_and_sqm_generate_same_value_but_retain_input_provenance():
    client=TestClient(app)
    p=next(p for p in repository.properties.values() if '173 ANG MO KIO AVE 4' in p.address and '4 ROOM' in p.property_type)
    on=(date.fromisoformat(repository.snapshot['data_date'])+timedelta(days=1)).isoformat()
    base={'property_id':p.property_id,'valuation_date':on}
    sqm=client.post('/valuations',json={**base,'area_sqm':92.90304}).json()
    sqft=client.post('/valuations',json={**base,'area_sqft':1000}).json()
    assert sqm['status']=='ok' and sqft['status']=='ok'
    assert sqft['estimated_value']==sqm['estimated_value']
    assert sqft['lower_bound']==sqm['lower_bound'] and sqft['upper_bound']==sqm['upper_bound']
    assert sqft['area_input']['value']==1000 and sqft['area_input']['unit']=='ft²'
    assert sqft['area_input']['normalized_sqm']==pytest.approx(92.90304)
    if sqft['estimated_value'] is not None:
        assert sqft['price_per_sqft']==pytest.approx(sqft['estimated_value']/1000,abs=.01)
    assert client.post('/valuations',json={**base,'area_sqm':100,'area_sqft':1000}).status_code==422
