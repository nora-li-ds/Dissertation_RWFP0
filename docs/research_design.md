# Research Design: Causal Stress Testing for Auditable Crypto-AML

## 1. Research objective

This study tests whether pseudonymous entities sending USDC or USDT to labelled
centralised-exchange deposit addresses reduce or delay their cash-out-proxy
activity when Ethereum transaction costs rise unexpectedly.

The study does **not** infer criminal intent. It estimates behavioural rigidity
under externally imposed network friction and evaluates whether that signal is
enriched among independently labelled high-risk entities.

## 2. Units and variables

- Observational unit: sender entity x UTC hour x fee-shock event.
- Entity proxy: the token-transfer `from` address. Address clustering is a
  sensitivity analysis, not a prerequisite for the main model.
- Cash-out proxy: an ERC-20 USDC or USDT transfer whose receiver is a labelled
  Ethereum CEX address.
- Outcomes:
  - `transfer_any`: whether an entity made at least one qualifying transfer;
  - `transfer_count`: number of qualifying transfers;
  - `volume_usd`: total qualifying USD value;
  - `delay_hours`: time to the entity's next qualifying transfer.
- Network-friction exposure:
  - pre-determined network base-fee shock;
  - continuous hourly base fee;
  - optional transaction-level realised fee in USD as a secondary measure.
- Market-stability controls:
  - absolute ETH hourly return;
  - rolling ETH return volatility;
  - USDC and USDT deviation from USD 1;
  - network transaction or block utilisation controls.

## 3. Two-stage data design

### Stage A: long-run event discovery

Use the existing six-hour series only to screen the full 2022-2026 period.
Candidate shocks must be defined using information available before the
candidate interval:

1. lagged rolling fee threshold;
2. an adaptive economic-materiality threshold;
3. de-duplication of adjacent or overlapping events;
4. exclusion or separate analysis of market-panic periods.

### Stage B: event-window extraction

For selected events, retrieve hourly entity-level transfers and hourly network
and market controls for seven days before and seven days after each event.
Fifteen-minute or block-level data are used only to validate the timing of the
largest shocks.

## 4. Estimands

### 4.1 Average event-time response

The primary estimand is the change in entity cash-out-proxy activity at each
event hour relative to the pre-event reference period, conditional on entity,
event, and calendar-time effects.

### 4.2 Entity-level rigidity

Entity rigidity is defined from a hierarchical or partially pooled interaction
between fee exposure and entity. It is not estimated from a separate noisy
regression for every address.

An entity is more rigid when its posterior or shrunken response is closer to
zero or positive than the response of comparable active entities.

### 4.3 Label enrichment

Known high-risk labels are positives. Unlabelled entities are not assumed to be
negatives. Evaluation therefore reports positive-unlabelled enrichment,
precision at the top-k rigidity tail, lift, and uncertainty intervals.

## 5. Main models

1. Event-study model for `log1p(volume_usd)` with entity and event-hour fixed
   effects and entity-clustered uncertainty.
2. Count model for transfer counts, preferably Poisson pseudo-maximum
   likelihood with high-dimensional fixed effects.
3. Extensive-margin model for `transfer_any`.
4. Time-to-next-transfer model as a complementary delay outcome.
5. Partially pooled entity heterogeneity model for the rigidity ranking.

## 6. Identification assumptions

1. Network fee shocks are not caused by the focal entity's own cash-out
   decision.
2. In the retained stable-market windows, no simultaneous market shock drives
   both fees and exchange-bound transfers after controls.
3. Entities are at risk of transferring in comparable pre- and post-event
   periods.
4. Event timing is defined without using future outcomes.
5. Label availability affects evaluation but not construction of the rigidity
   signal.

These assumptions are assessed rather than asserted.

## 7. Required falsification and robustness checks

- Pre-trend and anticipatory-effect tests.
- Placebo event times sampled from the same hour-of-week and market regime.
- Negative-control outcomes, including transfers not directed to CEX addresses.
- Alternative shock thresholds and rolling-window lengths.
- One-, three-, and six-hour aggregation.
- Leave-one-event-out estimates.
- Exclusion of the largest one or two shocks.
- Separate USDC and USDT estimates.
- Alternative active-entity inclusion thresholds.
- Stable-market definition sensitivity.
- Multiple-testing control for event-time coefficients.
- Sensitivity to CEX label category and label update date.

## 8. Interpretation boundary

The defensible conclusion is:

> Some entities exhibit unusually weak behavioural response to externally
> imposed transaction-cost shocks, conditional on observed market conditions.

The study must not claim that rigidity proves money laundering, sanctions
evasion, urgency, or fear of asset freezing.

