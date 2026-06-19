# Methods Draft

## Research design

This study develops an auditable behavioural stress test for exchange-bound
stablecoin activity on Ethereum. The central question is whether entities
reduce or delay transfers to labelled centralised-exchange (CEX) addresses when
network transaction costs rise sharply. The design does not attempt to infer
criminal intent. Instead, it estimates observable sensitivity to an externally
imposed operational friction and evaluates whether unusually weak sensitivity
is associated with independently constructed risk labels.

The empirical strategy has two stages. First, a long-run six-hour Ethereum
series is used to locate candidate fee shocks between January 2022 and April
2026. Second, selected events are studied using hourly transfer and market data
in event windows extending seven days before and after the shock.

## Data sources and sample

Ethereum block, token-transfer, price, and address-label data are obtained
through Dune Analytics. The transfer sample contains USDC and USDT ERC-20
transfers. A transfer is classified as CEX-bound when its receiver appears in
Dune's Ethereum `cex users` address category. This is a proxy for
exchange-related stablecoin movement rather than direct observation of fiat
cash-out.

The entity proxy is the transfer-level sending address. Addresses are retained
as pseudonymous technical identifiers and are hashed in derived modelling
files. No attempt is made to identify natural persons or combine addresses
using speculative ownership heuristics.

## Fee-shock discovery

Candidate events are identified from the average Ethereum base fee in
non-overlapping six-hour intervals. For each interval \(t\), the threshold is
the 99th percentile of the previous 90 days:

\[
q_t = Q_{0.99}(C_{t-1}, \ldots, C_{t-W}).
\]

An interval is a candidate shock when its average fee exceeds \(q_t\), is at
least 1.5 times the lagged rolling median, and exceeds that median by at least
5 Gwei. All threshold components are lagged so the candidate observation does
not determine its own treatment status. Adjacent candidates separated by no
more than 12 hours are grouped into one event. A greedy selection retains
events whose analysis windows are at least 14 days apart.

The six-hour data are used only for long-run discovery. Hourly observations are
used for event analysis.

## Market-stability screen

The proposed interpretation requires separating fee friction from market
panic. Candidate events are therefore excluded when the interval from six
hours before the event to six hours after it contains:

1. an absolute ETH hourly log return above 5%;
2. a USDC or USDT price deviation from USD 1 above 2%; or
3. 24-hour ETH volatility above the lagged 95th percentile of the previous
   year.

Of 32 non-overlapping candidate windows, 20 pass this screen. This screening
rule uses no entity-level transfer outcome.

## Outcomes

The primary outcomes are:

- hourly CEX-bound transaction count;
- whether a baseline-active entity makes any transfer during the shock;
- entity transaction count during the shock; and
- time until the next qualifying transfer.

USD volume is secondary because large individual transfers can dominate an
hourly total. Non-CEX USDC/USDT transfers form a negative-control outcome that
captures general stablecoin activity under the same network conditions.

## Aggregate causal comparison

The primary aggregate model compares CEX-bound and non-CEX activity:

\[
\log(1 + Y_{g e t}) =
\alpha_e + \delta_g + \lambda_{h(t)}
+ \beta_1 \log(1+C_{et})
+ \beta_2 \left[\mathbb{1}(g=\text{CEX})\log(1+C_{et})\right]
+ X_{et}'\theta + \epsilon_{get},
\]

where \(g\) indexes destination group, \(e\) event, and \(t\) hour.
\(\alpha_e\) are event effects, \(\lambda_{h(t)}\) are hour-of-week effects,
and \(X_{et}\) contains ETH return, lagged volatility, stablecoin depeg, and
block-utilisation controls. The interaction coefficient \(\beta_2\) estimates
whether CEX-bound activity is more fee-sensitive than general stablecoin
activity.

The final specification will use count-compatible models and uncertainty
clustered at event level. With only three pilot events, reported HAC standard
errors are exploratory and are not treated as final inference.

## Entity risk sets and behavioural rigidity

Selecting entities because they were active before an event can mechanically
produce a post-event decline through regression to the mean. The study
therefore defines every real and placebo risk set using the same rolling
look-back rule. For a candidate evaluation hour \(\tau\), eligible entities are
selected only from activity in the preceding 48 hours. Expected seven-hour
activity is:

\[
\widehat{Y}^{\,0}_{e,\tau}
= \frac{7}{48}Y^{pre}_{e,\tau}.
\]

An entity-level rigidity residual is constructed from observed minus expected
shock-period activity and standardised by expected activity:

\[
R_{e,\tau}
= \frac{Y^{obs}_{e,\tau}-\widehat{Y}^{\,0}_{e,\tau}}
{\sqrt{\widehat{Y}^{\,0}_{e,\tau}+1}}.
\]

The final rigidity ranking will use partial pooling across events and condition
on baseline transaction frequency. A high score means that an entity remains
more active than comparable baseline-active entities; it does not imply illicit
intent.

## Positive-unlabelled evaluation

OFAC-sanction and Tornado Cash persona labels are treated as separately
reported positive sets. Unlabelled entities are not treated as legitimate
negatives. Evaluation therefore reports top-decile lift, positive coverage,
and exact uncertainty rather than classification accuracy or ROC AUC.

## Robustness and falsification

The planned checks include:

- dynamically reconstructed pseudo-event risk sets;
- one-, three-, and six-hour aggregation;
- alternative activity thresholds;
- leave-one-event-out estimates;
- exclusion of the largest shock;
- separate USDC and USDT outcomes;
- alternative event thresholds and market-stability definitions;
- CEX-bound versus non-CEX negative-control outcomes;
- hour-of-week-matched placebo dates;
- pre-trend tests; and
- event-level wild-cluster bootstrap inference.

## Ethical interpretation

The analysis concerns pseudonymous transaction patterns and public technical
labels. It does not identify wallet holders, observe fiat withdrawal, or
establish money laundering. Findings are reported as behavioural responses and
limitations of auditable AML analytics, not allegations about individuals or
organisations.

