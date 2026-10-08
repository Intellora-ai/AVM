from fastapi import FastAPI, HTTPException
from .models import ValuationRequest
from .repository import repository, seed_demo_data
from .valuation import value_property

app = FastAPI(title="AVM valuation engine", version="1.0.0")
seed_demo_data()

@app.get("/health")
def health(): return {"status": "ok"}

@app.get("/properties")
def properties():
    return list(repository.properties.values())

@app.post("/valuations")
def valuation(request: ValuationRequest):
    target = repository.get_property(request.property_id)
    if not target: raise HTTPException(404, "property not found")
    result = value_property(target, repository.get_sales(request.valuation_date), request.valuation_date, repository.get_indices())
    result.historical_transactions = [s for s in repository.get_sales(request.valuation_date) if s.property_id == target.property_id]
    return result
