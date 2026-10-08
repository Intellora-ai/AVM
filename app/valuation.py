"""Replaceable comparable model with strictly earlier-sales calibration."""
from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt, log, exp, ceil
from statistics import median
from .models import Property, Sale, ComparableUsed, ValuationResponse, ForecastScenario

MODEL_VERSION='comparables-2.0'
def distance_m(a,b,c,d):
    h=sin(radians(c-a)/2)**2+cos(radians(a))*cos(radians(c))*sin(radians(d-b)/2)**2
    return 12742000*asin(sqrt(min(1,h)))

def annual_trend(sales,on):
    older=[s.price/s.area_sqm for s in sales if 365 <= (on-s.sale_date).days < 730]
    recent=[s.price/s.area_sqm for s in sales if 0 < (on-s.sale_date).days < 365]
    if min(len(older),len(recent)) < 10: return None
    return max(-.2,min(.2,log(median(recent)/median(older))))

def comparable_sales(target,sales,on,candidates=None):
    trend=annual_trend([s for s in sales if s.property_id!=target.property_id],on)
    if target.area_sqm is None or trend is None: return []
    ranked=[]
    for s in sales if candidates is None else candidates:
        age=(on-s.sale_date).days
        distance=distance_m(target.latitude,target.longitude,s.latitude,s.longitude)
        ratio=min(target.area_sqm,s.area_sqm)/max(target.area_sqm,s.area_sqm)
        if s.property_id==target.property_id or not 0<age<=730 or distance>2000 or ratio<.75 or s.property_type!=target.property_type: continue
        adjusted=s.price*exp(trend*age/365.25)
        c=ComparableUsed(sale_id=s.sale_id,property_id=s.property_id,sale_date=s.sale_date,distance_m=round(distance,1),similarity=ratio,recency_weight=exp(-age/365)/(1+distance/500),adjusted_price=round(adjusted,2),adjusted_price_per_sqm=adjusted/s.area_sqm,latitude=s.latitude,longitude=s.longitude,original_price=s.price,area_sqm=s.area_sqm,source=s.source,source_reference=s.source_reference,flat_model=s.flat_model,storey_range=s.storey_range)
        ranked.append(c)
    return sorted(ranked,key=lambda c:c.similarity*c.recency_weight,reverse=True)[:12]

def point_estimate(target,sales,on,candidates=None):
    comps=comparable_sales(target,sales,on,candidates)
    if len(comps)<5 or len({c.property_id for c in comps})<3: return None,comps
    weights=[c.similarity*c.recency_weight for c in comps]
    return target.area_sqm*sum(c.adjusted_price_per_sqm*w for c,w in zip(comps,weights))/sum(weights),comps

def backtest(sales,on):
    errors=[]
    candidates=sorted([s for s in sales if on-timedelta(days=730)<=s.sale_date<on],key=lambda s:(s.sale_date,s.sale_id))[-80:]
    for s in candidates:
        p=Property(property_id=s.property_id,latitude=s.latitude,longitude=s.longitude,area_sqm=s.area_sqm,property_type=s.property_type)
        predicted,_=point_estimate(p,sales,s.sale_date)
        if predicted: errors.append(abs(log(s.price/predicted)))
    return errors

def value_property(target,sales,on,indices=None,*,data_version='unknown',data_date=None,**kwargs):
    estimate,comps=point_estimate(target,sales,on,kwargs.get('candidates'))
    result=ValuationResponse(status='insufficient evidence',confidence=0,comparable_sales_used=comps,valuation_date=on,data_version=data_version,model_version=MODEL_VERSION,property=target,data_date=data_date,demo=False,sources=sorted({s.source for s in sales}),reason='Insufficient market evidence to produce a reliable valuation.')
    if data_date and (on-data_date).days>180:
        result.reason='Insufficient current evidence: transaction snapshot is more than 180 days old.'
        return result
    if estimate is None: return result
    errors=backtest(sales,on)
    if len(errors)<20:
        result.reason='Insufficient historical predictions to calibrate a valuation range.'
        return result
    q=sorted(errors)[min(len(errors)-1,ceil((len(errors)+1)*.9)-1)]
    result.status='ok';result.reason=None
    result.estimated_value=round(estimate)
    result.lower_bound=round(estimate*exp(-q));result.upper_bound=round(estimate*exp(q))
    result.calibration_count=len(errors)
    result.confidence=round(max(0,min(.85,1-exp(q)+1)),2)
    result.confidence_label='moderate' if q<.2 else 'low'
    result.interval_method='90% absolute log-error quantile from earlier rolling historical predictions; coverage not guaranteed.'
    trend=annual_trend([s for s in sales if s.property_id!=target.property_id],on)
    result.forecast_method=f'Historical town/type median price/m² trend ({100*(exp(trend)-1):.1f}% annual), compounded; widening residual scenarios. Mix changes may bias trend.'
    result.forecasts=[ForecastScenario(months=m,lower=round(estimate*exp(trend*m/12-q*sqrt(1+m/12))),central=round(estimate*exp(trend*m/12)),upper=round(estimate*exp(trend*m/12+q*sqrt(1+m/12)))) for m in (12,24,36)]
    return result
