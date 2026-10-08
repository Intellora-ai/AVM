from app.evidence import EvidenceDiscovery
from app.main import repository, app
from fastapi.testclient import TestClient

def test_worldwide_click_cache_and_abstention(tmp_path, monkeypatch):
    service = EvidenceDiscovery(repository, tmp_path)
    calls = []
    def reverse(lat, lon):
        calls.append((lat, lon))
        return {'display_name': 'Paris, France', 'address': {'country_code': 'fr'}}
    monkeypatch.setattr(service, 'reverse', reverse)
    first = service.discover(48.85, 2.35)
    second = service.discover(48.85, 2.35)
    assert first['status'] == 'insufficient evidence'
    assert first['matches'] == [] and 'estimated_value' not in first
    assert second['cache_hit'] and len(calls) == 1
    assert first['lookup_id'] == second['lookup_id']

def test_source_outage_still_returns_supported_choices(tmp_path, monkeypatch):
    import httpx
    service = EvidenceDiscovery(repository, tmp_path)
    def unavailable(*args):
        raise httpx.ConnectError('offline')
    monkeypatch.setattr(service, 'reverse', unavailable)
    p = next(iter(repository.properties.values()))
    result = service.discover(p.latitude, p.longitude)
    assert result['source_error'] and result['status'] == 'profiles available'
    assert any(m['property']['property_id'] == p.property_id for m in result['matches'])
    assert not list(tmp_path.glob('*.json'))
    assert TestClient(app).post('/evidence/discover', json={'latitude': 91, 'longitude': 0}).status_code == 422
