# AVM — residential property evidence

Global MapLibre/OpenStreetMap map and address discovery, official Singapore HDB resale evidence, dated valuations, scenario forecasts, historical charts and reproducible receipts. No Google Maps or paid AI API.

## Open locally on Mac

Install Python 3 and Node.js LTS, then:

```bash
git clone https://github.com/Intellora-ai/AVM.git
cd AVM
bash start.command
```

Already cloned:

```bash
cd ~/AVM
git pull --ff-only origin main
bash start.command
```

Open **http://localhost:8000** and leave the terminal running. Python 3.14 Apple Silicon wheels were checked for the previous requirement set; scikit-learn is now also required for the bundled challenger. The local app uses the compressed immutable snapshot and saves receipts in ignored data/receipts.

Explore Singapore, search **173 ANG MO KIO AVE 4**, select a flat type and see past recorded sales, a current estimate and 12/24/36-month scenarios. Supply actual area, storey range and flat model when known to enable the evaluated challenger where evidence supports it. Change the date for a historical estimate.

## Actual coverage and data

The direct official data.gov.sg acquisition contains **988,459 resale records from 1990–2026**: 242,256 recent records in the active snapshot and 746,203 older archived rows. The active inventory contains **16,938 block/type profiles** across all published Singapore HDB residential resale types. It was retrieved 8 October 2026. October is an incomplete reported month; valuations conservatively use earlier completed months through September. Older records are joined lazily to present matched blocks; demolished/unmatched historic blocks are not claimed as supported.

HDB withholds unit identities. Recorded sales belong to the block/type, not necessarily the selected apartment. Area is supplied by the buyer or inferred from strictly earlier block/type records. The model does not know condition or renovations. Coordinates are from a pinned OneMap-derived public mirror matched to official building keys.

Worldwide address lookup is geographic discovery. France, England/Wales and NYC official acquisition was attempted but blocked by this cloud's network policy. These markets are not claimed as valued. See data/coverage.json and [research and launch requirements](docs/VALUATION_RESEARCH.md).

## Accuracy and methods

Reused scikit-learn log-price ridge and histogram gradient boosting. Training ends June 2025; selection/calibration ends December 2025; later test data are January–September 2026. Every flat type at approximately 10% of building coordinates is held out together and reported separately.

On **19,639 later sales**, gradient boosting had **4.51% median absolute error**, versus 6.57% for ridge; 83.98% of boosting predictions were within ±10%. On 1,966 sales at unseen building coordinates its median error was 4.98%. These results use known sale attributes and do not establish global or future-price accuracy. Its nominal 90% band covered 85.02% of later sales; coverage is not guaranteed.

Comparable valuation uses earlier sales, same type, nearby location and area similarity; observed town/type price trends adjust older prices. It requires five comparable transactions across three other profiles and twenty historical calibration predictions. The challenger additionally requires user area/floor/model, a consistent recorded lease year, an evaluated effective-date range and corroborating comparable evidence. Older dates use comparable estimation; unsupported dates or characteristics abstain.

Future values are conditional trend scenarios with widening ranges, not verified transactions or validated individual-property forecasts. Past estimates are reconstructions from today's snapshot, not proof of contemporaneous knowledge.

## Reproduce data, evaluation and receipts

```bash
.venv/bin/python scripts/import_hdb.py
.venv/bin/python scripts/archive_history.py
OMP_NUM_THREADS=2 .venv/bin/python scripts/benchmark.py
.venv/bin/python -m pytest -q
cd frontend && npm ci && npm run build
```

Raw official CSVs, hashes, a compressed snapshot, benchmark metrics and a checksum-protected model artifact are bundled. Model/data version mismatch disables the challenger until a new benchmark is run. POST /valuations returns a content-addressed receipt; GET /valuations/{id} retrieves that saved output. GET /source-records/{sale_id} shows the original official CSV row from the current source snapshot.

## PostgreSQL/PostGIS

With Docker Desktop:

```bash
docker compose up --build
```

Open the same port 8000. Snapshots, spatial sale evidence and receipts persist in Postgres. DATABASE_URL enables the database adapter; without it, local spatial indexing and snapshot storage support the preview. Live processes must restart after a cloud snapshot restore.

## Mapping and attribution

Singapore streets use the official Singapore Land Authority OneMap public basemap, tested by direct tile requests. Global street tiles use OpenStreetMap's public service; cloud/datacenter requests may be denied under its tile policy. Bundled public-domain Natural Earth country geography supplies a global fallback; it is not a street map. VITE_TILE_URL can specify a self-hosted or policy-compliant raster service at frontend build time.

HDB sales/buildings: data.gov.sg and original Singapore government data terms. Coordinates: ayaka14732/singapore-hdb-map, OneMap-derived; source URI and hashes retained. Natural Earth: public-domain geography via nvkelso/natural-earth-vector. OpenStreetMap: © contributors, ODbL. Existing mirrored-sample license notice is retained for the older archived sample. The application MIT license does not relicense third-party data.

This is a buyer research tool. Private residential Singapore property, exact apartment history and majority-world valuation coverage have not yet been demonstrated. Public hosting, HTTPS, backups and ongoing refresh/monitoring remain deployment work.
# On-demand worldwide discovery

The latest [requirements audit and deletions](docs/REQUIREMENTS_AUDIT.md) removes
3D rendering, duplicate initial valuations/discovery calls, automatic footprint
requests and startup presentation panels. Optional tools run when requested.

Automatic Brave web-search and optional Google 360° Street View
integration are now available behind API-key configuration. Explicit OSM building
footprint lookup requests only a 125 m area around the selected address; source
failures leave drawing/import available. No parcel is invented from a building
outline. See [configuration, tested behavior and exclusions](docs/SOURCE_INTEGRATIONS.md).

After selecting an address, use **Measure plot or building outline**. Draw the
boundary on the map or import one Polygon GeoJSON outline, then finish to obtain
WGS84 area in m²/ft², perimeter and a saved coordinate receipt. Google satellite
view is available through an external location link. Measurements remain unverified
until boundary provenance is established and never automatically become floor area.
See [measurement, source and appraisal research](docs/PROPERTY_MEASUREMENT_RESEARCH.md).

The primary journey is now **enter address → resolve/select property → valuation**.
The app does not preload or draw a worldwide property-dot layer. Supported address
suggestions are fetched in batches of at most 20; ambiguous block/type matches
require selection. Comparable markers are off by default and can be enabled for
the selected valuation. A tilted map and an external Mapillary imagery link are
available; photorealistic 3D buildings and embedded street panoramas are not implemented.

The map panel now also includes **On-demand property intelligence**. It automatically
queries applicable NYC official sales, accepts public listing URLs, extracts and
classifies structured evidence, detects duplicates, scores comparability, and saves
complete evidence receipts. See [implemented behavior and limits](docs/ON_DEMAND_INTELLIGENCE.md).

Click anywhere on the world map or select a worldwide address search result.
The client calls `POST /evidence/discover` with latitude/longitude. The server
fetches OpenStreetMap/Nominatim address evidence only on demand, shares a
one-request-per-second limit with address search, and caches successful lookups
on disk for 24 hours. Source errors are shown and are not cached. No paid API key
is needed. OpenStreetMap addresses are map evidence, not verified sale records.

In Singapore, the source adapter offers nearby official HDB block/type profiles
within 100 metres for explicit selection. Selection runs the existing valuation
pipeline and saves its reproducible evidence receipt. A nearby building is never
silently treated as the selected apartment. Elsewhere the lookup returns
insufficient evidence: worldwide address discovery is implemented; worldwide
transaction connectors and reliable valuations are not yet implemented.

The existing official Singapore archives remain available for historical tests,
calibration and reproducibility. On-demand retrieval does not replace those
requirements. New market adapters must provide verified sales, characteristics,
currency, provenance, date semantics and historical validation before enabling
estimates. Discovery cache files are ignored by Git under `data/evidence-cache`.
