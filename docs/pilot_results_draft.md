# Pilot Results Draft

> Status: exploratory pilot based on three of 20 eligible events. This text
> must not be presented as the final dissertation results.

## Sample construction

The long-run screen identified 67 candidate six-hour fee events. Removing
overlapping 14-day analysis windows left 32 candidates. The market-stability
screen retained 20 events and excluded 12 because of elevated ETH volatility,
large hourly ETH returns, or stablecoin depegging.

Entity-hour transfer data were available for three pilot events:

- E002, an extreme event on 1 May 2022;
- E020, an event in May 2023; and
- E047, a lower-fee-regime event in October 2024.

Applying a minimum of two baseline transactions produced 15,036, 15,014, and
25,074 modelled entities respectively.

## Naive event patterns

Mean hourly CEX-bound transaction counts during the seven-hour shock period
were 11.9%, 30.3%, and 42.4% of their event-specific baseline means for E002,
E020, and E047. Aggregate USD volume behaved less consistently, confirming that
large transfers can obscure changes in transaction frequency.

A pooled hourly exploratory regression estimated a negative association
between average base fee and transaction count. The one-hour coefficient was
approximately -0.86. Estimates remained negative at three-hour (-0.66) and
six-hour (-0.64) aggregation. Leave-one-event-out estimates ranged from
approximately -0.89 to -0.80.

These estimates are not sufficient causal evidence. The entity sample was
selected using pre-event activity, which gives the pre-period a mechanical
activity advantage.

## Dynamic risk-set calibration

To address this issue, each real and pseudo event was assigned a separately
constructed risk set using only its own previous 48 hours. For E002, the real
shock's observed-to-expected transaction ratio was materially below all three
pseudo windows at every tested activity threshold. For entities with at least
two prior transactions, the real ratio was approximately 0.18 compared with
approximately 0.36-0.37 in the pseudo windows.

The pattern did not generalise cleanly. For E020 and E047, dynamically
calibrated real-event ratios were similar to placebo ratios. Among entities
with at least five prior transactions, observed activity was approximately
equal to or above the baseline projection.

The pilot therefore provides preliminary support for a response to the most
extreme fee event, but not for a general suppression effect across all
candidate shocks. This result motivates a negative-control comparison with
non-CEX stablecoin transfers in the full analysis.

## Behavioural heterogeneity

The probability of making any transfer during the seven-hour shock increased
strongly with baseline activity. Depending on event, fewer than 4% of entities
with exactly two baseline transactions remained active, compared with roughly
20-40% of entities with ten or more baseline transactions. A useful rigidity
score must therefore condition on expected activity rather than rank raw
shock-period transaction counts.

## Positive-unlabelled evaluation

No directly OFAC-labelled sender appeared in the pilot model samples. E002
contained 12 baseline-recurrent Tornado Cash persona addresses. One appeared
in the top rigidity decile, corresponding to lift of approximately 0.83 and a
one-sided Fisher exact p-value of approximately 0.72. The pilot provides no
evidence of label enrichment.

## Interim interpretation

The pilot supports three methodological conclusions:

1. transaction frequency is a more stable outcome than aggregate USD volume;
2. pre-activity selection can create a misleading event-study decline unless
   real and placebo risk sets are reconstructed symmetrically; and
3. public risk labels are too sparse to support conventional supervised
   validation.

The substantive fee-friction claim remains open pending the complete event
sample and the CEX-bound versus non-CEX negative-control analysis.

