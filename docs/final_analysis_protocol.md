# Final Analysis Protocol

## Status and purpose

This document freezes the primary analysis before the remaining event-level
data are extracted. Deviations must be recorded in `analysis_decisions.md` with
a reason and date.

## Confirmatory sample

- Study period: 2022-01-01 to 2026-04-30.
- Blockchain: Ethereum.
- Assets: native USDC and USDT contracts specified in the extraction scripts.
- Events: the 20 events marked `analysis_eligible = True` in
  `results/event_catalog/eligible_events.csv`.
- Event window: seven days before and seven days after each event.
- Primary hourly analysis range: relative hours -168 to +168.
- Shock window: relative hours 0 to +6 around the six-hour event peak.
- Events are excluded only by the pre-specified market-stability and overlap
  rules already applied.

The final confirmatory analysis requires at least 15 successfully extracted
eligible events. With fewer than 15, all estimates remain labelled
exploratory. All 20 remain the target.

## Primary hypothesis

**H1:** As Ethereum base fees increase within stable-market event windows,
CEX-bound USDC/USDT transaction counts decline more than non-CEX USDC/USDT
transaction counts.

Primary coefficient:

`is_cex_bound × log1p(avg_base_fee_gwei)`

Primary outcome:

`log1p(hourly transaction_count)`

The directional alternative is negative. Two-sided p-values and confidence
intervals will nevertheless be reported.

## Secondary hypotheses

- **H2:** The CEX-bound differential is larger in the pre-defined shock window
  than outside it.
- **H3:** The fee differential is stronger for lower-baseline-activity
  entities than for recurrently active entities.
- **H4:** A subset of entities remains more active than expected during fee
  shocks after conditioning on baseline frequency and pseudo-event behaviour.
- **H5:** Independently labelled positive entities are enriched in the upper
  tail of the rigidity distribution.

H2-H5 are secondary. Failure of H1 prevents claims that rigidity is a
cash-out-specific causal signal, even if H4 or H5 appears positive.

## Primary aggregate specification

\[
\log(1 + Y_{get}) =
\alpha_e + \delta_g + \lambda_{h(t)}
+ \beta_1 \log(1+C_{et})
+ \beta_2 I(g=\mathrm{CEX})\log(1+C_{et})
+ X_{et}'\theta + \epsilon_{get}.
\]

- \(g\): CEX-bound or non-CEX destination.
- \(e\): event.
- \(t\): UTC hour.
- \(X\): absolute ETH return, lagged 24-hour ETH volatility, maximum USDC/USDT
  depeg, and Ethereum block utilisation.
- Fixed effects: event and hour-of-week.

Inference:

- standard errors clustered by event;
- 95% confidence intervals;
- wild-cluster bootstrap-t p-value with Rademacher weights and at least 9,999
  replications for the primary coefficient.

If fewer than 15 events are available, HAC estimates may be shown only as
exploratory diagnostics.

## Entity-level risk-set protocol

For every real and pseudo event time:

1. define activity using only the previous 48 hours;
2. require at least two prior qualifying transactions in the main analysis;
3. calculate expected seven-hour activity as prior activity multiplied by
   \(7/48\);
4. compare observed and expected activity;
5. condition rigidity on baseline transaction count; and
6. use exactly the same rule for real and pseudo times.

Sensitivity thresholds: one, three, five, and ten prior transactions.

The main placebo times are relative hours -96, -72, and -48. They are selected
before inspecting the remaining events and fit inside the available pre-event
window with a full preceding 48-hour look-back.

## Rigidity construction

The preliminary entity-event residual is:

\[
R_{e\tau} =
\frac{Y^{obs}_{e\tau} - Y^{exp}_{e\tau}}
{\sqrt{Y^{exp}_{e\tau}+1}}.
\]

The final entity score must be partially pooled across available events.
Entities observed in only one event are not described as persistently rigid.
Persistent rigidity requires:

- presence in at least two eligible event risk sets; and
- a shrunken average residual in the top decile.

The dissertation will report both event-specific rigidity and persistent
rigidity, keeping the distinction explicit.

## Positive-unlabelled evaluation

Positive label sets are analysed separately:

- OFAC sanction labels;
- Tornado Cash persona labels.

Primary PU summary:

- positive coverage;
- top-decile positive count;
- top-decile lift;
- exact one-sided Fisher interval/test where feasible.

Unlabelled entities are not called negatives. ROC AUC, accuracy, specificity,
and false-positive rate are prohibited unless a defensible negative set is
obtained.

## Robustness family

Required:

1. one-, three-, and six-hour aggregation;
2. leave-one-event-out estimates;
3. exclusion of E002, the largest shock;
4. separate USDC and USDT outcomes;
5. transfer count, active sender count, and USD volume;
6. alternative market-stability cut-offs;
7. alternative fee-event quantiles (0.975 and 0.995);
8. dynamically reconstructed pseudo-event risk sets;
9. event-level wild-cluster inference;
10. CEX label-source sensitivity where metadata permit.

Secondary-model p-values will be reported as a family and adjusted using
Benjamini-Hochberg false-discovery-rate control. The primary H1 coefficient is
not selected from that family.

## Interpretation rules

- H1 negative with compatible placebo/pre-trend evidence:
  evidence consistent with a CEX-specific cost response.
- General stablecoin activity falls equally:
  network-wide congestion response, not cash-out-specific evidence.
- Only E002 drives the result:
  evidence limited to extreme shocks.
- Rigidity exists without label enrichment:
  interpretable behavioural heterogeneity, not validated AML specificity.
- Label enrichment without H1:
  exploratory association only; no causal AML claim.
- No robust effect:
  report a null result and the design's identification limits.

No result is described as proof of money laundering, sanctions evasion,
criminal urgency, or fear of freezing.

