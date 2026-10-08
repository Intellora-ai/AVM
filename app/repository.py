"""Immutable input snapshot with PostGIS persistence and append-only valuation receipts."""
import json, os, hashlib
from pathlib import Path
from datetime import date
import psycopg
from psycopg.types.json import Jsonb
from .models import Property, Sale

ROOT = Path(__file__).resolve().parents[1]
class Repository:
    def __init__(self):
        self.snapshot = json.loads((ROOT/'data/snapshot.json').read_text())
        self.properties = {p['property_id']: Property(**p) for p in self.snapshot['properties']}
        self.sales = [Sale(**s) for s in self.snapshot['sales']]
        self.url = os.environ.get('DATABASE_URL')
        if self.url:
            with psycopg.connect(self.url) as db:
                db.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                db.execute("CREATE TABLE IF NOT EXISTS avm_snapshots(version text PRIMARY KEY, payload jsonb NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS avm_sales(version text, id text, sale_date date, location geography(Point,4326), payload jsonb, PRIMARY KEY(version,id))")
                db.execute("CREATE INDEX IF NOT EXISTS avm_sales_geo ON avm_sales USING gist(location)")
                db.execute("CREATE TABLE IF NOT EXISTS avm_receipts(id text PRIMARY KEY, payload jsonb NOT NULL)")
                db.execute("INSERT INTO avm_snapshots VALUES (%s,%s) ON CONFLICT DO NOTHING",(self.version,Jsonb(self.snapshot)))
                with db.cursor() as cur:
                    cur.executemany("INSERT INTO avm_sales VALUES (%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,%s) ON CONFLICT DO NOTHING",[(self.version,s.sale_id,s.sale_date,s.longitude,s.latitude,Jsonb(s.model_dump(mode='json'))) for s in self.sales])

    @property
    def version(self): return self.snapshot['data_version']
    def nearby(self, target, on):
        if not self.url: return [s for s in self.sales if s.sale_date < on]
        with psycopg.connect(self.url) as db:
            rows = db.execute("SELECT payload FROM avm_sales WHERE version=%s AND sale_date < %s AND ST_DWithin(location,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,2000)",(self.version,on,target.longitude,target.latitude)).fetchall()
        return [Sale(**r[0]) for r in rows]
    def save(self,result):
        payload=result.model_dump(mode='json')
        key=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        payload['valuation_id']=key
        if self.url:
            with psycopg.connect(self.url) as db: db.execute("INSERT INTO avm_receipts VALUES (%s,%s) ON CONFLICT DO NOTHING",(key,Jsonb(payload)))
        else:
            directory=ROOT/'data/receipts'; directory.mkdir(exist_ok=True)
            path=directory/(key+'.json')
            if not path.exists(): path.write_text(json.dumps(payload))
        return payload
    def receipt(self,key):
        if self.url:
            with psycopg.connect(self.url) as db:
                row=db.execute("SELECT payload FROM avm_receipts WHERE id=%s",(key,)).fetchone()
                return row[0] if row else None
        path=ROOT/'data/receipts'/(key+'.json')
        return json.loads(path.read_text()) if path.exists() else None
