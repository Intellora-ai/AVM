"""Fixed comparable model evaluated on a deterministic later-sales sample."""
import json,hashlib
from datetime import date
from collections import defaultdict
from app_path import ROOT
from app.repository import Repository
from app.models import Property
from app.valuation import point_estimate
from benchmark import metrics
import numpy as np
def main():
    repo=Repository()
    candidates=sorted([s for s in repo.sales if date(2026,1,1)<=s.sale_date<=date(2026,9,30)],key=lambda s:hashlib.sha256(s.sale_id.encode()).hexdigest())[:250]
    actual,pred=[],[]
    for s in candidates:
        target=Property(property_id=s.property_id,latitude=s.latitude,longitude=s.longitude,area_sqm=s.area_sqm,property_type=s.property_type,neighbourhood=s.neighbourhood)
        market=repo.groups[(s.neighbourhood,s.property_type)]
        estimate,_=point_estimate(target,market,s.sale_date,repo.nearby(target,s.sale_date))
        if estimate is not None:actual.append(s.price);pred.append(estimate)
    report={'snapshot_version':repo.snapshot['data_version'],'sample_rule':'First 250 January–September 2026 records by SHA-256 sale ID; fixed before scoring','sample_count':len(candidates),'valued_count':len(pred),'abstained_count':len(candidates)-len(pred),'metrics':metrics(np.array(actual),np.array(pred)),'limitations':'Known sold-flat area. Earlier-date comparisons only; no formal interval or forecast evaluation here. This sample is not the full ML test cohort.'}
    (ROOT/'data/comparable_benchmark.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
if __name__=='__main__':main()
