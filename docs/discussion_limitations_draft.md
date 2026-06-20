# Discussion and Limitations Draft

> This chapter is written around the current pilot evidence. Statements marked
> as provisional must be updated after the full event sample is available.

## Discussion

### A stress test is more defensible than an intent detector

The project began with an ambitious proposition: entities that continue
exchange-bound activity during sharp fee increases may face constraints that
make them less cost-sensitive. The analysis supports retaining the first half
of this proposition and substantially narrowing the second. Cost sensitivity
is observable. The latent reason for low sensitivity is not.

This distinction is the main conceptual contribution. A regulator or
investigator can audit the event, the prior activity level, expected activity,
observed activity, placebo behaviour, and uncertainty. The same evidence cannot
establish urgency, fear of freezing, sanctions evasion, or laundering intent.
Behavioural rigidity is therefore best understood as a prioritisation signal
for further inquiry, conditional on independent evidence, rather than an AML
decision by itself.

### Why the dynamic risk-set correction matters

The pilot initially appeared to show a dramatic and consistent decline in
CEX-bound activity during all three fee shocks. That interpretation weakened
after applying symmetric risk-set construction to real and pseudo events.
Entities were originally selected because they had transferred before the real
event. Even in the absence of treatment, many would not transfer again during a
short subsequent window. This selection process creates regression to the mean
and can produce a convincing but mechanical event-study decline.

Reconstructing each placebo risk set from its own preceding 48 hours changed
the substantive conclusion. The extreme E002 event remained associated with
unusually low subsequent activity, whereas E020 and E047 were broadly similar
to placebo windows. This is not merely a robustness footnote. It demonstrates
why auditable causal assessment can be more valuable than a more elaborate
predictive model: the correction changes what the evidence is allowed to mean.

### Extreme shocks may be qualitatively different

The current evidence is consistent with a threshold rather than a smooth
elasticity story. E002 involved an exceptionally large fee increase and showed
the clearest placebo-adjusted suppression. More moderate events did not.
If this pattern survives the full sample, it would imply that a continuous
average elasticity is an incomplete summary. Ordinary congestion may coincide
with high transactional demand, while only severe friction meaningfully
interrupts planned exchange-bound transfers.

The final analysis should therefore report both:

- the continuous CEX-specific fee interaction; and
- event-level responses ordered by shock severity.

An effect driven only by E002 would be substantively interesting but narrow:
the stress test would apply to extreme network disruption, not routine fee
variation.

### Transaction count is more interpretable than volume

USD volume was much more volatile than transaction count in the pilot.
Individual large transfers could raise event-period volume even when the
number of transactions and active entities fell. For a behavioural stress
test, transaction count and the extensive margin more directly represent
whether an action was continued or deferred. Volume remains relevant, but it
should not determine the primary conclusion.

This result also illustrates a broader AML measurement problem. Aggregate
value can be dominated by institutional or operational flows that are
unrelated to the behavioural mechanism of interest. Transparent outcome
selection is therefore part of auditability.

### A negative-control comparison is necessary

All Ethereum users face the same fee environment. A decline in CEX-bound
transfers may simply reflect a network-wide reduction in stablecoin activity.
The planned comparison with non-CEX USDC/USDT transfers is therefore central,
not optional. Only a larger decline in CEX-bound activity supports a
cash-out-proxy interpretation.

If CEX-bound and non-CEX transfers respond equally, the study will still
estimate a general cost response, but it will not identify a specifically
AML-relevant bottleneck. The dissertation must preserve this distinction even
if it weakens the original narrative.

### Label scarcity limits AML-specific validation

The pilot produced no direct OFAC-labelled senders and only a small number of
Tornado Cash persona addresses. Those positives were not enriched in the upper
rigidity tail. Several interpretations remain possible:

1. rigidity is not AML-specific;
2. the labels cover too little of the relevant population;
3. labelled entities use operational patterns different from direct transfers
   to CEX addresses;
4. the selected events do not coincide with periods when labelled entities
   were active; or
5. address-level labels fail to capture multi-address entity control.

The available data cannot distinguish these explanations. A null enrichment
result should therefore be reported as absence of validation, not proof that
the behavioural measure is useless. Equally, label scarcity cannot be used to
protect the hypothesis from falsification. The correct conclusion is that AML
specificity remains unestablished.

## Limitations

### The cash-out proxy is indirect

A transfer to a labelled CEX address does not demonstrate fiat conversion.
It may represent internal treasury management, collateral movement, market
making, exchange-to-exchange routing, or a deposit that remains in crypto.
The outcome is exchange-bound stablecoin activity, not observed cash-out.

### Address labels are incomplete and time-varying

Dune labels may be incomplete, updated after the historical event, or derived
from activity-based models. The present extraction uses the label table
available at query time, which may introduce look-ahead in address
classification. Where possible, label creation and update timestamps should be
reported and sensitivity analyses should restrict labels to those available
before each event.

### An address is not necessarily an entity

The sender address is a transparent and reproducible unit, but one actor may
control many addresses and one smart-contract address may represent many
users. Address clustering could improve entity interpretation but would
introduce additional assumptions and possible privacy concerns. The
dissertation should consistently use "address-level entity proxy."

### Fee shocks are not perfectly exogenous

Network fees are generated by demand for block space. Even after filtering
market volatility and depegging, unobserved events may affect both fees and
stablecoin transfers. The negative-control comparison and placebo tests reduce
but do not eliminate this concern. The design identifies evidence consistent
with a friction response under stated assumptions, not a laboratory-randomised
effect.

### Base fee is not realised entity cost

Average base fee measures network friction but not the exact fee paid by each
entity. Realised cost depends on gas used, priority fee, contract path, and ETH
price. A network-level treatment avoids conditioning on a transaction that
only exists when the entity chooses to act, but it also creates measurement
error. Transaction-level realised cost should remain a secondary descriptive
measure rather than the main treatment.

### Temporary and recurrent treatments complicate event studies

Fee shocks are temporary, may cluster, and expose all users simultaneously.
There is no obvious untreated Ethereum group. Standard staggered-adoption
difference-in-differences assumptions do not directly apply. The design relies
on timing, placebo windows, negative-control outcomes, and replication across
events.

### Few event clusters limit inference

The target sample contains 20 events. Conventional hourly standard errors would
overstate precision because treatment varies at event-hour level. Event-
clustered uncertainty and wild-cluster bootstrap inference are required.
Results based on only the three pilot events are exploratory regardless of the
number of hourly or entity rows.

### Positive labels are selected positives

OFAC and Tornado Cash labels represent specific enforcement and typology
processes. They are not a random sample of all laundering-relevant entities.
Positive-unlabelled lift therefore evaluates alignment with those public label
processes, not sensitivity or specificity for money laundering in general.

### Generalisability is limited

The study covers Ethereum, USDC/USDT, labelled CEX destinations, and the
2022-2026 fee environment. Results may not generalise to layer-2 networks,
Bitcoin, privacy coins, decentralised exchanges, bridges, other stablecoins,
or future fee regimes.

## Provisional conclusion

The pilot's strongest contribution is methodological rather than predictive.
It shows how an initially persuasive behavioural pattern can weaken when
pre-selection is reproduced at placebo times. The final dissertation will be
valuable if it preserves that discipline: a narrow, auditable conclusion is
preferable to an impressive risk score whose causal meaning cannot be
defended.

