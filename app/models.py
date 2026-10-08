from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

class Property(BaseModel):
    property_id: str
    latitude: float
    longitude: float
    area_sqm: float = Field(gt=0)
    property_type: str
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
