"""Temporal and unseen-block evaluation; existing libraries reused, no hand-built learners."""
import gzip,json,math,os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from pathlib import Path
import sys,joblib,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ml import feature
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
def metrics(actual,pred):
    ratio=pred/actual;error=np.abs(ratio-1)
    return {'count':len(actual),'median_absolute_percentage_error':float(np.median(error)*100),'mean_absolute_percentage_error':float(np.mean(error)*100),'within_10_percent':float(np.mean(error<=.10)),'within_20_percent':float(np.mean(error<=.20)),'median_prediction_sale_ratio':float(np.median(ratio)),'cod':float(np.mean(np.abs(ratio-np.median(ratio)))/np.median(ratio)*100),'mae_currency':float(np.mean(np.abs(actual-pred)))}
def main():
    snapshot=json.loads(gzip.decompress((ROOT/'data/snapshot.json.gz').read_bytes()))
    sales=[s for s in snapshot['sales'] if s['sale_date']<=snapshot['data_date']]
    # A deterministic geographically grouped exclusion checks transfer to unseen blocks.
    # Group every type at the same building coordinate together, avoiding cross-type leakage.
    spatial=lambda s:int(hashlib.sha256((str(round(s['latitude'],6))+','+str(round(s['longitude'],6))).encode()).hexdigest()[:8],16)%10==0
    train=[s for s in sales if s['sale_date']<='2025-06-30' and not spatial(s)]
    cal=[s for s in sales if '2025-06-30'<s['sale_date']<='2025-12-31' and not spatial(s)]
    test=[s for s in sales if '2025-12-31'<s['sale_date']]
    vectorizer=DictVectorizer(sparse=False)
    X=vectorizer.fit_transform([feature(s) for s in train]);Y=np.log([s['price'] for s in train])
    XC=vectorizer.transform([feature(s) for s in cal]);YC=np.array([s['price'] for s in cal])
    XT=vectorizer.transform([feature(s) for s in test]);YT=np.array([s['price'] for s in test])
    models={'log_ridge':make_pipeline(StandardScaler(),Ridge(alpha=100)),'hist_gradient_boosting':HistGradientBoostingRegressor(max_iter=180,max_leaf_nodes=31,l2_regularization=10,learning_rate=.08,early_stopping=False,random_state=42)}
    result={'data_version':snapshot['data_version'],'currency':'SGD','train_through':'2025-06-30','calibration_through':'2025-12-31','test_through':snapshot['data_date'],'spatial_holdout':'Approximately 10% of building coordinates, across every flat type, excluded from training and calibration; reported separately. Not an entire-region holdout.','train_count':len(train),'calibration_count':len(cal),'models':{},'warning':'Published transaction prices, not independently screened arms-length market values. Month precision only. This is a benchmark, not a certified appraisal or proof of global accuracy.'}
    winners={};trained={}
    for name,model in models.items():
        model.fit(X,Y)
        pc=np.exp(model.predict(XC));pt=np.exp(model.predict(XT))
        q=float(np.quantile(np.abs(np.log(YC/pc)),min(1,math.ceil((len(YC)+1)*.9)/len(YC)),method='higher'))
        unseen=np.array([spatial(s) for s in test])
        report={'calibration':metrics(YC,pc),'test':metrics(YT,pt),'unseen_block_test':metrics(YT[unseen],pt[unseen]),'interval_90_nominal_coverage':float(np.mean((YT>=pt*np.exp(-q))&(YT<=pt*np.exp(q)))),'calibration_log_error_quantile':q,'by_type':{}}
        for kind in sorted({s['property_type'] for s in test}):
            mask=np.array([s['property_type']==kind for s in test]);report['by_type'][kind]=metrics(YT[mask],pt[mask])
        result['models'][name]=report
        winners[name]=report['calibration']['median_absolute_percentage_error']
        trained[name]=model
        print(name,json.dumps(report['test']),flush=True)
    result['selected_by_calibration']=min(winners,key=winners.get)
    champion=result['selected_by_calibration']
    artifact=ROOT/'data/champion.joblib'
    joblib.dump({'model':trained[champion],'vectorizer':vectorizer},artifact,compress=3)
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
    meta={'data_version':snapshot['data_version'],'model_version':champion+'-1-'+digest[:12],'valid_from':'2026-01-01','evaluated_through':snapshot['data_date'],'sha256':digest,'calibration_log_error_quantile':result['models'][champion]['calibration_log_error_quantile'],'calibration_count':len(cal),'test_interval_coverage':result['models'][champion]['interval_90_nominal_coverage']}
    (ROOT/'data/model_metadata.json').write_text(json.dumps(meta,indent=2))
    (ROOT/'data/benchmark.json').write_text(json.dumps(result,indent=2))
    print('Benchmark and checksum-protected challenger saved. Application requires user attributes and corroborating comparables.')
if __name__=='__main__':main()
