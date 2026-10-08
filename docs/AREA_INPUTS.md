# Area inputs that reach the valuation

The valuation and intelligence APIs accept either `area_sqm` or `area_sqft`.
Square feet use the exact international-foot conversion: 1 ft² = 0.09290304 m².
Supplying both fields is rejected to prevent conflicting measurements. All
comparable selection, adjustments and model features use normalized square metres.
The UI converts an entered value when its unit selector changes, preserving the
same physical size rather than interpreting 100 m² as 100 ft².

Supported valuations save the original value/unit, normalized floor area and
whether it was supplied or inferred from earlier block/type sales. They show
estimated price per m² and per ft². These are estimated unit rates, not recorded
transaction rates. Historical and comparable source prices remain separate.

Plot area, building footprint and a flat's floor area are not interchangeable.
Map outlines remain in measurement receipts; they do not silently overwrite a
flat-area input. A verified plot polygon establishes land area; an individual
unit plan/record establishes unit area. Neither establishes sale price by itself.

Reproduce an area's input from `area_input.value` and `area_input.unit` alongside
the receipt's property/date/data/model versions. The intelligence property object
also contains the normalized square-metre value and original square-foot input.
When replaying a request supply one unit, not both normalized and original fields.

Acceptance checks cover 1,000 ft² → 92.90304 m², identical supported-market
valuations/ranges for those equivalent inputs, unit-price arithmetic, and
rejection of conflicting, negative or unsupported oversized area inputs.
