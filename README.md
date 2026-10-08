# AVM — residential evidence explorer

Interactive MapLibre/OpenStreetMap map, address search, block detail panel, recorded sale evidence, calibrated comparable estimates, scenario forecasts and saved JSON receipts.

## Run on Mac

Install Python 3 and Node.js LTS once. From Terminal:

```bash
git clone https://github.com/Intellora-ai/AVM.git
cd AVM
bash start.command
```

If already cloned: `cd ~/AVM && git pull --ff-only && bash start.command`.

Open **http://localhost:8000**. Keep the terminal open. One server serves both frontend and API. This local mode uses the immutable JSON data snapshot and stores receipts in ignored `data/receipts/`.

## PostgreSQL/PostGIS mode

With Docker Desktop running:

```bash
docker compose up --build
```

Open the same address. This runs the actual spatial comparable query in PostGIS and persists input snapshots and valuation receipts in a named volume. Development API can also use `DATABASE_URL=postgresql://avm:avm@localhost:55432/avm`.

## Data and precise limits

The included public-mirror snapshot contains 2,672 Singapore HDB 4-room block profiles and 3,852 resale records through **November 2025**. Every sale retains its pinned original file and row reference. SHA-256 source hashes and a content version are retained in the snapshot. Data acquisition is reproducible with `python3 scripts/import_hdb.py`.

**This is a block-profile research preview, not the completed individual-property MVP.** HDB does not disclose unit IDs. A block's multiple sales cannot be represented as one apartment's sale history. Profile floor area is the median of available block sales, not a verified individual flat size. Bedrooms and bathrooms remain unknown. The public mirror is incomplete and has not been independently reconciled with the official dataset. Official download access was blocked by the cloud network policy. No transaction is labelled independently verified.

The default date is today. Data older than 180 days causes an explicit insufficient-evidence response. Click **Explore at latest dataset date** to inspect a historical estimate. Example: search **173 ANG MO KIO AVE 4**, select it, then use the dataset-date button. This does not claim a current market value.

## Model

Pure functions in `app/valuation.py` select up to 12 earlier sales within 2km, same type, size ratio >= .75; exclude the subject block; require five sales across three other blocks. A city/type median price-per-m² trend adjusts prices, weighted by size similarity, distance and age. The sample's changing mix may bias this trend; it is not an official index.

Ranges use the 90th percentile of absolute log prediction errors from up to 80 strictly earlier rolling predictions, requiring 20 usable results. These are historical calibration errors, not a guarantee of 90% future coverage. Forecasts compound the observed annual trend (capped at ±20% log growth) and widen the residual range with horizon. They are conditional scenarios, not independently validated forecasts. Confidence is an evidence-quality label, not a probability.

Snapshot version, data cutoff, model version, source rows, comparable adjustments and complete output are preserved in content-addressed valuation receipts. POST `/valuations` then GET `/valuations/{valuation_id}`.

## Validation

```bash
.venv/bin/python -m pytest -q
cd frontend && npm ci && npm run build
```

Tests cover temporal leakage, calibration, forecasts, sparse/stale evidence, missing size, property search and receipt retrieval. Real market accuracy and live forecast coverage remain unvalidated.

## Attribution

Sales mirror: [Claratxy/HDB-Resale-Rest-API](https://github.com/Claratxy/HDB-Resale-Rest-API), MIT, copyright 2026 Tan Xin Yue; original source HDB/data.gov.sg. Coordinates: [ayaka14732/singapore-hdb-map](https://github.com/ayaka14732/singapore-hdb-map), derived from HDB Property Information and Singapore Land Authority OneMap. Exact pinned URLs are in `data/snapshot.json`. Upstream data terms apply; the application MIT license does not relicense third-party data. Map tiles © OpenStreetMap contributors; respect the public tile service policy. Production can substitute a self-hosted raster tile URL.
