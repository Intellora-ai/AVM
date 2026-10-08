# Property measurement and valuation: necessary foundations

## What was actually researched

Read the openly accessible IAAO *Standard on Mass Appraisal of Real Property*
(approved July 2017; the retrieved document includes later explanatory notes):
https://www.iaao.org/wp-content/uploads/StandardOnMassAppraisal.pdf
This is official guidance, not the complete commercial book *Fundamentals of
Mass Appraisal* by Gloudemans and Almy. It directly cites that book (2011), including
chapter 9 for property characteristics. The full commercial book and requested
*The Appraisal of Real Estate, 16th Edition* were not accessed. No claim is made
to have read their entire contents, verified the requested edition's contents,
or implemented every recommendation.

Read the authors' open spatial-regression chapter of *Geographic Data Science
with Python*: https://github.com/gdsbook/book/blob/main/notebooks/11_regression.qmd
Read Microsoft's official global building-footprint documentation:
https://github.com/microsoft/GlobalMLBuildingFootprints
As retrieved on 2026-10-08, it reports 1.4 billion detected buildings, imagery
from 2014–2024 with later updates, and CDLA Permissive 2.0 licensing. Coverage
and source imagery dates vary; these are detected building outlines, not legal
parcel boundaries. The linked dataset index download was denied here.

General web-search, Copernicus, Google developer docs and live OSM geometry
endpoints returned access-denied errors in this environment. The Appraisal
Institute publication URL tried returned 404. Those failures are not proof that
the sources are unavailable elsewhere. This report uses accessible primary
documents and established appraisal principles, not a purported exhaustive
search or full-book reproduction.

## The measurements the system must keep separate

| Measurement | Meaning | Suitable evidence |
|---|---|---|
| Land/plot area | Area inside parcel boundary | Cadastral polygon, deed/survey, separately labelled user outline |
| Building footprint | Ground coverage of building | OSM/Microsoft polygon, suitable imagery-derived outline |
| Gross floor area | Area across floors under a stated measurement standard | Plans, official records, measured floor outlines |
| Usable/net internal area | Interior space under the applicable standard | Floor plans or interior measurement |
| Apartment area | Area of a specific unit | Unit records/plans; whole-building imagery cannot establish it |

Satellite imagery alone does not establish ownership or legal boundaries.
Roof overhangs, trees, shadows, off-nadir distortion, adjoining structures and
imagery age can change apparent outlines. Sentinel-2's best nominal 10 m bands
are useful for land cover and neighborhood context, not precise small-home
boundaries. Google Maps/Street View are proprietary services with API terms,
quotas and billing; free consumer viewing is not an unlimited extraction license.
The app links to Google's satellite viewer, rather than scraping Google imagery.

The implemented measurement uses GeographicLib's WGS84 ellipsoidal polygon
calculation. It rejects crossed, degenerate, repeated-vertex and oversized outlines;
returns m², ft² and perimeter; saves coordinates, source, area kind and method.
Numerical precision is not survey accuracy. Drawn parcels are labelled unverified.
Neither plot area nor building footprint is automatically fed into a model expecting
floor area. Holes/multipolygons and official cadastral-source adapters are not yet implemented.
Single Polygon GeoJSON files can be imported from Microsoft/OSM/parcel workflows;
imported coordinates are user-supplied evidence, not independently verified sources.

## Essential appraisal principles and their engineering consequences

The following is an implementation-oriented synthesis of the accessible IAAO
guidance, open geographic chapter and general appraisal methods. It is not a
chapter-by-chapter summary of the two inaccessible commercial books.

1. Define the valuation date, purpose, market-value basis, property interest and
   assumptions. Ownership restrictions, leasehold duration and permitted use can
   change value even when two buildings look identical.
2. Resolve identity: coordinates, address, parcel ID, building and unit are different
   identifiers. A geocoder point can represent an entrance or street centroid.
   Match records before attributing a transaction to a household.
3. Collect consistently defined characteristics. IAAO identifies living area,
   construction quality, effective age/condition, building design, bathrooms and
   other features; land size, zoning, utilities; market area, amenities and nuisances.
   Record source, date, units and confidence instead of silently filling gaps.
4. Verify market evidence. Filter gifts, related-party transfers, portfolio/package
   sales and other non-market observations where identifiable. Registered data
   establishes provenance but does not guarantee an arms-length transaction.
5. Sales comparison: compare substitutable properties and adjust supported
   differences in time, location, size, quality, condition, tenure and features.
   Infer adjustments from market evidence; do not assign a universal corner premium.
6. Income approach: rent, vacancy, expenses and locally supported capitalization
   rates can provide another indication. Gross rental yield is not equivalent to
   net operating income capitalization. Do not infer a local yield from nothing.
7. Cost approach: land value plus replacement cost, less physical depreciation,
   functional obsolescence and external obsolescence. Use where suitable evidence
   supports it, not as a guaranteed equivalent to resale market value.
8. Reconcile methods by relevance and evidence quality. Correlated estimates or
   syndicated advertisements are not independent confirmations. Disagreement
   warrants examination and a wider range or abstention.
9. Measure mass-appraisal performance on withheld sales: valuation/sale ratios,
   median ratio, dispersion and price-related bias. Check property-type and
   neighborhood slices, not only a global error average. Calibration sales must
   not leak into the reported test set.
10. Account for spatial structure. The geographic chapter explains spatial features,
    heterogeneity and dependence; patterned residuals can indicate missing variables.
    Validate on later dates and separated spatial groups, inspect residual clusters,
    and test whether added proximity features actually improve withheld accuracy.
11. Assess corner status from parcel frontage and road topology, not a roof shape.
    Two nearby roads do not establish legal access or frontage. Corner lots can
    benefit from access/light or suffer traffic/noise; the value effect is local.
12. Forecast conditionally. Historical trends, rates, supply and demand can motivate
    scenarios, but historical fit does not establish future forecast accuracy.
    Backtest 12/24/36-month horizons when sufficient historical snapshots exist.

## Source roles and next necessary steps

OSM is useful for map context, mapped buildings and roads, with uneven completeness
and ODbL attribution requirements. Microsoft offers reusable machine-detected
building geometry with its own license; it is not an apartment/parcel registry.
Google satellite/Street View can support visual review subject to their terms;
licensed integration requires an appropriate API configuration. Cadastral sources,
surveys and unit plans supply measurements these imagery products cannot establish.

Next: import/verify actual parcel polygons and footprint sources; retain geometry
dates and positional uncertainty; resolve individual units; add road-frontage
analysis with confirmation; validate attribute accuracy against measured records;
then evaluate whether these attributes improve the sale-price benchmark. An accurate
outline alone does not guarantee an accurate valuation.
