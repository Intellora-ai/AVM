import pytest
from geographiclib.geodesic import Geodesic
from app.geometry import measure,MeasurementRequest
from fastapi.testclient import TestClient
from app.main import app

def test_geodesic_rectangle_units_and_reversed_winding():
    g=Geodesic.WGS84
    east=g.Direct(0,0,90,20);north=g.Direct(0,0,0,10);corner=g.Direct(north['lat2'],north['lon2'],90,20)
    points=[(0,0),(east['lon2'],east['lat2']),(corner['lon2'],corner['lat2']),(north['lon2'],north['lat2'])]
    a=measure(MeasurementRequest(coordinates=points,area_kind='land parcel'))
    b=measure(MeasurementRequest(coordinates=points[::-1]))
    assert a['area_sqm']==pytest.approx(200,abs=.01)
    assert a['area_sqft']==pytest.approx(2152.78,abs=.01)
    assert b['area_sqm']==a['area_sqm'] and a['floor_area_sqm'] is None
    assert not a['verified_boundary'] and a['corner_status']=='unknown'
    client=TestClient(app)
    response=client.post('/measurements',json={'coordinates':points,'area_kind':'land parcel'})
    assert response.status_code==200
    assert client.get('/measurements/'+response.json()['measurement_id']).json()==response.json()

def test_invalid_and_crossed_outlines_rejected():
    with pytest.raises(ValueError):measure(MeasurementRequest(coordinates=[(0,0),(.001,.001),(0,.001),(.001,0)]))
    with pytest.raises(ValueError):measure(MeasurementRequest(coordinates=[(0,0),(1,0),(1,1)]))
    with pytest.raises(ValueError):measure(MeasurementRequest(coordinates=[(0,0),(.001,0),(.002,0)]))
