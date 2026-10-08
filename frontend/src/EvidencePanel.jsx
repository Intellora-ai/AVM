import React, {useEffect,useState} from 'react';

export default function EvidencePanel({latitude,longitude,address,propertyId,currency='USD',onLocationEvidence}) {
  const [urls,setUrls]=useState(''),[area,setArea]=useState(''),[unit,setUnit]=useState(currency),[yieldRate,setYieldRate]=useState('');
  const [result,setResult]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [propertyType,setPropertyType]=useState('residential'),[areaUnit,setAreaUnit]=useState('sqm');
  const [chosenProfile,setChosenProfile]=useState(null);
  async function run(signal, initial=false) {
    setBusy(true);setError('');
    try {
      const response=await fetch('/intelligence',{method:'POST',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude,longitude,address:address||'',property_id:propertyId||chosenProfile?.property_id||null,property_type:initial?'residential':propertyType,currency:chosenProfile?.currency||(initial?currency:unit),...(!initial&&area?{[areaUnit==='sqft'?'area_sqft':'area_sqm']:Number(area)}:{}),annual_gross_yield:initial?null:yieldRate?Number(yieldRate)/100:null,source_urls:initial?[]:urls.split(/\n/).map(u=>u.trim()).filter(Boolean)})});
      const body=await response.json();if(!response.ok)throw Error(typeof body.detail==='string'?body.detail:'Check the supplied inputs and URLs.');
      if(!signal?.aborted){setResult(body);onLocationEvidence?.(body.location_evidence)}
    }catch(e){if(e.name!=='AbortError')setError(e.message)}finally{if(!signal?.aborted)setBusy(false)}
  }
  useEffect(()=>{const controller=new AbortController();setResult(null);setChosenProfile(null);setUrls('');setArea('');setAreaUnit('sqm');setYieldRate('');setUnit(currency);setBusy(false);if(!propertyId)run(controller.signal,true);return()=>controller.abort()},[latitude,longitude,propertyId,currency]);
  useEffect(()=>{if(chosenProfile)run()},[chosenProfile]);
  const format=n=>n==null?'Unavailable':new Intl.NumberFormat('en',{style:'currency',currency:result?.property.currency||unit,maximumFractionDigits:0}).format(n);
  return <section><h2>On-demand property intelligence</h2><p>Fetch published source evidence for this location. Sale transactions, asking prices and rents remain separate.</p>
    <label>Public listing/source URLs (one per line, maximum 8)<textarea aria-label="Source URLs" rows="3" value={urls} onChange={e=>setUrls(e.target.value)} placeholder="https://…" style={{width:'100%'}}/></label>
    <label>Target floor area<input aria-label="Evidence floor area" type="number" min="1" value={area} onChange={e=>setArea(e.target.value)}/></label>
    <label>Area unit<select aria-label="Evidence area unit" value={areaUnit} onChange={e=>{const next=e.target.value;if(area&&Number.isFinite(Number(area)))setArea(String(Number((Number(area)*(next==='sqft'?1/0.09290304:0.09290304)).toPrecision(12))));setAreaUnit(next)}}><option value="sqm">m²</option><option value="sqft">ft²</option></select></label>
    <label>Residential type<select value={propertyType} onChange={e=>setPropertyType(e.target.value)}><option value="residential">Unknown</option><option value="house">House</option><option value="apartment">Apartment</option></select></label>
    <label>Currency<select aria-label="Evidence currency" value={unit} onChange={e=>setUnit(e.target.value)}>{['USD','SGD','EUR','GBP','INR','AUD','CAD','AED','JPY'].map(c=><option key={c}>{c}</option>)}</select></label>
    <label>Assumed annual gross rental yield (%; optional)<input aria-label="Gross yield" type="number" min="0.5" max="30" value={yieldRate} onChange={e=>setYieldRate(e.target.value)}/></label>
    <button className="secondary" disabled={busy} onClick={()=>run()}>{busy?'Gathering source evidence…':'Fetch and analyse evidence'}</button>
    {error&&<p role="alert">{error}</p>}
    {result&&<><p className="notice">{result.estimated_value?`Transaction-backed estimate: ${format(result.estimated_value)}`:'Insufficient evidence for a reliable property valuation.'} {result.confidence_reason}</p>
      {!propertyId&&!chosenProfile&&result.location_evidence?.matches.length>0&&<><p>Select the residential type in this building to value it:</p>{result.location_evidence.matches.map(m=><button className="secondary" key={m.property.property_id} onClick={()=>{setChosenProfile(m.property);setUnit(m.property.currency)}}>{m.property.address} · {m.property.property_type}</button>)}</>}
      {chosenProfile&&<p>Selected profile: {chosenProfile.address} · {chosenProfile.property_type}.</p>}
      {result.transaction_valuation?.price_per_sqft!=null&&<p>{format(result.transaction_valuation.price_per_sqm)}/m² · {format(result.transaction_valuation.price_per_sqft)}/ft²</p>}
      <p>{result.evidence.length} unique records · {result.duplicates.length} duplicates removed</p>
      <details open><summary>Automatic web search · {result.web_search?.status||'unavailable'}</summary>{result.web_search?.reason&&<p>{result.web_search.reason}</p>}{result.web_search?.results.map(r=><article key={r.url}><a href={r.url} target="_blank" rel="noreferrer">{r.title||r.url}</a><span>{r.description}</span><small>Search result; price and property identity are unverified.</small></article>)}</details>
      {result.signals.map(s=><article key={s.method}><b>{s.method}: {format(s.value)}</b><span>Observed dispersion {format(s.observed_low)} – {format(s.observed_high)}</span><span>{s.assumption} Unvalidated supporting indication.</span></article>)}
      {result.signal_disagreement!=null&&<p>Signal disagreement: {Math.round(result.signal_disagreement*100)}%</p>}
      {result.source_results.map((s,i)=><p key={i}><a href={s.url} target="_blank" rel="noreferrer">{s.url}</a><br/>{s.status}{s.rows_received!=null&&` · ${s.rows_received} fetched / ${s.usable_one_family_records} usable single-family records`}</p>)}
      <details><summary>Evidence and comparison exclusions</summary>{result.evidence.map(r=><article key={r.evidence_id}><b>{r.type.replaceAll('_',' ')} · {new Intl.NumberFormat('en',{style:'currency',currency:r.currency,maximumFractionDigits:0}).format(r.price)}</b><span>{r.address||'Address unavailable'} · {r.area_sqm?Math.round(r.area_sqm)+' m²':'Area unavailable'} · {r.source_date||'Date unavailable'}</span><span>{r.classification_basis}</span><span>{r.location_scope}</span><a href={r.source_url} target="_blank" rel="noreferrer">Published source</a></article>)}{result.rejected_evidence.map(r=><p key={r.evidence_id}>{r.reason}</p>)}</details>
      <details><summary>Coverage and reproducibility</summary>{result.limitations.map(l=><p key={l}>{l}</p>)}<p>{result.model_version} · {result.retrieved_at}</p><a href={'/intelligence/'+result.receipt_id} target="_blank" rel="noreferrer">Saved complete evidence receipt (JSON)</a></details>
    </>}
  </section>;
}
