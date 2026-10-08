"""Click-triggered source adapters. Cache discovery, retain immutable evidence receipts."""
import hashlib
import json
import threading
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import httpx

class EvidenceDiscovery:
    def __init__(self, repository, directory=None):
        self.repository = repository
        self.directory = Path(directory or Path(__file__).resolve().parents[1] / 'data/evidence-cache')
        self.lock = threading.Lock()
        self.last_request = 0

    def reverse(self, latitude, longitude):
        # Explicit user actions only; fixed destination and shared rate limit.
        with self.lock:
            time.sleep(max(0, 1 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            response = httpx.get('https://nominatim.openstreetmap.org/reverse',
                params={'lat': latitude, 'lon': longitude, 'format': 'jsonv2', 'addressdetails': 1},
                headers={'User-Agent': 'AVM-ResearchPreview/1.0 (https://github.com/Intellora-ai/AVM)'}, timeout=15)
            response.raise_for_status()
            return response.json()

    def discover(self, latitude, longitude):
        key = hashlib.sha256(f'{latitude:.6f},{longitude:.6f}|{self.repository.version}|discovery-1'.encode()).hexdigest()
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (key + '.json')
        if path.exists() and time.time() - path.stat().st_mtime < 86400:
            return {**json.loads(path.read_text()), 'cache_hit': True}
        from .valuation import distance_m
        matches = []
        # Existing official adapter is reused, never confuse nearest buildings with an exact unit match.
        if 1.1 <= latitude <= 1.5 and 103.5 <= longitude <= 104.2:
            matches = [{'property': p.model_dump(mode='json'), 'distance_m': round(distance_m(latitude, longitude, p.latitude, p.longitude), 1)}
                for p in self.repository.properties.values()
                if distance_m(latitude, longitude, p.latitude, p.longitude) <= 100]
            matches.sort(key=lambda item: item['distance_m'])
        address, source_error = None, None
        try:
            address = self.reverse(latitude, longitude)
        except (httpx.HTTPError, ValueError):
            source_error = 'Address source unavailable; no address was inferred.'
        result = {'lookup_id': key, 'latitude': latitude, 'longitude': longitude,
            'retrieved_at': datetime.now(timezone.utc).isoformat(), 'cache_hit': False,
            'address': address, 'source_error': source_error, 'matches': matches[:30],
            'status': 'profiles available' if matches else 'insufficient evidence',
            'reason': 'Choose a nearby block/type profile; exact apartment identity is unavailable.' if matches else 'No matched, validated property valuation is available for this location. The intelligence panel checks available source evidence separately.',
            'sources': ['https://nominatim.openstreetmap.org/'],
            'data_version': self.repository.version, 'discovery_version': 'discovery-1'}
        # Address failure should be retried on the next click instead of cached for a day.
        if source_error is None:
            with tempfile.NamedTemporaryFile(mode='w', dir=self.directory, delete=False) as stream:
                json.dump(result, stream)
                temporary = Path(stream.name)
            temporary.replace(path)
        return result
