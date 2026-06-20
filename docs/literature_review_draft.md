# Literature Review Draft

## 1. From transaction classification to auditable behavioural evidence

Most empirical crypto-AML research treats detection as a supervised or
weakly-supervised classification problem. The Elliptic Bitcoin dataset made it
possible to compare logistic regression, random forests, neural networks, and
graph convolutional networks on illicit-transaction labels (Weber et al.,
2019). Later work expanded the unit of analysis from transactions to addresses
and user graphs (Elmougy and Liu, 2023), while Elliptic2 framed laundering as a
subgraph-representation problem (Bellei et al., 2024). These studies show the
value of relational structure, but their primary estimand remains predictive:
whether a model can distinguish labelled illicit observations from other
observations.

Prediction is not the same as an auditable behavioural explanation. A high
score can combine many correlated features without establishing why an entity
behaved as it did or what would have happened under a changed operational
constraint. This distinction is especially important in AML settings, where
labels are scarce, selected through enforcement and investigation processes,
and unlikely to be representative of all illicit activity. Lorenz et al.
(2020), for example, explicitly study Bitcoin AML under label scarcity and
show the limitations of unsupervised anomaly detection. The practical label
problem also means that unlabelled observations cannot safely be interpreted
as legitimate negatives.

The present study takes a different route. It does not attempt to replace graph
classification with a new classifier. It asks whether an observable network
friction changes exchange-bound behaviour and whether heterogeneous responses
can be described in a transparent decision record. The output is therefore a
stress-test response, not a probability that an entity is criminal.

## 2. Transaction fees as operational friction

Ethereum transaction fees are not merely a technical variable. They ration
scarce block space and affect the timing and cost of user actions. Liu et al.
(2022) study the causal effects of EIP-1559 using blockchain, mempool, and
exchange data. They find that the mechanism changed fee dispersion and waiting
times, while fee levels were also related to market conditions. Their evidence
supports two elements of the current design: fees can alter user timing, and
market volatility must be separated from fee effects.

However, a high fee is not automatically an exogenous shock. Demand for block
space can rise during market stress, token launches, liquidations, or other
events that simultaneously change stablecoin transfers. In the proposal's
causal notation, market conditions \(M\) affect both cost \(C\) and outcome
\(Y\). A regression of transfer activity on gas fees therefore mixes network
friction with the demand shocks that produced congestion.

This motivates the study's two-stage design. Long-run data locate candidate
fee shocks using thresholds based only on prior observations. ETH returns,
rolling volatility, and stablecoin depegging then exclude obvious market-panic
periods. Finally, CEX-bound activity is compared with non-CEX stablecoin
activity under the same network conditions. The comparison does not make the
shock perfectly random, but it tests whether any decline is specific to the
cash-out proxy rather than a general fall in Ethereum activity.

## 3. Causal assessment and falsification

Pearl (2009) emphasises that causal conclusions require assumptions about the
data-generating structure, not only predictive association. Varian (2016)
similarly describes the value of quasi-experimental reasoning and explicit
counterfactual questions in economic and marketing data. In security
measurement, Mariconti et al. (2017) argue for testable causal assessment
rather than interpreting correlated user actions as causes.

This study applies that logic to blockchain behaviour. The treatment is a
pre-determined network-level fee event. Outcomes are measured at hourly and
entity-event levels. Falsification is built into the design through:

- pseudo-event times with independently reconstructed prior risk sets;
- pre-trend diagnostics;
- non-CEX stablecoin negative-control outcomes;
- alternative temporal aggregation;
- alternative fee thresholds; and
- leave-one-event-out analysis.

The dynamic risk-set placebo is particularly important. If entities are
included because they were active before the real event, their activity will
often fall afterwards even without treatment. Reconstructing the risk set from
the preceding look-back window at every real and pseudo event applies the same
selection mechanism to all comparisons. The pilot analysis demonstrates that
this correction can materially change the substantive conclusion.

The design differs from conventional staggered-adoption difference-in-
differences. Fee events are temporary, may recur, and expose all Ethereum users
at once. There is no clean contemporaneous untreated population. The
identifying evidence instead comes from within-event timing, negative-control
outcomes, pseudo events, and cross-event replication. Consequently, event-
level uncertainty and sensitivity to individual shocks are more informative
than a mechanically precise hourly standard error.

## 4. Behavioural rigidity and heterogeneous response

The proposal's substantive construct is behavioural rigidity: continuing a
cash-out-proxy action despite a sharp increase in its operational cost. This is
not equivalent to a raw post-event transaction count. Highly active entities
are mechanically more likely to transact during any short window, while
infrequent entities are likely to record zero even without a shock. Rigidity
must therefore be estimated relative to an entity's expected activity and
partially pooled across events.

The pilot results reinforce this point. Entities with ten or more baseline
transactions were far more likely to remain active during a seven-hour shock
than entities with only two baseline transactions. A defensible rigidity
measure consequently uses observed-minus-expected activity, standardisation,
and baseline-frequency controls. The final score is descriptive of response to
friction; latent urgency or perceived enforcement risk remains only one
possible explanation.

## 5. Positive-unlabelled validation

Public blockchain risk labels create a positive-unlabelled problem. Known
sanctioned or typology-linked addresses can be treated as positives, but an
unlabelled address may be benign, undetected, newly created, or outside the
coverage of the label provider. Standard binary accuracy and ROC measures
would silently misclassify the unlabelled set as negative.

PU-learning research formalises this setting. Kiryo et al. (2017) develop a
non-negative PU risk estimator that avoids overfitting when only positive and
unlabelled examples are available. Hammoudeh and Lowd (2020) show that
selection bias in the positive set is itself consequential. These results
support a conservative evaluation strategy: report positive coverage, lift in
the upper rigidity tail, exact uncertainty, and label-source sensitivity
rather than claim supervised classification performance.

In the current pilot, direct OFAC positives were absent and Tornado Cash
persona labels were sparse. This is not evidence that the signal fails or
succeeds as an AML measure; it is evidence that public labels provide weak
validation power. The final dissertation should treat label enrichment as a
secondary research question and report a null result without attempting to
manufacture negative labels.

## 6. Governance and interpretability

The regulatory motivation should be stated carefully. Regulation (EU)
2023/1114 (MiCA) is relevant to governance and operational expectations for
crypto-asset service providers, but it does not by itself validate this
specific analytical method. The methodological claim is narrower: an
investigator can audit the event definition, market exclusions, entity
baseline, expected response, observed response, and uncertainty supporting
each rigidity flag.

This produces a qualitatively different decision record from an opaque score.
The record can state:

1. which exogenous-looking friction event was used;
2. why the event passed the market-stability screen;
3. how active the entity was before comparable real and placebo windows;
4. how much activity was expected;
5. what was observed; and
6. whether the result replicated across events and specifications.

Interpretability here is therefore procedural rather than cosmetic. The model
is auditable because the inferential chain is exposed and falsifiable, not
because a post-hoc feature-importance chart accompanies a black-box prediction.

## 7. Research gap and contribution

The literature contains sophisticated predictive crypto-AML models and
empirical analyses of blockchain transaction fees, but little work combines
the two as a causal behavioural stress test. This dissertation contributes:

1. a pre-determined and reproducible fee-event catalogue;
2. a market-stability screen separating congestion from obvious panic;
3. a CEX-bound versus non-CEX negative-control design;
4. symmetric real and pseudo-event risk-set construction;
5. an activity-calibrated entity rigidity measure; and
6. PU evaluation that preserves the distinction between unlabelled and
   legitimate.

The contribution is methodological even if the final label-enrichment result
is null. A null result would show that transparent cost rigidity cannot be
treated as an AML-specific signal without stronger labels or additional
behavioural evidence.

## Working references

- Bellei, C. et al. (2024). *The Shape of Money Laundering: Subgraph
  Representation Learning on the Blockchain with the Elliptic2 Dataset*.
  https://arxiv.org/abs/2404.19109
- Elmougy, Y. and Liu, L. (2023). *Demystifying Fraudulent Transactions and
  Illicit Nodes in the Bitcoin Network for Financial Forensics*.
  https://arxiv.org/abs/2306.06108
- Hammoudeh, Z. and Lowd, D. (2020). *Learning from Positive and Unlabeled Data
  with Arbitrary Positive Shift*. https://arxiv.org/abs/2002.10261
- Kiryo, R. et al. (2017). *Positive-Unlabeled Learning with Non-Negative Risk
  Estimator*. https://arxiv.org/abs/1703.00593
- Liu, Y. et al. (2022). *Empirical Analysis of EIP-1559: Transaction Fees,
  Waiting Time, and Consensus Security*. https://arxiv.org/abs/2201.05574
- Lorenz, J. et al. (2020). *Machine Learning Methods to Detect Money
  Laundering in the Bitcoin Blockchain in the Presence of Label Scarcity*.
  https://arxiv.org/abs/2005.14635
- Mariconti, E. et al. (2017). *The Cause of All Evils: Assessing Causality
  Between User Actions and Malware Activity*. USENIX CSET 2017.
- Pearl, J. (2009). *Causality: Models, Reasoning, and Inference*, 2nd ed.
- Regulation (EU) 2023/1114 of the European Parliament and of the Council.
  http://data.europa.eu/eli/reg/2023/1114/oj
- Varian, H. R. (2016). Causal inference in economics and marketing. *PNAS*,
  113(27), 7310-7315.
- Weber, M. et al. (2019). *Anti-Money Laundering in Bitcoin: Experimenting
  with Graph Convolutional Networks for Financial Forensics*.
  https://arxiv.org/abs/1908.02591

