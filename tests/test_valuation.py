from datetime import date, timedelta
from app.models import MarketIndex, Property, Sale
from app.valuation import value_property

def fixtures():
    target = Property(property_id="target", latitude=51.0, longitude=0.0, area_sqm=100, property_type="house", bedrooms=3)
    sales = [Sale(sale_id=str(i), property_id=f"p{i}", sale_date=date(2025, 1, 1)-timedelta(days=i*30), price=500000-i*5000, area_sqm=100, latitude=51.0+i*.001, longitude=0, property_type="house", bedrooms=3) for i in range(1,5)]
    indices = [MarketIndex(index_date=date(2024,1,1), value=100), MarketIndex(index_date=date(2025,1,1), value=110), MarketIndex(index_date=date(2025,6,1), value=115)]
    return target, sales, indices

def test_value_adjusts_trend_and_returns_range():
    target, sales, indices = fixtures()
    result = value_property(target, sales, date(2025,6,1), indices)
    assert result.status == "ok"
    assert result.estimated_value > 500000
    assert result.lower_bound < result.estimated_value < result.upper_bound
    assert len(result.comparable_sales_used) == 4

def test_insufficient_evidence():
    target, sales, indices = fixtures()
    result = value_property(target, sales[:2], date(2025,6,1), indices)
    assert result.status == "insufficient evidence"
