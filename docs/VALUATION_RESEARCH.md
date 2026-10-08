# Valuation methods and public-data research

Research and experiments performed 8 October 2026. This document separates accessed material, implemented methods and unresolved coverage.

## What the books imply for this system

There is no universally most accurate valuation formula. Appraisal asks for a defined interest in a property, purpose and effective date; prediction must be evaluated against observed transactions in the relevant segment.

| Resource | Material actually accessed | Engineering consequence |
|---|---|---|
| The Appraisal of Real Estate, Appraisal Institute | Publisher site attempted; blocked by network policy. The full commercial text was not accessed. | Treat sales comparison, income capitalisation and replacement cost as distinct approaches. A residential transaction engine cannot claim an income or cost appraisal without rent, expenses, land and construction evidence. |
| Fundamentals of Mass Appraisal, IAAO | Publisher/standards site attempted; blocked by network policy. Full text not accessed. | Segment by market and type; measure prediction/sale ratios and dispersion; report subgroup error. Do not claim IAAO compliance from one benchmark. |
| An Introduction to Statistical Learning | Authors' open [resampling lab](https://github.com/intro-stat-learning/ISLP_labs/blob/main/Ch05-resample-lab.ipynb) and [bagging/boosting lab](https://github.com/intro-stat-learning/ISLP_labs/blob/main/Ch08-baggboost-lab.ipynb) | Separate model training, selection/calibration and later testing. Reuse scikit-learn ridge and gradient boosting. We select the challenger on calibration error, then report later test error. |
| Geographic Data Science with Python | Authors' open [spatial regression chapter](https://github.com/gdsbook/book/blob/main/notebooks/11_regression.qmd) | Location effects, spatially structured errors and omitted features matter. Include coordinates and town; exclude grouped block IDs from training and report performance on those unseen groups. |
| Designing Machine Learning Systems | Author's [official repository](https://github.com/chiphuyen/dmls-book) and [chapter summaries](https://github.com/chiphuyen/dmls-book/blob/main/summary.md) | Preserve source data, versions, feature assumptions and model checksums. Monitor data freshness and model error; refuse stale or unsupported evidence. |

These are design choices informed by the resources, not a claim to have read every commercial book or a certification of compliance. The material was researched via HTTP and official author repositories; no specialist web-search connector was available.

## Direct official source acquisition

- HDB resale dataset: [data.gov.sg](https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view). Downloaded via the public API, not a scraped third-party table. Raw CSV retained as content-hashed gzip.
- HDB property/building information: [data.gov.sg](https://data.gov.sg/datasets/d_17f5382f26140b1fdae0ba2ef6239d2f/view). Downloaded directly and used for exact block/street matching and building completion.
- Coordinates: pinned [OneMap-derived public mirror](https://github.com/ayaka14732/singapore-hdb-map), joined to the official building keys. They are not claimed to have been newly geocoded directly by us.
- Retained evidence: 242,256 official resale rows and 16,938 block/type profiles; three transactions lacked a matched official building/location and were excluded.
- Reported months reach October 2026. Since exact transaction days are not published, current incomplete-month records are conservatively excluded from valuation. Latest completed month: September 2026.
- Official publication establishes provenance, not independent verification of condition, ownership, unit identity, market exposure or arm's-length status.
- The official resale collection's four earlier files were also downloaded: 746,203 archival rows extend the source history to January 1990. Total acquired official rows: 988,459. Archives are loaded by town/type and matched to currently supported building coordinates; historic unmatched/demolished blocks remain outside the active map inventory.
- Before March 2012, source periods represent approval month; later periods represent registration month. The record and UI preserve this distinction.

HDB unit numbers are withheld. No model can reconstruct a reliable unique apartment sale history from block/type records alone. The software makes that limitation visible and lets a buyer supply area, storey range and flat model.

## Measured accuracy

The machine-readable results are in data/benchmark.json. Training ends June 2025; calibration/model selection ends December 2025; testing uses January–September 2026 sales. Approximately ten percent of building-coordinate groups are excluded across every flat type from training/calibration and reported separately. Nearby training blocks may remain; this is not a whole-region holdout.

Final experiment on 19,639 later transactions:

| Model | Median absolute percentage error | Within ±10% | Within ±20% |
|---|---:|---:|---:|
| Log-price ridge regression | 6.57% | 68.89% | 93.31% |
| Histogram gradient boosting | 4.51% | 83.98% | 98.71% |

On 1,966 sales at unseen building coordinates, gradient boosting's median absolute error was 4.98%. Its nominal 90% calibration band covered 85.02% of later actual prices: an explicit sign that future coverage cannot be assumed from calibration.

Known sale attributes are available during this benchmark. These results do not establish the same accuracy for an unknown flat profile, a different country, later dates, property conditions we do not observe, or forecasts. This is a preliminary temporal and grouped validation, not a repeated evaluation across all cities.

The fixed comparable-sales model was separately evaluated on 250 deterministic later-sale samples with strictly earlier evidence: 249 produced estimates and one abstained. Median absolute error among those valued was 6.49%; 69.88% were within ±10%. This is a different cohort from the ML experiment and should not be treated as a paired head-to-head comparison. See data/comparable_benchmark.json.

The challenger is applied from January 2026 through at most 90 days beyond the evaluated period, with supplied area/floor/model, a consistent recorded lease year, at least the required comparable evidence and no strong disagreement with the comparable model. Live dates beyond evaluation are explicitly disclosed. Earlier dates use earlier-sale comparison, so a model calibrated in late 2025 cannot leak into a 2020 estimate.

## Past, present and future

- Past **recorded prices** are official facts about published transactions within a block/type.
- Past **estimated values** are reconstructed using earlier records and the requested date. The source snapshot was obtained today; this is not proof of contemporaneous knowledge.
- Present **estimated values** require fresh completed-month evidence, usable characteristics and nearby sales.
- Future **scenarios** compound a town/type trend and widen uncertainty. They have not been validated as individual-property price forecasts; market-mix changes and regime shifts can invalidate them.

## Worldwide coverage through reuse

Reuse the global MapLibre interface, address search, source schema, model interfaces, receipts and evaluation gates. Add official sources as adapters rather than rebuilding applications for each country.

| Market/source | Attempted operation | Current result | Data work needed |
|---|---|---|---|
| Singapore HDB | Public official sales/buildings CSV download | Acquired and ingested | Unit identities withheld; private residential property is absent |
| France DVF/Etalab | Geocoded Paris transaction file request | Proxy/network-policy 403 | Screen residential mutations, multiple lots/parcels and department exclusions |
| England/Wales HM Land Registry | Official 2025 price-paid file request | Proxy/network-policy 403 | Join characteristics/area and reliable location; not Scotland/Northern Ireland |
| NYC Department of Finance/Socrata | Official rolling-sales portal/dataset request | Proxy/network-policy 403 | Validate the correct dataset, zero-price/non-market transfers, tax lots and condo areas |
| Worldwide OpenStreetMap | Public user-triggered geocoder and world geography | Address lookup tested | Buildings/addresses provide discovery, not sales or verified value |

Source attempts and capabilities are in data/coverage.json. Network domains were added to the environment draft; saving that draft alone does not activate runtime permissions. Exact blocked operations should be retried after environment settings are applied.

Majority-world property valuation has not been demonstrated. Coverage must count successfully matched properties with enough verified source evidence, not map tiles, country population or an assumed price per square metre.

## Staged launch requirements

1. A buyer can open the application without development tooling failures; map pan/zoom/search/select work.
2. Each supported profile shows official sale references and admits missing unit identity.
3. Current/past estimates pass date and evidence gates; future numbers are labelled scenarios.
4. Models are promoted only through documented temporal and spatial tests, with per-type and per-region error and interval coverage.
5. New official adapters acquire and normalise records before a region is labelled supported.
6. A public launch still needs hosting, HTTPS, backups, freshness/retraining operations and reviewed data terms. No public deployment was performed here.
