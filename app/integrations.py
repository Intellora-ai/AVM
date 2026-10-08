"""Credential-gated search and imagery. Search snippets are discovery, not sales."""
import os,time,threading
from datetime import datetime,timezone
from urllib.parse import urlsplit
import httpx

_cache={}
_lock=threading.Lock()

def search_address(address,neighbourhood=''):
    key=os.environ.get('BRAVE_SEARCH_API_KEY')
    if not key:return {'status':'not configured','provider':'Brave Search','results':[],'reason':'BRAVE_SEARCH_API_KEY is required.'}
    clean=address.strip().replace('"',' ')[:300]
    if not clean:return {'status':'address required','provider':'Brave Search','results':[]}
    cache_key=(clean,neighbourhood[:100])
    with _lock:
        cached=_cache.get(cache_key)
        if cached and time.monotonic()-cached[0]<21600:return {**cached[1],'cache_hit':True}
    queries=[f'"{clean}" {term}' for term in ('sale','property','price')]
    if neighbourhood:queries.append(f'"{neighbourhood[:100]}" recent property sales')
    results={};failed=0
    with httpx.Client(timeout=10) as client:
        for query in queries:
            try:
                response=client.get('https://api.search.brave.com/res/v1/web/search',params={'q':query,'count':5},headers={'X-Subscription-Token':key,'Accept':'application/json'})
                response.raise_for_status()
                for row in response.json().get('web',{}).get('results',[]):
                    url=row.get('url','');parsed=urlsplit(url)
                    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:continue
                    identity=(parsed.netloc.lower(),parsed.path.rstrip('/'))
                    if identity not in results:results[identity]={'url':url,'title':row.get('title',''),'description':row.get('description',''),'queries':[query],'evidence_type':'search result; unverified'}
                    elif query not in results[identity]['queries']:results[identity]['queries'].append(query)
            except (httpx.HTTPError,ValueError,TypeError):failed+=1
    ranked=sorted(results.values(),key=lambda row:len(row['queries']),reverse=True)[:12]
    result={'status':'ok' if not failed else 'partial' if ranked else 'unavailable','provider':'Brave Search','queries':queries,'results':ranked,'failed_queries':failed,'cache_hit':False,'retrieved_at':datetime.now(timezone.utc).isoformat()}
    if ranked:
        with _lock:
            if len(_cache)>=256:_cache.pop(next(iter(_cache)))
            _cache[cache_key]=(time.monotonic(),result)
    return result

def imagery(latitude,longitude):
    server_key=os.environ.get('GOOGLE_MAPS_SERVER_KEY') or os.environ.get('GOOGLE_MAPS_API_KEY')
    browser_key=os.environ.get('GOOGLE_MAPS_BROWSER_KEY')
    result={'street_view':'not configured','browser_key':browser_key,'three_d_enabled':bool(browser_key and os.environ.get('GOOGLE_3D_TILES_ENABLED')=='true'),'fallbacks':['satellite viewer','OpenStreetMap','imported building footprints']}
    if server_key:
        try:
            response=httpx.get('https://maps.googleapis.com/maps/api/streetview/metadata',params={'location':f'{latitude},{longitude}','radius':50,'key':server_key},timeout=10)
            response.raise_for_status();data=response.json()
            status=data.get('status','UNKNOWN_ERROR')
            result['street_view']='available' if status=='OK' and browser_key else 'browser key required' if status=='OK' else 'no coverage' if status=='ZERO_RESULTS' else 'unavailable'
            if status=='OK':result.update({'panorama_id':data.get('pano_id'),'imagery_date':data.get('date'),'copyright':data.get('copyright'),'panorama_location':data.get('location')})
        except (httpx.HTTPError,ValueError):result['street_view']='unavailable'
    return result
