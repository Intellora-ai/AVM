from datetime import date
import re
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from .repository import Repository, ROOT
from .models import ValuationRequest
from .valuation import value_property

repository=Repository()
app=FastAPI(title='AVM · residential evidence')
@app.get('/health')
def health(): return {'status':'ok','storage':'postgis' if repository.url else 'snapshot'}
@app.get('/metadata')
def metadata(): return {k:v for k,v in repository.snapshot.items() if k not in ('properties','sales')}
@app.get('/properties')
def properties(q:str=''):
    return [p for p in repository.properties.values() if q.lower() in (p.address+' '+p.property_id).lower()]
@app.post('/valuations')
def valuation(request:ValuationRequest):
    target=repository.properties.get(request.property_id)
    if target is None: raise HTTPException(404,'Property not found')
    if request.valuation_date>date.today(): raise HTTPException(422,'Use a current or historical valuation date')
    # Full local sample calibrates the market; candidate selection also uses PostGIS.
    nearby=repository.nearby(target,request.valuation_date)
    result=value_property(target,repository.sales,request.valuation_date,candidates=nearby,data_version=repository.version,data_date=date.fromisoformat(repository.snapshot['data_date']))
    result.historical_transactions=[s for s in repository.sales if s.property_id==target.property_id and s.sale_date<request.valuation_date]
    return repository.save(result)
@app.get('/valuations/{key}')
def receipt(key:str):
    if not re.fullmatch('[a-f0-9]{64}',key): raise HTTPException(404)
    value=repository.receipt(key)
    if value is None: raise HTTPException(404)
    return value
if (ROOT/'frontend/dist').exists():
    app.mount('/',StaticFiles(directory=ROOT/'frontend/dist',html=True),name='frontend')
