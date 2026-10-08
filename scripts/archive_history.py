"""Reuse the official downloader and retain the four earlier official HDB CSVs."""
import argparse,gzip,hashlib,json
from pathlib import Path
from import_hdb import ROOT,download
IDS=['d_43f493c6c50d54243cc1eab0df142d6a','d_2d5ff9ea31397b66239f245f57751537','d_ebc5ab87086db484f88045b47411ebc5','d_ea9ed51da2787afaf8e51f827c304208']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-directory');args=parser.parse_args()
    manifest=[]
    for dataset in IDS:
        raw=(Path(args.from_directory)/(dataset+'.csv')).read_bytes() if args.from_directory else download(dataset)
        digest=hashlib.sha256(raw).hexdigest();filename='history-'+digest+'.csv.gz'
        (ROOT/'data'/filename).write_bytes(gzip.compress(raw,mtime=0))
        manifest.append({'dataset_id':dataset,'sha256':digest,'file':filename,'source':'https://data.gov.sg/datasets/'+dataset+'/view','rows':len(raw.splitlines())-1})
    (ROOT/'data/history_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(sum(m['rows'] for m in manifest),'earlier official records archived')
if __name__=='__main__':main()
