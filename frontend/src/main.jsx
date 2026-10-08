import React, {useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';
import EvidencePanel from './EvidencePanel';
const money=n=>n==null?'Unavailable':new Intl.NumberFormat('en-SG',{style:'currency',currency:'SGD',maximumFractionDigits:0}).format(n);
async function api(path,options){const r=await fetch(path,options);if(!r.ok)throw Error((await r.json()).detail||'Request failed');return r.json();}
function Timeline({result}){
  const history=result.historical_transactions;
  const points=history.map(s=>({time:Date.parse(s.sale_date),value:s.price,type:'fact'}));
  if(result.estimated_value)points.push({time:Date.parse(result.valuation_date),value:result.estimated_value,type:'estimate'});
  const future=result.forecasts.map(f=>{const d=new Date(result.valuation_date);d.setMonth(d.getMonth()+f.months);return {...f,time:+d,value:f.central,type:'forecast'}});
  points.push(...future);if(!points.length)return <p>No timeline evidence available.</p>;
  const minT=Math.min(...points.map(p=>p.time)),maxT=Math.max(...points.map(p=>p.time));
  const maxV=Math.max(...points.map(p=>p.upper||p.value))*1.12;
  const x=t=>50+(t-minT)/Math.max(86400000,maxT-minT)*470,y=v=>170-v/maxV*140;
  return <><svg viewBox="0 0 560 205" role="img" aria-label="Historical sale dots, current estimate diamond and dashed future scenario range">
    {[.25,.5,.75,1].map(n=><g key={n}><line x1="50" x2="530" y1={y(maxV*n)} y2={y(maxV*n)} stroke="#e2e8ed"/><text x="0" y={y(maxV*n)} fontSize="9">{Math.round(maxV*n/1000)}k</text></g>)}
    {future.length>0&&<polyline points={[{time:Date.parse(result.valuation_date),value:result.estimated_value},...future].map(p=>x(p.time)+','+y(p.value)).join(' ')} fill="none" stroke="#a45cc4" strokeDasharray="5 5"/>}
    {points.map((p,i)=><g key={i}><title>{p.type}: {money(p.value)}</title>{p.type==='forecast'?<><line x1={x(p.time)} x2={x(p.time)} y1={y(p.lower)} y2={y(p.upper)} stroke="#a45cc4" strokeWidth="5" opacity=".3"/><circle cx={x(p.time)} cy={y(p.value)} r="4" fill="white" stroke="#a45cc4"/></>:p.type==='estimate'?<path d={'M '+x(p.time)+' '+(y(p.value)-7)+' l 7 7 -7 7 -7 -7 Z'} fill="#d27c22"/>:<circle cx={x(p.time)} cy={y(p.value)} r="4" fill="#167774"/>}</g>)}
    <text x="50" y="196" fontSize="11">{new Date(minT).getFullYear()}</text><text x="490" y="196" fontSize="11">{new Date(maxT).getFullYear()}</text>
  </svg><p className="muted">● Recorded block sales · ◆ Estimate · ◌ Forecast scenarios</p></>;
}
function App(){
  const [properties,setProperties]=useState([]),[meta,setMeta]=useState(null),[query,setQuery]=useState(''),[selected,setSelected]=useState(null),[result,setResult]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [on,setOn]=useState(new Date().toISOString().slice(0,10)),[mapError,setMapError]=useState('');
  const [area,setArea]=useState(''),[floor,setFloor]=useState(''),[flatModel,setFlatModel]=useState(''),[location,setLocation]=useState(null),[coverage,setCoverage]=useState(null),[globalPlaces,setGlobalPlaces]=useState([]),[bench,setBench]=useState(null),[evidence,setEvidence]=useState(null),[discovering,setDiscovering]=useState(false);
  const container=useRef(null),map=useRef(null),requestId=useRef(0);
  useEffect(()=>{Promise.all([api('/properties'),api('/metadata'),api('/coverage'),api('/benchmark')]).then(([p,m,c,b])=>{setProperties(p);setMeta(m);setCoverage(c);setBench(b)}).catch(e=>setError(e.message))},[]);
  useEffect(()=>{
    const m=new maplibregl.Map({container:container.current,center:[10,20],zoom:1.5,style:{version:8,sources:{world:{type:'geojson',data:'/world.geojson'},osm:{type:'raster',tiles:[import.meta.env.VITE_TILE_URL||window.location.origin+'/basemap/world/{z}/{x}/{y}.png'],tileSize:256,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · Natural Earth'},onemap:{type:'raster',tiles:[window.location.origin+'/basemap/sg/{z}/{x}/{y}.png'],tileSize:256,bounds:[103.59,1.13,104.12,1.48],minzoom:9,maxzoom:18,attribution:'© <a href="https://www.onemap.gov.sg/">Singapore Land Authority OneMap</a>'}},layers:[{id:'ocean',type:'background',paint:{'background-color':'#dcebf0'}},{id:'countries',type:'fill',source:'world',paint:{'fill-color':'#eef1e8'}},{id:'borders',type:'line',source:'world',paint:{'line-color':'#adc0bd','line-width':1}},{id:'basemap',type:'raster',source:'osm'},{id:'official-sg',type:'raster',source:'onemap'}]}});
    map.current=m;m.addControl(new maplibregl.NavigationControl());m.addControl(new maplibregl.FullscreenControl());
    m.on('error',()=>setMapError('Some street tiles could not load. Try again shortly; Singapore also uses the official OneMap basemap.'));
    m.on('click',e=>{if(m.getLayer('homes')&&m.queryRenderedFeatures(e.point,{layers:['homes']}).length)return;setSelected(null);setLocation({name:'Selected map location',lat:e.lngLat.lat,lon:e.lngLat.lng});setResult(null)});
    return()=>m.remove();
  },[]);
  useEffect(()=>{
    if(!properties.length)return;const m=map.current;let cancelled=false;
    const draw=()=>{
      if(cancelled)return;
      const data={type:'FeatureCollection',features:properties.map(p=>({type:'Feature',geometry:{type:'Point',coordinates:[p.longitude,p.latitude]},properties:{id:p.property_id,address:p.address}}))};
      if(m.getSource('homes'))m.getSource('homes').setData(data);else{
        m.addSource('homes',{type:'geojson',data});
        m.addLayer({id:'homes',type:'circle',source:'homes',paint:{'circle-radius':6,'circle-color':'#167774','circle-stroke-color':'white','circle-stroke-width':2}});
        m.on('click','homes',e=>{const p=properties.find(p=>p.property_id===e.features[0].properties.id);setLocation(null);setArea('');setFloor('');setFlatModel('');setSelected(p);});
        m.on('mouseenter','homes',()=>m.getCanvas().style.cursor='pointer');m.on('mouseleave','homes',()=>m.getCanvas().style.cursor='');
      }
    };if(m.isStyleLoaded())draw();else m.once('load',draw);return()=>{cancelled=true;m.off('load',draw)};
  },[properties]);
  useEffect(()=>{
    if(!selected){requestId.current++;setBusy(false);return;}const n=++requestId.current;setBusy(true);setError('');
    map.current.flyTo({center:[selected.longitude,selected.latitude],zoom:15});
    api('/valuations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({property_id:selected.property_id,valuation_date:on,area_sqm:area?Number(area):null,storey_range:floor||null,flat_model:flatModel||null})}).then(r=>{if(n===requestId.current)setResult(r)}).catch(e=>{if(n===requestId.current)setError(e.message)}).finally(()=>{if(n===requestId.current)setBusy(false)});
  },[selected,on,area,floor,flatModel]);
  useEffect(()=>{
    const markers=[];const m=map.current;
    if(selected)markers.push(new maplibregl.Marker({color:'#dc7d20'}).setLngLat([selected.longitude,selected.latitude]).addTo(m));
    else if(location)markers.push(new maplibregl.Marker({color:'#dc7d20'}).setLngLat([location.lon,location.lat]).addTo(m));
    if(selected)result?.comparable_sales_used.forEach(c=>markers.push(new maplibregl.Marker({color:'#7957a4',scale:.7}).setLngLat([c.longitude,c.latitude]).setPopup(new maplibregl.Popup().setText(money(c.original_price)+' · '+c.area_sqm+' m² · '+c.sale_date.slice(0,7))).addTo(m)));
    return()=>markers.forEach(m=>m.remove());
  },[selected,result,location]);
  useEffect(()=>{
    setEvidence(null);if(!location){setDiscovering(false);return;}
    let active=true;setDiscovering(true);
    api('/evidence/discover',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude:location.lat,longitude:location.lon})})
      .then(r=>{if(active)setEvidence(r)}).catch(e=>{if(active)setError(e.message)})
      .finally(()=>{if(active)setDiscovering(false)});
    return()=>{active=false};
  },[location]);
  const matches=properties.filter(p=>(p.address+' '+p.neighbourhood+' '+p.property_type).toLowerCase().includes(query.toLowerCase())).slice(0,20);
  async function searchWorld(){setError('');try{setGlobalPlaces(await api('/places?q='+encodeURIComponent(query)))}catch(e){setError(e.message)}}
  function choose(p){setLocation(null);setArea('');setFloor('');setFlatModel('');setSelected(p)}
  return <><header><b className="brand">AVM<span> / residential evidence</span></b><span>Global map · evidence varies by market</span></header><main>
    <section className="map-pane"><div ref={container} className="map"/><div className="search"><label htmlFor="search">Search supported properties or a world address</label><input id="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search street or neighbourhood…"/><button className="secondary" onClick={searchWorld} disabled={query.length<3}>Search worldwide</button><div className="matches">{globalPlaces.map(p=><button key={p.place_id} onClick={()=>{setSelected(null);setResult(null);setLocation({name:p.display_name,lat:Number(p.lat),lon:Number(p.lon)});map.current.flyTo({center:[Number(p.lon),Number(p.lat)],zoom:15})}}>{p.display_name}</button>)}{matches.map(p=><button key={p.property_id} onClick={()=>choose(p)}>{p.address}<small>{p.neighbourhood} · {p.property_type}</small></button>)}</div></div><div className="map-note">{mapError||'Drag to explore · scroll to zoom · click a green property'}<br/>Orange: selected · purple: comparables</div></section>
    <aside>{!selected?<div className="welcome"><span className="tag">PROPERTY EXPLORER</span><h1>{location?'Selected location':'Find the evidence behind a property’s price.'}</h1>{location&&<><p>{location.name}</p><p>{location.lat.toFixed(5)}, {location.lon.toFixed(5)}</p>{discovering&&<p role="status">Fetching available evidence for this location…</p>}{evidence&&<><p>{evidence.address?.display_name}</p><p className="notice">{evidence.reason}</p>{evidence.matches.map(m=><button className="secondary" key={m.property.property_id} onClick={()=>choose(m.property)}>{m.property.address} · {m.property.property_type} · {m.distance_m} m</button>)}<p className="muted">{evidence.cache_hit?'Cached lookup':'Fresh lookup'} · retrieved {evidence.retrieved_at}{evidence.source_error&&' · '+evidence.source_error}</p></>}</>}<p>Select a supported map point or search an address to see recorded sales, an evidence-based estimate and future scenarios.</p><p>{properties.length.toLocaleString()} supported Singapore block/type profiles · {meta?.scope}.</p><button className="secondary" onClick={()=>map.current.flyTo({center:[103.84,1.35],zoom:11})}>Explore supported Singapore properties</button><p className="notice">{meta?.identity_note}</p><p>Completed-month evidence through {meta?.data_date}.</p><details><summary>Official source coverage</summary>{coverage?.markets.map(c=><p key={c.id}><b>{c.country}</b>: {c.status}<br/>{c.limits}</p>)}</details><details><summary>Measured model accuracy</summary>{bench?.models&&Object.entries(bench.models).map(([name,b])=><p key={name}>{name}: median test error {b.test.median_absolute_percentage_error.toFixed(2)}% on {b.test.count.toLocaleString()} later sales. Applies to known Singapore attributes, not all properties globally.</p>)}</details></div>:<>
      <h1>{selected.address}</h1><p className="muted">{selected.neighbourhood} · {selected.property_type} · {selected.building}</p><div className="facts"><b>{selected.area_sqm} m²</b><span>Representative area from recorded sales</span><span>Bedrooms / bathrooms: unavailable</span><span>Completed: {selected.year_built||'unavailable'}</span></div>
      <p className="notice">{meta?.identity_note}</p><label>Valuation date <input aria-label="Valuation date" type="date" max={new Date().toISOString().slice(0,10)} value={on} onChange={e=>setOn(e.target.value)}/></label>
      <button className="secondary" onClick={()=>{const d=new Date(meta.data_date);d.setDate(d.getDate()+1);setOn(d.toISOString().slice(0,10))}}>Explore at latest dataset date</button>
      <label>Actual flat area (m², optional)<input aria-label="Actual flat area" type="number" min="1" max="2000" value={area} onChange={e=>setArea(e.target.value)} placeholder="Use earlier block records if unknown"/></label>
      <label>Storey range (optional)<select aria-label="Storey range" value={floor} onChange={e=>setFloor(e.target.value)}><option value="">Unknown — comparable model</option>{Array.from({length:17},(_,i)=>String(i*3+1).padStart(2,'0')+' TO '+String(i*3+3).padStart(2,'0')).map(s=><option key={s}>{s}</option>)}</select></label>
      <label>Flat model (optional)<select aria-label="Flat model" value={flatModel} onChange={e=>setFlatModel(e.target.value)}><option value="">Unknown — comparable model</option>{[...new Set(result?.historical_transactions.map(s=>s.flat_model)||[])].filter(Boolean).map(s=><option key={s}>{s}</option>)}</select></label>
      {busy&&<p role="status">Checking sales and historical prediction errors…</p>}{error&&<p role="alert">{error}</p>}
      {result&&<>
        <section><span className="tag estimate">ESTIMATE</span><h2>{result.status==='ok'?money(result.estimated_value):'Insufficient market evidence'}</h2>{result.reason?<p>{result.reason}</p>:<><p>{money(result.lower_bound)} – {money(result.upper_bound)}</p><p>Confidence: {result.confidence_label} (quality indicator, not a probability)</p></>}<p className="muted">As of {result.valuation_date} · representative flat profile</p></section>
        <section><span className="tag">FACT · OFFICIAL RECORDED TRANSACTIONS · BLOCK/TYPE</span><p>Direct HDB/data.gov.sg records. These are sales within this block/type, not the same apartment. Reported month only.</p>{result.historical_transactions.length?result.historical_transactions.map(s=><article key={s.sale_id}><b>{money(s.price)}</b><span>{s.sale_date.slice(0,7)} · {s.area_sqm} m² · {s.storey_range} · {s.date_basis}</span><a href={'/source-records/'+s.sale_id} target="_blank" rel="noreferrer">Original official CSV record ↗</a></article>):<p>No recorded sales available for this block.</p>}</section>
        <section><h2>Price timeline</h2><Timeline result={result}/></section>
        <section><span className="tag forecast">FORECAST · SCENARIOS</span>{result.forecasts.length?<><table><thead><tr><th>Months</th><th>Lower</th><th>Central</th><th>Upper</th></tr></thead><tbody>{result.forecasts.map(f=><tr key={f.months}><td>{f.months}</td><td>{money(f.lower)}</td><td>{money(f.central)}</td><td>{money(f.upper)}</td></tr>)}</tbody></table><p className="muted">{result.forecast_method} These are conditional scenarios, not guaranteed prices.</p></>:<p>Forecasts are unavailable without a supported current estimate.</p>}</section>
        <section><h2>Comparable sales · {result.comparable_sales_used.length}</h2>{result.comparable_sales_used.map(c=><article key={c.sale_id}><b>{properties.find(p=>p.property_id===c.property_id)?.address||c.property_id}</b><span>Recorded {money(c.original_price)} · {c.sale_date.slice(0,7)}</span><span>{c.area_sqm} m² · {Math.round(c.distance_m)} m away · same flat type</span><span>Adjusted: {money(c.adjusted_price)} · {money(c.adjusted_price_per_sqm)}/m²</span><span>Area similarity: {Math.round(c.similarity*100)}%</span><a href={c.source_reference} target="_blank" rel="noreferrer">Source transaction ↗</a></article>)}</section>
        <details><summary>Sources, methodology & reproducibility</summary><p>Data: {result.data_version} · through {result.data_date}</p><p>Method: {result.valuation_method} · model: {result.model_version}</p><p>{result.input_assumptions?.join(' ')}</p><p>{result.interval_method} Calibration predictions: {result.calibration_count}.</p><p>{result.sources.join('; ')}</p><a href={'/valuations/'+result.valuation_id} target="_blank" rel="noreferrer">Open saved valuation receipt (JSON)</a></details>
      </>}
    </>}{!selected&&error&&<p role="alert">{error}</p>}
    {(location||selected)&&<EvidencePanel latitude={location?location.lat:selected.latitude} longitude={location?location.lon:selected.longitude} address={location?location.name:selected.address} propertyId={selected?.property_id} currency={selected?.currency||'USD'}/>}
    </aside>
  </main></>;
}
createRoot(document.getElementById('root')).render(<App/>);
