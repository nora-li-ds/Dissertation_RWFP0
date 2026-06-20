# Analysis Decision Log

## 2026-06-18

- Retained six-hour aggregation for long-run fee-event discovery.
- Selected hourly data for event analysis.
- Replaced contemporaneous rolling thresholds with lagged thresholds.
- Separated fee-event discovery from market-stability classification.

## 2026-06-19

- Made transaction count and the extensive margin primary outcomes.
- Retained USD volume as secondary because whale transfers dominate totals.
- Required baseline activity to be measured before the anticipatory period.
- Kept OFAC and Tornado Cash labels separate.
- Treated unlabelled entities as unlabelled rather than negative.

## 2026-06-20

- Identified regression-to-the-mean risk from selecting pre-active entities.
- Added dynamically reconstructed real and pseudo-event risk sets.
- Downgraded the naive pooled pre/post decline from causal evidence.
- Added non-CEX stablecoin transfers as the primary negative-control outcome.
- Made the CEX-bound-by-fee interaction the primary aggregate estimand.
- Set 15 extracted eligible events as the minimum for confirmatory reporting;
  all 20 remain the target.

