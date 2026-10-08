"""Build a reproducible snapshot from pinned public mirrors; no invented unit IDs."""
import csv, hashlib, json, calendar, urllib.request
from pathlib import Path
from collections import defaultdict
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'sales': 'https://raw.githubusercontent.com/Claratxy/HDB-Resale-Rest-API/81c7b8d45cfb6832f038d91aa501edb7795f5b84/data/AWD_resale_cleaned.csv',
    'locations': 'https://raw.githubusercontent.com/ayaka14732/singapore-hdb-map/08950a9eca3568eb8b488245cb6db4de0124d451/data/hdb_geocoded.csv',
}

def main():
    folder = ROOT / 'data'
    folder.mkdir(exist_ok=True)
    raw = {k: urllib.request.urlopen(v).read() for k,v in SOURCES.items()}
    geo = {(r['blk_no'],r['street']):r for r in csv.DictReader(raw['locations'].decode().splitlines())}
    sales, groups = [], defaultdict(list)
    for line,r in enumerate(csv.DictReader(raw['sales'].decode().splitlines()),2):
        if r['flat_type'] != '4 ROOM': continue
        g = geo.get((r['block'],r['street_name']))
        if not g or not g['latitude'] or not g['longitude']: continue
        pid = hashlib.sha256((r['block']+' '+r['street_name']).encode()).hexdigest()[:12]
        y,m = map(int,r['transaction_date'][:7].split('-'))
        s = dict(sale_id=f'hdb-row-{line}',property_id=pid,sale_date=f'{y}-{m:02}-{calendar.monthrange(y,m)[1]}',price=float(r['resale_price']),area_sqm=float(r['floor_area_sqm']),latitude=float(g['latitude']),longitude=float(g['longitude']),property_type='4 ROOM',source='HDB resale data via public mirror (not independently verified)',source_reference=SOURCES['sales']+f'#L{line}',verified=False)
        sales.append(s); groups[pid].append((r,g,s))
    properties=[]
    for pid,rows in groups.items():
        r,g,_ = rows[-1]
        properties.append(dict(property_id=pid,latitude=float(g['latitude']),longitude=float(g['longitude']),area_sqm=median(x[2]['area_sqm'] for x in rows),property_type='4 ROOM',address=r['block']+' '+r['street_name']+', Singapore',neighbourhood=r['town'],building='HDB block '+r['block'],source_reference=SOURCES['locations'],year_built=int(g['year_completed']) if g['year_completed'] else None))
    snapshot=dict(properties=properties,sales=sales,sources=SOURCES,data_date=max(s['sale_date'] for s in sales),scope='Singapore · HDB 4-room block profiles',identity_note='Unit numbers are withheld by HDB. These are block/type profiles, not individual apartments. Transactions are block-level evidence; unit-specific history is unavailable.',source_hashes={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()})
    snapshot['data_version']=hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()[:16]
    (folder/'snapshot.json').write_text(json.dumps(snapshot,separators=(',',':')))
    print(f'{len(properties)} block profiles; {len(sales)} resale records; through {snapshot["data_date"]}')

if __name__=='__main__': main()
