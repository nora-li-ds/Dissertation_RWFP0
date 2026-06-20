# Dissertation Structure and Evidence Map

## 1. Introduction

- Crypto-AML auditability problem.
- Difference between prediction, anomaly detection, and causal assessment.
- Research aim and three research questions.
- Contribution summary.

Evidence required:

- RP motivation;
- regulatory and methodological references;
- final one-paragraph findings after full analysis.

## 2. Literature review

- Predictive graph-based crypto-AML.
- Label scarcity and PU evaluation.
- Ethereum fees and behavioural timing.
- Causal assessment and falsification.
- Auditability as procedural transparency.

Current draft: `docs/literature_review_draft.md`.

## 3. Data

- Dune tables and extraction dates.
- USDC/USDT contracts.
- CEX label definition and limitations.
- Long-run six-hour series.
- Hourly market controls.
- Event and entity samples.
- Ethics and privacy handling.

Required final tables:

- data-source table;
- event-flow table (67 -> 32 -> 20 -> extracted);
- descriptive event table;
- label-coverage table.

## 4. Methods

- Causal graph and assumptions.
- Lagged event discovery.
- Market-stability screen.
- CEX versus non-CEX negative control.
- Dynamic real/placebo risk sets.
- Entity rigidity construction.
- PU evaluation.
- Inference and robustness.

Current drafts:

- `docs/research_design.md`
- `docs/final_analysis_protocol.md`
- `docs/dissertation_methods_draft.md`

## 5. Results

Recommended order:

1. event discovery and exclusions;
2. descriptive fee-shock severity;
3. primary CEX-by-fee negative-control model;
4. event-level heterogeneity;
5. dynamic risk-set placebo results;
6. entity rigidity;
7. PU enrichment;
8. robustness family.

Do not lead with the label analysis. The causal behavioural result must be
established before discussing AML specificity.

Current pilot draft: `docs/pilot_results_draft.md`.

## 6. Discussion

- What the stress test identifies.
- What it cannot identify.
- Extreme versus ordinary fee shocks.
- Transaction count versus volume.
- Implications of null label enrichment.
- Operational use as a review trigger.

Current draft: `docs/discussion_limitations_draft.md`.

## 7. Limitations

- cash-out proxy;
- labels and look-ahead;
- address/entity mismatch;
- residual fee endogeneity;
- treatment measurement;
- few event clusters;
- external validity.

## 8. Conclusion

The conclusion should answer:

1. Is there a CEX-specific cost response?
2. Is rigidity persistent across events?
3. Is rigidity enriched among available positive labels?
4. What audit record can the method produce?

## Appendices

- Dune SQL and schema audit.
- Full event catalogue.
- Market-stability thresholds.
- Alternative event definitions.
- Placebo and leave-one-event-out results.
- Wild-cluster bootstrap details.
- Data contract and reproducibility commands.
- Ethics and label interpretation statement.

