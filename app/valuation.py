"""Pure comparable-sales model. Database and HTTP layers deliberately do not leak in here."""
from datetime import date
from math import asin, cos, radians, sin, sqrt
from statistics import median
from .models import MarketIndex, Property, Sale, ComparableUsed, ValuationResponse

EARTH_M = 6_371_000

def distance_m(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    dlat, dlon = radians(b_lat-a_lat), radians(b_lon-a_lon)
    h = sin(dlat/2)**2 + cos(radians(a_lat))*cos(radians(b_lat))*sin(dlon/2)**2
    return 2 * EARTH_M * asin(sqrt(h))

def index_value(indices: list[MarketIndex], on: date) -> float | None:
    prior = [x for x in indices if x.index_date <= on]
    return max(prior, key=lambda x: x.index_date).value if prior else None

def similarity(target: Property, sale: Sale) -> float:
    score = 1.0 if target.property_type == sale.property_type else 0.15
    area_ratio = min(target.area_sqm, sale.area_sqm) / max(target.area_sqm, sale.area_sqm)
    score *= 0.5 + 0.5 * area_ratio
    if target.bedrooms is not None and sale.bedrooms is not None:
        score *= 1.0 if target.bedrooms == sale.bedrooms else 0.65
    return score

def comparable_sales(target: Property, sales: list[Sale], valuation_date: date, indices: list[MarketIndex], *, radius_m=5000, max_age_days=1095) -> list[ComparableUsed]:
    current_index = index_value(indices, valuation_date)
    result = []
    for sale in sales:
        age = (valuation_date - sale.sale_date).days
        d = distance_m(target.latitude, target.longitude, sale.latitude, sale.longitude)
        if sale.property_id == target.property_id or age < 0 or age > max_age_days or d > radius_m:
            continue
        sim = similarity(target, sale)
        if sim < 0.35:
            continue
        sale_index = index_value(indices, sale.sale_date)
        adjusted = sale.price * (current_index / sale_index if current_index and sale_index else 1.0)
        recency = max(0.05, 1 - age / max_age_days)
        dist_weight = max(0.05, 1 - d / radius_m)
        result.append(ComparableUsed(sale_id=sale.sale_id, sale_date=sale.sale_date, distance_m=round(d, 2), similarity=round(sim, 4), recency_weight=round(recency*dist_weight, 4), adjusted_price=round(adjusted, 2), adjusted_price_per_sqm=round(adjusted/sale.area_sqm, 2), latitude=sale.latitude, longitude=sale.longitude))
    return sorted(result, key=lambda c: c.similarity*c.recency_weight, reverse=True)

def value_property(target: Property, sales: list[Sale], valuation_date: date, indices: list[MarketIndex], *, min_comparables=3, data_version="demo-1", model_version="comparable-v1") -> ValuationResponse:
    comps = comparable_sales(target, sales, valuation_date, indices)
    if len(comps) < min_comparables:
        return ValuationResponse(status="insufficient evidence", confidence=0, comparable_sales_used=comps, valuation_date=valuation_date, data_version=data_version, model_version=model_version, reason=f"Only {len(comps)} suitable comparables; need at least {min_comparables}.")
    weights = [max(0.0001, c.similarity*c.recency_weight) for c in comps]
    ppsm = sum(c.adjusted_price_per_sqm*w for c,w in zip(comps,weights)) / sum(weights)
    estimate = ppsm * target.area_sqm
    errors = [abs(c.adjusted_price_per_sqm - ppsm) / ppsm for c in comps]
    spread = max(0.05, min(0.35, median(errors) * 1.96))
    quality = min(1.0, sum(weights)/len(weights))
    confidence = round(max(0.0, min(0.99, quality * (1 - min(0.8, spread)))), 3)
    return ValuationResponse(status="ok", estimated_value=round(estimate,2), lower_bound=round(estimate*(1-spread),2), upper_bound=round(estimate*(1+spread),2), confidence=confidence, comparable_sales_used=comps, valuation_date=valuation_date, data_version=data_version, model_version=model_version)
