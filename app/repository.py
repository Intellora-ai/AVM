from datetime import date, timedelta
from .models import MarketIndex, Property, Sale

class DemoRepository:
    def __init__(self):
        self.properties: dict[str, Property] = {}
        self.sales: list[Sale] = []
        self.indices: list[MarketIndex] = []
    def get_property(self, property_id: str) -> Property | None:
        return self.properties.get(property_id)
    def get_sales(self, valuation_date: date) -> list[Sale]:
        return [s for s in self.sales if s.sale_date <= valuation_date]
    def get_indices(self) -> list[MarketIndex]: return self.indices

repository = DemoRepository()

def seed_demo_data():
    """Small deterministic dataset for a fresh MVP checkout."""
    if repository.properties:
        return
    repository.properties["demo-001"] = Property(property_id="demo-001", latitude=51.5074, longitude=-0.1278, area_sqm=92, property_type="flat", bedrooms=2)
    repository.indices.extend([MarketIndex(index_date=date(2024, 1, 1), value=100), MarketIndex(index_date=date(2025, 1, 1), value=106), MarketIndex(index_date=date(2026, 1, 1), value=110)])
    for i, (lat, lon, area, price) in enumerate([(51.508, -0.128, 90, 565000), (51.506, -0.126, 95, 590000), (51.509, -0.127, 88, 548000), (51.505, -0.129, 94, 570000), (51.507, -0.125, 91, 555000)], 1):
        repository.sales.append(Sale(sale_id=f"demo-sale-{i}", property_id=f"sold-{i}", sale_date=date(2025, 12, 1)-timedelta(days=i*35), price=price, area_sqm=area, latitude=lat, longitude=lon, property_type="flat", bedrooms=2))
    repository.sales.append(Sale(sale_id="demo-history-001", property_id="demo-001", sale_date=date(2022, 6, 15), price=470000, area_sqm=92, latitude=51.5074, longitude=-0.1278, property_type="flat", bedrooms=2, source="demo registry"))
