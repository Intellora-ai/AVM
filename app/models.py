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

class MarketIndex(BaseModel):
    index_date: date
    value: float = Field(gt=0)

class ValuationRequest(BaseModel):
    property_id: str
    valuation_date: date

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
