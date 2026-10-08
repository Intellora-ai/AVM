"""Immutable input snapshot with PostGIS persistence and append-only valuation receipts."""
import json, os, hashlib, gzip,csv,calendar
from functools import lru_cache
from pathlib import Path
from datetime import date
import psycopg
from psycopg.types.json import Jsonb
from .models import Property, Sale

ROOT = Path(__file__).resolve().parents[1]
class Repository:
    def __init__(self):
        path=ROOT/'data/snapshot.json.gz'
        self.snapshot=json.loads(gzip.decompress(path.read_bytes())) if path.exists() else json.loads((ROOT/'data/snapshot.json').read_text())
        history_path=ROOT/'data/history_manifest.json'
        self.archives=json.loads(history_path.read_text()) if history_path.exists() else []
        self.properties = {p['property_id']: Property(**p) for p in self.snapshot['properties']}
        self.sales = [Sale(**s) for s in self.snapshot['sales']]
        self.groups={}
        self.grid={}
        for s in self.sales:
            self.groups.setdefault((s.neighbourhood,s.property_type),[]).append(s)
            self.grid.setdefault((int(s.latitude/.02),int(s.longitude/.02)),[]).append(s)
        self.url = os.environ.get('DATABASE_URL')
        if self.url:
            with psycopg.connect(self.url) as db:
                db.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                db.execute("CREATE TABLE IF NOT EXISTS avm_snapshots(version text PRIMARY KEY, payload jsonb NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS avm_sales(version text, id text, sale_date date, location geography(Point,4326), payload jsonb, PRIMARY KEY(version,id))")
                db.execute("CREATE INDEX IF NOT EXISTS avm_sales_geo ON avm_sales USING gist(location)")
                db.execute("CREATE TABLE IF NOT EXISTS avm_receipts(id text PRIMARY KEY, payload jsonb NOT NULL)")
                db.execute("INSERT INTO avm_snapshots VALUES (%s,%s) ON CONFLICT DO NOTHING",(self.version,Jsonb({**self.snapshot,'history_manifest':self.archives})))
                existing=db.execute("SELECT count(*) FROM avm_sales WHERE version=%s",(self.version,)).fetchone()[0]
                if existing!=len(self.sales):
                    db.execute("CREATE TEMP TABLE ingest_sales(version text,id text,sale_date date,longitude float,latitude float,payload jsonb)")
                    with db.cursor().copy("COPY ingest_sales FROM STDIN") as copy:
                        for s in self.sales: copy.write_row((self.version,s.sale_id,s.sale_date,s.longitude,s.latitude,Jsonb(s.model_dump(mode='json'))))
                    db.execute("INSERT INTO avm_sales SELECT version,id,sale_date,ST_SetSRID(ST_MakePoint(longitude,latitude),4326)::geography,payload FROM ingest_sales ON CONFLICT DO NOTHING")

    @property
    def version(self):
        if not self.archives:return self.snapshot['data_version']
        return hashlib.sha256((self.snapshot['data_version']+json.dumps(self.archives,sort_keys=True)).encode()).hexdigest()[:16]
    @lru_cache(maxsize=32)
    def historical_sales(self,town,kind):
        rows=[]
        for archive in self.archives:
            with gzip.open(ROOT/'data'/archive['file'],'rt') as stream:
                for line,r in enumerate(csv.DictReader(stream),2):
                    if r['town']!=town or r['flat_type']!=kind:continue
                    pid=hashlib.sha256((r['block']+' '+r['street_name']+'|'+r['flat_type']).encode()).hexdigest()[:16]
                    p=self.properties.get(pid)
                    if p is None:continue
                    year,month=map(int,r['month'].split('-'))
                    rows.append(Sale(sale_id=archive['dataset_id']+'-row-'+str(line),property_id=pid,sale_date=date(year,month,calendar.monthrange(year,month)[1]),price=float(r['resale_price']),area_sqm=float(r['floor_area_sqm']),latitude=p.latitude,longitude=p.longitude,property_type=kind,neighbourhood=town,flat_model=r['flat_model'],storey_range=r['storey_range'],lease_commence_date=int(r['lease_commence_date']),record_month=r['month'],verified=True,source='HDB/data.gov.sg · official published historical resale record',source_reference=archive['source']+'#csv-row-'+str(line),date_basis='approval month' if r['month']<'2012-03' else 'registration month'))
        return rows
    def nearby(self, target, on):
        if not self.url:
            from .valuation import distance_m
            a,b=int(target.latitude/.02),int(target.longitude/.02)
            return [s for i in range(a-2,a+3) for j in range(b-2,b+3) for s in self.grid.get((i,j),[]) if s.sale_date<on and distance_m(target.latitude,target.longitude,s.latitude,s.longitude)<=2000]
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
