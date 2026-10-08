# Google-native address and business search

When `GOOGLE_MAPS_BROWSER_KEY` is configured, the app opens Google Maps itself,
not an imitation geocoder. Search uses Places Text Search for addresses/businesses,
with Google's Geocoding service as a fallback. Results are shown on the Google
map; selecting one centers the map, adds its pin and starts evidence discovery.
No list of manually entered worldwide properties is required.

Enable Maps JavaScript API, Places API (New), and Geocoding API for the restricted
browser key. Native Street View comes from the map control where coverage exists.
Google services require a project/API key and applicable billing/quotas; free usage
allowances do not mean unlimited anonymous use. Set the key privately in ignored
`.env` or environment settings, then start the app. No live key was available in
this cloud, so authenticated Google search/imagery remain unverified.

Google satellite/hybrid view supports boundary drawing directly on the native
map. The API calculates WGS84 m², ft² and perimeter, keeps the coordinate receipt
and distinguishes plot area from building footprint. The user-drawn outline is
not a survey or an automatically verified property boundary. Measurement does
not silently overwrite floor area. An optional 3D/imagery control retains the
restored Cesium/Google viewer with its own API configuration.

If Google is not configured, the existing open-map address search and measurement
workflow starts. The Google page also offers a switch to that fallback. Search
results do not by themselves establish residential eligibility, sale history or
market value. Supporting source discovery runs for the selected location; where
supported block/type profiles are available, choose one explicitly to value it.
The component does not permanently archive Google's raw search responses.
