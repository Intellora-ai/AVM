# Question → delete → simplify

This audit supersedes earlier descriptions of automatic imagery/outline calls and
Google photorealistic 3D support. Those behaviors were removed during simplification.

| Requirement / origin | Why it exists and what removal changes | Decision / proof needed |
|---|---|---|
| Address search — customer | Identifies the intended property; removing it breaks the main journey | Keep; test search-to-result |
| Exact household identity — customer / data correctness | Wrong identity attaches another property's price | Keep explicit ambiguity; unit identity must be verified before calling block history household history |
| Evidence, date, currency, measurement type — correctness | Numbers without these can compare different things | Keep; retain source receipts and checks |
| Sales comparison — customer / appraisal method | Establishes market price from substitutes | Keep; judge by held-out actual sales |
| Multiple model implementations — engineering choice | Useful only if accuracy warrants complexity | Existing measured baseline/challenger remain; no new model unless it beats validation |
| 3D rendering/Cesium — customer feature request | Shows context, not measured market value; no demonstrated accuracy gain | Delete viewer, loader and enable flag; add back only with a validated user benefit |
| Street imagery — customer feature request | Can help visual review but is not necessary for every valuation | Optional explicit action; keep satellite link fallback |
| Every-address footprint query — implementation choice | Added latency/network calls even when size is already known | Delete automatic lookup; request only when measurement is needed |
| Two discovery calls — implementation accident | Main panel and intelligence both called discovery | Delete standalone client discovery; share intelligence location evidence |
| Two initial valuations — implementation accident | Supported property was valued in both main and intelligence panels | Delete automatic intelligence run for already-selected supported profiles |
| Front-page benchmark/coverage requests and panels — presentation choice | Consumed requests/UI without helping select an address | Delete from startup UI; API/research evidence remains available |
| Duplicate imagery links — presentation choice | Google and Mapillary controls repeated similar functions | Delete extra Mapillary control |
| Heavy raster/SAM/QGIS pipeline — suggested implementation | Needs suitable imagery and testing; cannot manufacture boundary detail | Do not add until measured attribute/valuation benefit |
| Voronoi plots / guessed floor counts — suggested implementation | Generates assumptions instead of measured parcel/unit attributes | Reject for valuation inputs |
| Global preloaded property database / marker layer — implementation choice | Large initial load and clutter | Remains deleted from main journey; query only what is selected |
| Historical test data — accuracy requirement | Necessary to measure failures and calibrate uncertainty | Keep existing source archives; deleting them would remove the evidence supporting accuracy claims |
| PostgreSQL deployment — implementation choice | Useful shared/spatial persistence; unnecessary for one-user local preview | Keep optional; file storage remains usable |

The remaining journey is address → identity → usable evidence → estimate or
abstention → receipt. Measurement and visual review are explicit optional tools.
Keep range calibration and historical validation: neither imagery nor attractive
3D rendering substitutes for evidence that predictions match later actual sales.

## Concrete help with external blockers

The observed cloud errors were HTTP/proxy 403 responses, not missing Python
libraries. Check the cloud environment's network settings and permit the sources
that will actually be used:

- `overpass-api.de`: implemented OSM building-outline query.
- `stac.overturemaps.org`: catalogue for a potential Overture adapter; that adapter
  is not implemented, so enabling the domain alone does not add it.
- `bfppub.blob.core.windows.net`: Microsoft's footprint index/downloads; automatic
  Microsoft retrieval is not implemented. Imported outlines are supported.
- `planetarycomputer.microsoft.com`: potential imagery catalogue, not required by
  the current measurement tool.
- `api.search.brave.com`: optional search API, additionally requiring its key.
- `maps.googleapis.com`: optional Street View metadata API, additionally requiring
  its server key. Browser embedding needs a restricted browser key and enabled APIs.

Start with Overpass for free outline retrieval. Permit only the sources needed,
then retry a representative request. A saved allowlist is not proof of live access.
If you cannot edit cloud networking, running locally can test whether the denial
is specific to the cloud proxy. No claim is made that local access will succeed.
Add credentials privately through environment settings or ignored `.env`, never
through chat. Leave Google/search keys empty if the immediate priority is the free
measurement and existing supported-market valuation workflow.
