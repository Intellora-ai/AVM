import React, {useEffect,useState} from 'react';

export default function EvidencePanel({latitude,longitude,address,propertyId,currency='USD'}) {
  const [urls,setUrls]=useState(''),[area,setArea]=useState(''),[unit,setUnit]=useState(currency),[yieldRate,setYieldRate]=useState('');
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [propertyType,setPropertyType]=useState('residential');
  async function run(signal, initial=false) {
    setBusy(true);setError('');
    try {
      const response=await fetch('/intelligence',{method:'POST',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude,longitude,address:address||'',property_id:propertyId||null,property_type:initial?'residential':propertyType,currency:initial?currency:unit,area_sqm:initial?null:area?Number(area):null,annual_gross_yield:initial?null:yieldRate?Number(yieldRate)/100:null,source_urls:initial?[]:urls.split(/\n/).map(u=>u.trim()).filter(Boolean)})});
      const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Check the supplied inputs and URLs.');
      if(!signal?.aborted)setResult(body);
    }catch(e){if(e.name!=='AbortError')setError(e.message)}finally{if(!signal?.aborted)setBusy(false)}
  }
  useEffect(()=>{const controller=new AbortController();setResult(null);setUrls('');setArea('');setYieldRate('');setUnit(currency);run(controller.signal,true);return()=>controller.abort()},[latitude,longitude,propertyId,currency]);
  const format=n=>n==null?'Unavailable':new Intl.NumberFormat('en',{style:'currency',currency:result?.property.currency||unit,maximumFractionDigits:0}).format(n);
  return <section><h2>On-demand property intelligence</h2><p>Fetch published source evidence for this location. Sale transactions, asking prices and rents remain separate.</p>
    <label>Public listing/source URLs (one per line, maximum 8)<textarea aria-label="Source URLs" rows="3" value={urls} onChange={e=>setUrls(e.target.value)} placeholder="https://…" style={{width:'100%'}}/></label>
    <label>Target floor area (m²)<input aria-label="Evidence floor area" type="number" min="1" value={area} onChange={e=>setArea(e.target.value)}/></label>
    <label>Residential type<select value={propertyType} onChange={e=>setPropertyType(e.target.value)}><option value="residential">Unknown</option><option value="house">House</option><option value="apartment">Apartment</option></select></label>
    <label>Currency<select aria-label="Evidence currency" value={unit} onChange={e=>setUnit(e.target.value)}>{['USD','SGD','EUR','GBP','INR','AUD','CAD','AED','JPY'].map(c=><option key={c}>{c}</option>)}</select></label>
    <label>Assumed annual gross rental yield (%; optional)<input aria-label="Gross yield" type="number" min="0.5" max="30" value={yieldRate} onChange={e=>setYieldRate(e.target.value)}/></label>
    <button className="secondary" disabled={busy} onClick={()=>run()}>{busy?'Gathering source evidence…':'Fetch and analyse evidence'}</button>
    {error&&<p role="alert">{error}</p>}
    {result&&<><p className="notice">{result.estimated_value?`Transaction-backed estimate: ${format(result.estimated_value)}`:'Insufficient evidence for a reliable property valuation.'} {result.confidence_reason}</p>
      <p>{result.evidence.length} unique records · {result.duplicates.length} duplicates removed</p>
      {result.signals.map(s=><article key={s.method}><b>{s.method}: {format(s.value)}</b><span>Observed dispersion {format(s.observed_low)} – {format(s.observed_high)}</span><span>{s.assumption} Unvalidated supporting indication.</span></article>)}
      {result.signal_disagreement!=null&&<p>Signal disagreement: {Math.round(result.signal_disagreement*100)}%</p>}
      {result.source_results.map((s,i)=><p key={i}><a href={s.url} target="_blank" rel="noreferrer">{s.url}</a><br/>{s.status}{s.rows_received!=null&&` · ${s.rows_received} fetched / ${s.usable_one_family_records} usable single-family records`}</p>)}
      <details><summary>Evidence and comparison exclusions</summary>{result.evidence.map(r=><article key={r.evidence_id}><b>{r.type.replaceAll('_',' ')} · {new Intl.NumberFormat('en',{style:'currency',currency:r.currency,maximumFractionDigits:0}).format(r.price)}</b><span>{r.address||'Address unavailable'} · {r.area_sqm?Math.round(r.area_sqm)+' m²':'Area unavailable'} · {r.source_date||'Date unavailable'}</span><span>{r.classification_basis}</span><span>{r.location_scope}</span><a href={r.source_url} target="_blank" rel="noreferrer">Published source</a></article>)}{result.rejected_evidence.map(r=><p key={r.evidence_id}>{r.reason}</p>)}</details>
      <details><summary>Coverage and reproducibility</summary>{result.limitations.map(l=><p key={l}>{l}</p>)}<p>{result.model_version} · {result.retrieved_at}</p><a href={'/intelligence/'+result.receipt_id} target="_blank" rel="noreferrer">Saved complete evidence receipt (JSON)</a></details>
    </>}
  </section>;
}
