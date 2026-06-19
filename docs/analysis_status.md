# Analysis Status

Last updated: 2026-06-19

## Completed

- Read and translated the RP into a frozen causal research design.
- Audited the existing six-hour dataset.
- Rebuilt event discovery with a lagged rolling threshold.
- Identified 67 candidate events and 32 non-overlapping event windows.
- Extracted complete hourly Ethereum fee, ETH price, USDC price, and USDT
  price controls for 2022-01-01 to 2026-04-30.
- Applied the pre-specified market-stability screen.
- Retained 20 eligible stable-market fee shocks.
- Extracted entity-hour CEX-bound USDC/USDT transfers for three pilot events:
  E002, E020, and E047.
- Built event-hour and entity-event-period modelling panels.
- Ran exploratory event-study, hourly regression, entity-response, and
  positive-unlabelled enrichment analyses.

## Pilot evidence

These are exploratory findings, not final dissertation estimates.

- Mean hourly transaction counts fell strongly during all three pilot shocks
  relative to their baseline periods.
- In the pooled hourly pilot model, the estimated transaction-count elasticity
  with respect to average base fee was approximately -0.89.
- The analogous USD-volume elasticity was approximately -0.48 and was visibly
  less stable because a small number of large transfers dominated volume.
- Baseline-active entities with more frequent pre-event transfers were more
  likely to keep transferring during the shock. Rigidity must therefore be
  calibrated conditional on baseline activity.
- Direct OFAC-labelled senders were absent from the pilot risk sets.
- The E002 risk set contained 12 baseline-recurrent Tornado Cash persona
  addresses. They were not enriched in the rigidity top decile:
  lift approximately 0.83; one-sided Fisher p approximately 0.72.

## Interpretation

The pilot supports the existence of a broad cost response in transaction
counts. It does not currently support the stronger claim that behaviourally
rigid entities are enriched for the available public high-risk labels.

The defensible contribution may therefore be:

1. a transparent causal stress-test design;
2. evidence that transaction count is more informative than aggregate volume;
3. an auditable rigidity signal conditional on baseline activity; and
4. a demonstration of the limits of public labels for AML validation.

## Current external blocker

Dune returned HTTP 402 while starting the remaining event extractions. The
current account requires additional credits or a quota reset. The extraction
script now stops immediately on HTTP 402 instead of retrying.

## Resume command

After Dune access is restored:

```powershell
python scripts/extract_entity_event_transfers.py --all-eligible
python scripts/build_analysis_panels.py
python scripts/run_pilot_analysis.py
```

Existing event files are reused, so the first command resumes rather than
repeating completed extractions.

## Remaining work

- Extract the remaining 17 eligible events.
- Rename the pilot analysis script/output to final analysis after full
  extraction.
- Estimate final event-study uncertainty with event-level clustering or a
  wild-cluster bootstrap.
- Implement leave-one-event-out and placebo-event analyses.
- Estimate partially pooled entity rigidity across events.
- Run one-, three-, and six-hour aggregation sensitivity checks.
- Produce dissertation-ready tables and figures.
- Draft Methods, Results, Limitations, and Discussion chapters.

