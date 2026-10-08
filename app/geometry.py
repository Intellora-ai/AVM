"""WGS84 polygon measurements; geometry evidence is distinct from floor area."""
import hashlib, json, math
from datetime import datetime, timezone
from geographiclib.geodesic import Geodesic
from pydantic import BaseModel, Field
from typing import Literal

class MeasurementRequest(BaseModel):
    coordinates: list[tuple[float,float]] = Field(min_length=3,max_length=200)
    area_kind: Literal['building footprint','land parcel'] = 'building footprint'
    source: str = Field(default='user-drawn outline',max_length=300)
    corner_status: Literal['unknown','user confirmed corner','user confirmed not corner'] = 'unknown'

def measure(request):
    coords=request.coordinates[:]
    if coords[0]==coords[-1]:coords.pop()
    if len(set(coords))!=len(coords) or len(coords)<3:raise ValueError('Use at least three distinct vertices without duplicates')
    if any(not math.isfinite(x) or not math.isfinite(y) or not -180<=x<=180 or not -85<=y<=85 for x,y in coords):raise ValueError('Invalid coordinates; measurement supports latitudes within ±85°')
    lat=sum(y for x,y in coords)/len(coords)
    points=[(((x-coords[0][0]+180)%360-180)*111320*math.cos(math.radians(lat)),(y-coords[0][1])*111320) for x,y in coords]
    if max(math.hypot(x,y) for x,y in points)>2000:raise ValueError('Outline must fit within 2 km of its first vertex')
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,c):return abs(cross(a,b,c))<1e-7 and min(a[0],b[0])-1e-7<=c[0]<=max(a[0],b[0])+1e-7 and min(a[1],b[1])-1e-7<=c[1]<=max(a[1],b[1])+1e-7
    n=len(points)
    for i in range(n):
        a,b=points[i],points[(i+1)%n]
        for j in range(i+1,n):
            if j==i+1 or (i==0 and j==n-1):continue
            c,d=points[j],points[(j+1)%n]
            if (cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0) or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):raise ValueError('Outline crosses itself; draw a simple boundary')
    polygon=Geodesic.WGS84.Polygon()
    for lon,lat in coords:polygon.AddPoint(lat,lon)
    _,perimeter,area=polygon.Compute();area=abs(area)
    if area<1:raise ValueError('Outline must enclose at least 1 m²')
    result={'area_sqm':round(area,2),'area_sqft':round(area*10.76391041671,2),'perimeter_m':round(perimeter,2),
        'area_kind':request.area_kind,'corner_status':request.corner_status,'source':request.source,
        'geometry':{'type':'Polygon','coordinates':[coords+[coords[0]]]},'measurement_method':'WGS84 ellipsoidal geodesic polygon',
        'measured_at':datetime.now(timezone.utc).isoformat(),'model_version':'geometry-1',
        'verified_boundary':False,'floor_area_sqm':None,
        'limitations':['Precision of arithmetic does not establish boundary accuracy.','Footprint is ground coverage, not total floor area or apartment area.','A drawn parcel is not an official cadastral boundary.','Corner status is user supplied; no corner premium is applied.']}
    result['measurement_id']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result
