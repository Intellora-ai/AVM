"""Trusted bundled challenger; model application requires explicit user flat attributes."""
import gzip,hashlib,json,math
from pathlib import Path
from functools import lru_cache
from datetime import date,timedelta
import joblib
from .models import ForecastScenario
ROOT=Path(__file__).resolve().parents[1]
def feature(s):
    year,month=map(int,s['record_month'].split('-'))
    floor=s.get('storey_range') or '0 TO 0'
    try: floor=float(floor.split(' TO ')[0])
    except ValueError: floor=0
    return {'log_area':math.log(s['area_sqm']),'latitude':s['latitude'],'longitude':s['longitude'],'building_age':year-s.get('lease_commence_date',year),'floor':floor,'time':year+(month-1)/12,'town='+s.get('neighbourhood',''):1,'type='+s['property_type']:1,'model='+str(s.get('flat_model','')):1}
@lru_cache(maxsize=1)
def load_model():
    meta_path=ROOT/'data/model_metadata.json'
    if not meta_path.exists():return None
    meta=json.loads(meta_path.read_text());payload=(ROOT/'data/champion.joblib').read_bytes()
    if hashlib.sha256(payload).hexdigest()!=meta['sha256']:raise RuntimeError('Model artifact checksum mismatch')
    return joblib.load(ROOT/'data/champion.joblib'),meta
def apply_challenger(result,request,history):
    loaded=load_model()
    if not loaded or result.status!='ok' or request.area_sqm is None or not request.storey_range or not request.flat_model or not history:return result
    bundle,meta=loaded
    valid_until=date.fromisoformat(meta['evaluated_through'])+timedelta(days=90)
    if (result.model_training_data_version or result.data_version)!=meta['data_version'] or result.valuation_date<date.fromisoformat(meta['valid_from']) or result.valuation_date>valid_until:return result
    if request.flat_model not in {s.flat_model for s in history}:return result
    years={s.lease_commence_date for s in history if s.lease_commence_date}
    if len(years)!=1:return result
    p=result.property
    inputs=dict(record_month=result.valuation_date.isoformat()[:7],area_sqm=request.area_sqm,latitude=p.latitude,longitude=p.longitude,lease_commence_date=next(iter(years)),neighbourhood=p.neighbourhood,property_type=p.property_type,storey_range=request.storey_range,flat_model=request.flat_model)
    prediction=math.exp(float(bundle['model'].predict(bundle['vectorizer'].transform([feature(inputs)]))[0]))
    # Corroborating sale evidence still required; abstain on strong model disagreement.
    if not .7<=prediction/result.estimated_value<=1.3:
        result.input_assumptions.append('Challenger disagreed with comparable evidence; retained comparable result.');return result
    ratio=prediction/result.estimated_value
    result.estimated_value=round(prediction)
    q=meta['calibration_log_error_quantile']
    result.lower_bound=round(prediction*math.exp(-q));result.upper_bound=round(prediction*math.exp(q))
    result.forecasts=[f.model_copy(update={'lower':round(f.lower*ratio),'central':round(f.central*ratio),'upper':round(f.upper*ratio)}) for f in result.forecasts]
    result.model_version=meta['model_version']
    result.valuation_method='histogram gradient boosting; comparable evidence required'
    result.interval_method='Calibration-period 90th percentile log-error band; measured later-test coverage '+str(round(meta['test_interval_coverage']*100,1))+'%, not guaranteed coverage.'
    result.calibration_count=meta['calibration_count']
    result.input_assumptions.extend(['User supplied area, storey range and flat model.', 'Lease start is consistent across this block/type record history.', 'No verified unit identity or condition information.'])
    if result.valuation_date>date.fromisoformat(meta['evaluated_through']):result.input_assumptions.append('Live date is later than the evaluated test period; recent live accuracy is not yet measured.')
    return result
