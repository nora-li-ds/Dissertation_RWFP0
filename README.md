
# Fee Regime Classification and Stablecoin Transfer Behaviour for Auditable Crypto-AML

This repository contains the code, data-processing workflow, and analytical materials for my MSc dissertation in Crime Science with Data Science at University College London.

## Project Overview

Crypto-asset anti-money laundering systems often rely on risk scores or behavioural indicators that may be difficult to interpret and audit. One potential indicator is the Ethereum gas fee, which represents the cost of processing a transaction on the network.

However, gas fees may not have a fixed behavioural meaning. In low-fee environments, relatively higher gas fees may mainly reflect increased network activity. In genuinely high-fee environments, extreme fee increases may instead operate as transaction-cost pressure and discourage non-urgent transfers.

This project investigates whether Ethereum fee regimes should be identified before gas-fee behaviour is used as an interpretable signal in crypto-AML analysis.

## Research Aim

The main aim is to examine whether stablecoin transfer behaviour responds differently to transaction-cost pressure across different Ethereum fee regimes.

The project focuses on the following questions:

1. Can Ethereum activity be separated into distinct low-fee, normal-fee, and high-fee stress regimes?
2. Do USDC and USDT transfers involving exchange-related addresses respond differently to gas-fee increases across these regimes?
3. Are genuinely high-fee periods more informative for behavioural stress testing than ordinary relative fee spikes?
4. Can these findings be communicated as transparent and auditable behavioural signals rather than opaque risk scores?

## Background

A preliminary pilot analysis compared two Ethereum fee environments using hourly stablecoin transfers to exchange-related addresses.

The initial findings suggested that:

- continuous gas fees were positively associated with stablecoin transfer activity in both periods;
- relative gas-fee shocks did not have the same meaning across regimes;
- in a low-fee environment, higher gas fees appeared to reflect increased network activity;
- in a higher-fee environment, extreme gas-fee shocks were associated with lower transfer activity.

These findings motivate the current dissertation design, which treats fee-regime classification as a necessary first step before analysing behavioural cost sensitivity.

The pilot analysis should be interpreted as exploratory rather than causal evidence.

## Data

The project uses secondary digital data derived from publicly accessible Ethereum blockchain activity.

The data may include:

- Ethereum block timestamps;
- gas-fee measures;
- USDC and USDT transfer amounts;
- transaction counts;
- token type;
- wallet or address labels;
- exchange-related address classifications;
- time-based market and network activity measures.

The data are primarily accessed and structured through Dune Analytics. The underlying transaction records are publicly visible on the Ethereum blockchain.

Transfers involving exchange-related addresses are treated as a proxy for exchange-related stablecoin movement. They are not treated as direct evidence of fiat cash-out, money laundering, or criminal behaviour.

## Planned Methodology

The analytical workflow may include:

1. Data extraction and cleaning
2. Construction of hourly or daily time-series datasets
3. Exploratory analysis of gas-fee distributions
4. Identification and classification of Ethereum fee regimes
5. Detection of genuinely high-fee stress windows
6. Comparison of stablecoin transfer behaviour across fee regimes
7. Time-series and/or panel modelling
8. Robustness checks and sensitivity analysis
9. Interpretation of findings for auditable crypto-AML analytics

Possible statistical methods include:

- descriptive time-series analysis;
- change-point or regime-detection methods;
- regression with time-series controls;
- interrupted time-series analysis;
- regression discontinuity in time;
- panel regression for wallet- or entity-level analysis;
- placebo and sensitivity tests.

The final methodology may be revised based on data quality, model diagnostics, and supervisor feedback.

## Repository Structure

```text
.
├── README.md
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── sql/
│   └── dune_queries/
├── notebooks/
│   ├── exploratory_analysis/
│   └── modelling/
├── src/
│   ├── data_processing/
│   ├── feature_engineering/
│   ├── regime_detection/
│   └── modelling/
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── model_results/
├── docs/
│   ├── proposal/
│   ├── ethics/
│   └── notes/
└── requirements.txt
```

The folder structure may change as the project develops.

## Reproducibility

The repository will contain:

* Dune SQL queries;
* data-cleaning scripts;
* feature-construction code;
* modelling scripts;
* figure-generation code;
* model diagnostics;
* documentation of analytical decisions.

Large raw datasets and potentially traceable address-level files may not be uploaded directly to the public repository.

Where possible, the repository will instead provide:

* reproducible queries;
* data-processing instructions;
* aggregated outputs;
* appropriately minimised sample data.

## Ethics and Responsible Data Use

This project does not involve interviews, surveys, experiments, or direct interaction with human participants.

Wallet addresses are treated as pseudonymous technical identifiers.

The project will not:

* attempt to identify or deanonymise wallet holders;
* link blockchain addresses to real-world individuals;
* use private KYC records, leaked data, police data, or private exchange records;
* make allegations about identifiable individuals or organisations;
* treat behavioural patterns as proof of criminal intent.

Results will primarily be reported at aggregate, group, regime, or pseudonymous level. Address-level data will be minimised where possible.

Ethics approval or exemption must be obtained before data collection or analysis outside the approved research design begins.

## Current Status

* [x] Initial research proposal developed
* [x] Preliminary Dune data pipeline tested
* [x] Pilot comparative time-series analysis completed
* [x] Dissertation ethics form submitted
* [ ] Ethics decision received
* [ ] Final research design confirmed
* [ ] Fee-regime classification method selected
* [ ] Main dataset constructed
* [ ] Main statistical analysis completed
* [ ] Robustness checks completed
* [ ] Dissertation figures and tables finalised
* [ ] Final dissertation submitted

## Limitations

The project does not directly observe:

* the identity of wallet holders;
* the motivation behind transactions;
* fiat withdrawal from exchanges;
* whether a transaction is illicit;
* whether an address is controlled by one person or multiple entities.

Any detected pattern should therefore be interpreted as a behavioural or operational signal, not as evidence of criminal intent.

## Author

**Xinnuo Li**
MSc Crime Science with Data Science
University College London

## Academic Use

This repository is part of an MSc dissertation project.

Materials may change during the research process, and preliminary outputs should not be treated as final findings.


