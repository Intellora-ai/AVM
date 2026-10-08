"""Direct official data.gov.sg acquisition. Stable refs, hashes and original rows retained."""
import argparse, calendar, csv, gzip, hashlib, json, time, urllib.request,subprocess
from pathlib import Path
from datetime import date
from collections import defaultdict
from statistics import median

ROOT=Path(__file__).resolve().parents[1]
SALES_ID='d_8b84c4ee58e3cfc0ece0d773c8ca6abc'
BUILDINGS_ID='d_17f5382f26140b1fdae0ba2ef6239d2f'
GEO_URL='https://raw.githubusercontent.com/ayaka14732/singapore-hdb-map/08950a9eca3568eb8b488245cb6db4de0124d451/data/hdb_geocoded.csv'
def download(dataset):
    base='https://api-open.data.gov.sg/v1/public/api/datasets/'+dataset
    for attempt in range(6):
        status=json.loads(subprocess.check_output(['curl','-fsSL','--max-time','30',base+'/poll-download']))
        data=status.get('data',{})
        if data.get('url'):
            with urllib.request.urlopen(urllib.request.Request(data['url'],headers={'User-Agent':'AVM/1.0'}),timeout=120) as r: return r.read()
        if attempt==0:
            req=urllib.request.Request(base+'/initiate-download',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=30): pass
        time.sleep(2)
    raise RuntimeError('Official download not ready: '+dataset)

def build(sales_raw,buildings_raw,geo_raw):
    buildings={(r['blk_no'],r['street']):r for r in csv.DictReader(buildings_raw.decode().splitlines())}
    geo={(r['blk_no'],r['street']):r for r in csv.DictReader(geo_raw.decode().splitlines())}
    sales,groups=[],defaultdict(list); missing=0
    for line,r in enumerate(csv.DictReader(sales_raw.decode().splitlines()),2):
        key=(r['block'],r['street_name']);g=geo.get(key);b=buildings.get(key)
        if not g or not b or not g['latitude'] or not g['longitude']:
            missing+=1;continue
        pid=hashlib.sha256((r['block']+' '+r['street_name']+'|'+r['flat_type']).encode()).hexdigest()[:16]
        y,m=map(int,r['month'].split('-'))
        # Reported months have no exact transaction day: use month-end conservatively.
        when=f'{y}-{m:02}-{calendar.monthrange(y,m)[1]}'
        source='https://data.gov.sg/datasets/'+SALES_ID+'/view'
        sale=dict(sale_id=f'hdb-row-{line}',property_id=pid,sale_date=when,record_month=r['month'],price=float(r['resale_price']),area_sqm=float(r['floor_area_sqm']),latitude=float(g['latitude']),longitude=float(g['longitude']),property_type=r['flat_type'],source='HDB/data.gov.sg · official published resale record',source_reference=source+f'#csv-row-{line}',verified=True,neighbourhood=r['town'],flat_model=r['flat_model'],storey_range=r['storey_range'],lease_commence_date=int(r['lease_commence_date']))
        sales.append(sale);groups[pid].append((r,b,g,sale))
    properties=[]
    for pid,rows in groups.items():
        r,b,g,_=rows[-1]
        properties.append(dict(property_id=pid,latitude=float(g['latitude']),longitude=float(g['longitude']),area_sqm=median(x[3]['area_sqm'] for x in rows),property_type=r['flat_type'],address=r['block']+' '+r['street_name']+', Singapore',neighbourhood=r['town'],building='HDB block '+r['block'],source_reference='https://data.gov.sg/datasets/'+BUILDINGS_ID+'/view',year_built=int(b['year_completed']) if b['year_completed'] else None))
    today=date.today()
    completed=[s['sale_date'] for s in sales if date.fromisoformat(s['sale_date'])<today]
    sources=dict(sales='https://data.gov.sg/datasets/'+SALES_ID+'/view',buildings='https://data.gov.sg/datasets/'+BUILDINGS_ID+'/view',coordinates=GEO_URL)
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in [('sales',sales_raw),('buildings',buildings_raw),('coordinates',geo_raw)]}
    snapshot=dict(properties=properties,sales=sales,sources=sources,data_date=max(completed),reported_through=max(s['record_month'] for s in sales),retrieved_at=today.isoformat(),scope='Singapore · all published HDB residential resale flat types',identity_note='HDB withholds unit identities. Select a block/type and enter the flat area; recorded sales are within that block/type, not a specific apartment history.',source_hashes=hashes,excluded_missing_locations=missing,official_sales=True,coordinate_note='Coordinates are OneMap-derived through a pinned public mirror, joined on exact block/street to official building records.')
    snapshot['data_version']=hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()[:16]
    return snapshot
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sales');parser.add_argument('--buildings');parser.add_argument('--coordinates');args=parser.parse_args()
    raw_sales=Path(args.sales).read_bytes() if args.sales else download(SALES_ID)
    raw_buildings=Path(args.buildings).read_bytes() if args.buildings else download(BUILDINGS_ID)
    raw_geo=Path(args.coordinates).read_bytes() if args.coordinates else urllib.request.urlopen(GEO_URL).read()
    snapshot=build(raw_sales,raw_buildings,raw_geo)
    folder=ROOT/'data';folder.mkdir(exist_ok=True)
    for k,v in [('sales',raw_sales),('buildings',raw_buildings),('coordinates',raw_geo)]:
        (folder/(k+'-'+snapshot['source_hashes'][k]+'.csv.gz')).write_bytes(gzip.compress(v,mtime=0))
    payload=json.dumps(snapshot,separators=(',',':')).encode()
    (folder/'snapshot.json.gz').write_bytes(gzip.compress(payload,mtime=0))
    print(json.dumps({k:snapshot[k] for k in ('data_date','reported_through','data_version','excluded_missing_locations')}))
    print(len(snapshot['properties']),'profiles;',len(snapshot['sales']),'official resale records')
if __name__=='__main__':main()
