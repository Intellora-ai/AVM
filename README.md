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
