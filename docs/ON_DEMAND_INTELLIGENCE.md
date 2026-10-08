# On-demand intelligence V1

Implemented flow: map/address selection → resolve location → query eligible
official sources and supplied public listing URLs → extract JSON-LD → classify
evidence → deduplicate → check comparability → show supporting indications →
retain original source evidence and reproducible response.

## What works

- `POST /intelligence`: coordinates, optional address, house/apartment type,
  floor area, currency, bedrooms/bathrooms, land area, age/condition, up to eight
  HTTPS source URLs, optional explicitly assumed gross annual rental yield.
- Address lookup is global via OpenStreetMap/Nominatim, not a sales registry.
  Global street tiles are relayed through a fixed OpenStreetMap endpoint with
  TLS verification, attribution and browser caching, avoiding browser/proxy TLS
  failures observed in this cloud. No bulk tile download is performed.
- NYC Department of Finance rolling sales are fetched on demand from its
  official Socrata endpoint when location evidence identifies a New York ZIP.
  Single-family, single-unit sales above $10,000 are retained. Source rows,
  dates, prices, floor areas, parcel identities and provenance remain available.
  At most 400 recent rows are queried; historical coverage is not complete.
- Existing Singapore HDB transaction model can be used by explicitly choosing
  a supported block/type profile. `property_id` in an intelligence request
  links its current estimate, range, scenarios and saved transaction receipt.
- Public HTML pages with residential JSON-LD offers can yield asking/rental
  prices, attributes, source dates and coordinates. Advertisements never become
  verified sales just because a page says the property was sold.
- Comparison requires same currency and confirmed house/apartment type, known
  floor areas with at least 65% area similarity, coordinates within 2 km and a
  publication date within 180 days. Missing data causes exclusion, not inference.
- Asking/rental signals require at least three property identities across two
  source hosts. Source hosts are not proof of independent ownership. Identity
  deduplication limits obvious syndication/repricing; it cannot detect all copies.
- Source-type reliability, area similarity, distance and freshness determine
  weights. These are transparent heuristic scores, not calibrated probabilities.
- Rental indications require a stated monthly/annual period and a user-assumed
  gross yield. Expenses are excluded. No country-wide yield is guessed.
- Differences between supporting indications are reported. No unvalidated
  averaging of asking prices, rents and transaction models is used as market value.
- Six-hour source caches, original bounded webpage snapshots and saved JSON
  evidence receipts. `GET /intelligence/{receipt_id}` reproduces the saved result.
  User-supplied attributes are recorded with the request, not verified by the app.

## Current limits

This is an evidence pipeline, not a completed global household AVM. Automatic
general web-search integration is absent: Bing RSS and the attempted France
endpoint were denied by the execution environment. Listing URLs can be supplied
in the map panel. No bypass of paywalls, site blocks or authentication is attempted.
Sites without usable server-rendered JSON-LD return no structured offers.

NYC official records currently lack comparable coordinates in this adapter.
They are shown as postal-code evidence and excluded from the distance-based
valuation. Parcel/address resolution, arms-length filtering, historical calibration
and a temporally held-out evaluation are prerequisites to enabling NYC estimates.
Singapore remains block/type research, not exact apartment sale history.

Where a transaction-backed, validated estimate is unavailable, the response has
`estimated_value: null`, no forecasts and an explicit insufficient-evidence status.
Supporting listing/rental indications are separately labelled unvalidated.
Observed signal dispersion is not a calibrated confidence interval. Historical
values and future scenarios continue to use the existing supported-market engine;
webpage discovery does not invent a historical trend.

Before public multi-user launch: move cache/receipt files into managed storage,
apply request quotas and concurrent lookup coalescing, validate source permissions,
complete a production review of source-fetch egress controls, and add outcome-based
evaluation for each enabled market model. No paid search or AI keys are required
for the implemented development workflow.
