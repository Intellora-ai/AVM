# Search, imagery and minimal free spatial pipeline

## Search and Google integrations

The backend uses one provider, Brave Search. `BRAVE_SEARCH_API_KEY` enables
address sale/property/price queries plus a neighborhood recent-sales query.
It returns at most 12 deduplicated, ranked discovery links, caches successful
results for six hours and records them in intelligence receipts. Search snippets
do not become verified transaction prices. There is no recursive crawler.
`GET /web-search?address=...` can also be used independently.

Google's Street View metadata API checks coverage within 50 m. Configure
`GOOGLE_MAPS_SERVER_KEY` for metadata and `GOOGLE_MAPS_BROWSER_KEY` for the
360° Maps Embed viewer. The server key is never returned to the client. Restrict
the public browser key to your website and required APIs. Enable the Street View
Static and Maps Embed APIs as appropriate to the two calls. Billing/quotas and
provider terms apply; free source data is not a guarantee of free API usage.

CesiumJS 1.134.1 / Google Photorealistic 3D Tiles are restored for optional visual
review. Configure the restricted browser key, enable Google Map Tiles API and set
`GOOGLE_3D_TILES_ENABLED=true`. The viewer loads only after opening imagery and
pressing the 3D button. No Cesium ion token is required. Google/Cesium attribution
remains visible. A loading error falls back to satellite reference. No coverage or
valuation accuracy is guaranteed by enabling the viewer. Street/satellite imagery
and measurement tools remain usable independently. Authenticated live rendering
has not been verified because Google API keys are absent here.

Set variables in the environment before launching; `.env.example` lists names.
Alternatively copy that template to the ignored `.env` file and fill values locally;
`start.command` loads it through Uvicorn's dotenv support. Docker Compose also
passes these optional settings through to the web service. Do not commit keys.
Neither provider credential was present
during development, so authenticated live search, Google coverage
remain unverified. Their integration logic is tested with controlled API responses.

## Free outline lookup and measurement

Explicit outline lookup requests OSM building ways within 125 m via Overpass. Up to 100
simple closed outlines are normalized, measured with WGS84 and cached for a day.
The panel offers up to five outline choices; users confirm the appropriate building.
It does not silently treat the nearest building as a legal plot or a particular unit.
Original OSM way references/tags and ODbL attribution are retained. Complex
multipolygon relations/holes are not implemented and are not approximated silently.

Live Overpass, Overture STAC and Microsoft Planetary Computer requests were denied
by the cloud's network policy during this work. The OSM adapter is implemented and
its normalization/cache are tested, but no live footprint success is claimed. Manual
drawing and single-Polygon GeoJSON imports remain available. Existing Microsoft
and Overture footprint downloads can be converted to individual GeoJSON outlines
outside the app; automatic Overture/Microsoft retrieval is not implemented here.

With `DATABASE_URL`, measurement polygons and immutable receipt payloads are also
stored as PostGIS `geography(Polygon,4326)` with a GiST index. Use `ST_Area(outline)`
for square metres and `ST_Perimeter(outline)` for metres. The WGS84 measurement
API continues to work without PostgreSQL. Measurement is horizontal geodesic area,
not sloped terrain surface area. SQL spatial indexing improves selected queries;
it does not make arbitrary analysis of billions of polygons instantaneous.

## Deliberate exclusions

- **Voronoi parcel guessing:** partitions distance to address points, not ownership.
  It must not supply plot sizes, setbacks, frontage or valuations as if measured.
- **SAM/edge filters as precision boundary generators:** segmentation can assist
  suitable high-resolution imagery, but cannot recover fences/roof details absent
  from a 10 m raster. It also cannot establish legal boundaries.
- **Automatic height/floors from arbitrary DEM:** a terrain DEM is not building
  height. DSM-minus-DTM needs compatible resolution, dates and vertical datums;
  height divided by a guessed floor height is not measured unit floor area.
- **Global terrain engine or QGIS/GRASS/GDAL stack initially:** unnecessary for
  existing polygon measurement. Add raster processing only for a measured benefit,
  e.g. documented flood/terrain-risk features with validated source resolution.
- **Imagery-based corner premium:** nearby roads are not legal frontage. Corner
  access, traffic and market preferences must be supported by parcel/road records
  and sales evidence; no universal uplift is applied.

Sentinel-2, Landsat, SAR and open elevation sources can supply useful context,
but revisit interval, cloud cover, resolution, archive availability and licenses
differ by product. Earth Engine requires registration/project setup and usage
terms; commercial usage is not automatically free. Sentinel Hub is not an unlimited
free high-resolution API. ASF downloads can require Earthdata authentication.
Overture's datasets have theme/source-specific licensing; do not assume every layer
has one blanket ODbL license. Building footprints and administrative boundaries
are not cadastral parcels. Free data/software still require compute, storage and
operations. These sources will not be substituted for missing measurements.
