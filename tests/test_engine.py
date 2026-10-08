from datetime import date,timedelta
from app.models import Property,Sale
from app.valuation import value_property,point_estimate

def fixture():
    on=date(2025,10,1)
    p=Property(property_id='target',latitude=1.35,longitude=103.84,area_sqm=100,property_type='4 ROOM')
    sales=[Sale(sale_id=str(i),property_id=str(i%12),sale_date=on-timedelta(days=i*7+1),price=600000*(1-.00005*i*7),area_sqm=100,latitude=1.35+i%4*.001,longitude=103.84,property_type='4 ROOM') for i in range(220)]
    return p,sales,on

def test_calibrated_estimate_and_forecasts():
    p,sales,on=fixture();r=value_property(p,sales,on,data_date=on)
    assert r.status=='ok' and r.calibration_count>=20
    assert r.lower_bound<=r.estimated_value<=r.upper_bound
    assert [f.months for f in r.forecasts]==[12,24,36]
    assert all(f.lower<=f.central<=f.upper for f in r.forecasts)

def test_no_future_or_subject_leakage():
    p,sales,on=fixture();baseline=point_estimate(p,sales,on)
    injected=[sales[0].model_copy(update={'sale_date':on+timedelta(days=1),'price':99999999}),sales[0].model_copy(update={'property_id':'target','price':99999999})]
    assert point_estimate(p,sales+injected,on)[0]==baseline[0]

def test_stale_and_missing_area_abstain():
    p,sales,on=fixture()
    for target,when in [(p,on+timedelta(days=181)),(p.model_copy(update={'area_sqm':None}),on)]:
        r=value_property(target,sales,when,data_date=on)
        assert r.status=='insufficient evidence' and r.estimated_value is None and not r.forecasts

def test_too_few_sales_abstain():
    p,sales,on=fixture()
    assert value_property(p,sales[:2],on).estimated_value is None
