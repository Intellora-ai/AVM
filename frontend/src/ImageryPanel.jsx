import React,{useEffect,useState} from 'react';
export default function ImageryPanel({latitude,longitude}){
  const [config,setConfig]=useState(null),[mode,setMode]=useState('fallback');
  useEffect(()=>{const controller=new AbortController();setConfig(null);setMode('fallback');fetch(`/imagery?latitude=${latitude}&longitude=${longitude}`,{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(c=>{setConfig(c);if(c.street_view==='available')setMode('street')}).catch(()=>{if(!controller.signal.aborted)setConfig({street_view:"unavailable",browser_key:null})});return()=>controller.abort()},[latitude,longitude]);
  const params=new URLSearchParams({key:config?.browser_key||''});
  if(mode==='street'){if(config?.panorama_id)params.set('pano',config.panorama_id);else params.set('location',`${latitude},${longitude}`)}else{params.set('center',`${latitude},${longitude}`);params.set('zoom','18');params.set('maptype','satellite')}
  return <section><h2>Optional visual reference</h2><p>Street View: {config?.street_view||'checking availability'}</p>
    {config?.street_view==='available'&&<button className="secondary" onClick={()=>{setMode('street')}}>360° Street View</button>}{' '}
    {config?.browser_key&&<button className="secondary" onClick={()=>{setMode('satellite')}}>Satellite</button>}{' '}
    {config?.browser_key&&mode!=='fallback'?<iframe title={mode==='street'?'Google 360 degree Street View':'Google satellite view'} width="100%" height="320" style={{border:0}} loading="lazy" allowFullScreen referrerPolicy="no-referrer-when-downgrade" src={`https://www.google.com/maps/embed/v1/${mode==='street'?'streetview':'view'}?${params}`}/>:<p className="muted">Google API keys are not configured. OpenStreetMap and outline measurement remain available.</p>}
    <p><a href={`https://www.google.com/maps/@${latitude},${longitude},19z/data=!3m1!1e3`} target="_blank" rel="noreferrer">Open satellite viewer ↗</a></p><p className="muted">Imagery shows visual context, not verified parcel boundaries. Google services require enabled APIs, appropriate keys and applicable billing.</p>
  </section>;
}
