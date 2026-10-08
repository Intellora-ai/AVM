from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

class Property(BaseModel):
    property_id: str
    latitude: float
    longitude: float
    area_sqm: float | None = Field(default=None, gt=0)
    property_type: str
    address: str = "Address unavailable"
    neighbourhood: str | None = None
    bathrooms: int | None = None
    building: str | None = None
    source_reference: str = "synthetic fixture"
    market: str = "SG-HDB"
    currency: str = "SGD"
    bedrooms: int | None = Field(default=None, ge=0)
    year_built: int | None = None

class Sale(BaseModel):
    sale_id: str
    property_id: str
    sale_date: date
    price: float = Field(gt=0)
    area_sqm: float = Field(gt=0)
    latitude: float
    longitude: float
    property_type: str
    bedrooms: int | None = Field(default=None, ge=0)
    source: str = "demo registry"
    source_reference: str = "synthetic fixture"
    verified: bool = False
    neighbourhood: str = ""
    flat_model: str | None = None
    storey_range: str | None = None
    lease_commence_date: int | None = None
    record_month: str | None = None
    date_basis: str = "registration month"

class MarketIndex(BaseModel):
    index_date: date
    value: float = Field(gt=0)

class ValuationRequest(BaseModel):
    property_id: str
    valuation_date: date
    area_sqm: float | None = Field(default=None, gt=0, le=2000)
    storey_range: str | None = Field(default=None, pattern=r"^[0-9]{2} TO [0-9]{2}$")
    flat_model: str | None = Field(default=None, max_length=80)

class ComparableUsed(BaseModel):
    sale_id: str
    sale_date: date
    distance_m: float
    similarity: float
    recency_weight: float
    adjusted_price: float
    adjusted_price_per_sqm: float
    latitude: float
    longitude: float
    property_id: str
    original_price: float
    area_sqm: float
    source: str
    source_reference: str
    storey_range: str | None = None
    flat_model: str | None = None

class ForecastScenario(BaseModel):
    months: int
    lower: float
    central: float
    upper: float

class ValuationResponse(BaseModel):
    status: Literal["ok", "insufficient evidence"]
    estimated_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    confidence: float
    comparable_sales_used: list[ComparableUsed]
    valuation_date: date
    data_version: str
    model_version: str
    reason: str | None = None
    historical_transactions: list[Sale] = []
    forecasts: list[ForecastScenario] = []
    sources: list[str] = []
    valuation_id: str | None = None
    property: Property | None = None
    data_date: date | None = None
    demo: bool = True
    confidence_label: str = "unavailable"
    interval_method: str = "unavailable"
    calibration_count: int = 0
    forecast_method: str = "unavailable"
    currency: str = "SGD"
    evidence_scope: str = "block/type profile; exact unit identity unavailable"
    forecast_validation: str = "Conditional scenarios; forecast accuracy has not been established."
    valuation_method: str = "comparable sales"
    input_assumptions: list[str] = []
    model_training_data_version: str | None = None
