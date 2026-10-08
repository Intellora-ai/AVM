# AVM

First working comparable-sales valuation engine. The valuation core is pure Python and has no database or web dependencies, so alternative models can implement the same `ValuationModel` interface later.

## Run

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

`POST /valuations` accepts a property id and valuation date. The demo repository is in-memory; `app/repository.py` contains the PostgreSQL/PostGIS query boundary to replace with a real adapter.

The seeded `demo-001` property makes the MVP immediately usable. Run the API on port 8000 and the frontend with `cd frontend && npm run dev`; Vite proxies API calls to the backend. `docker compose up -d postgres` starts the PostGIS database defined in `db/schema.sql`.

## Data model

`db/schema.sql` defines properties, sales, and market indices using PostGIS `geography(Point,4326)`. Keep database access outside `app/valuation.py` so model experiments remain isolated.
