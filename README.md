# Fee Regime Classification and Stablecoin Transfer Behaviour for Auditable Crypto-AML
 
This repository contains the code, data workflow, and research notes for my MSc dissertation in Crime Science with Data Science at University College London.
 
The project studies whether Ethereum gas-fee shocks can be used as an interpretable behavioural signal for crypto-AML analysis, focusing on USDC and USDT transfer behaviour around exchange-related addresses.
 
> An MSc dissertation on Ethereum gas fees, stablecoins, and academic survival.
 
## Project Overview
 
Crypto-AML systems often rely on risk scores or behavioural indicators that can be difficult to interpret and audit. Ethereum gas fees may provide a useful signal because they represent the cost of executing a transaction.
 
However, gas fees do not always have the same behavioural meaning. In low-fee periods, relatively higher fees may mainly reflect increased network activity. In genuinely high-fee periods, extreme fee increases may operate as transaction-cost pressure and may discourage non-urgent transfers.
 
This dissertation therefore first identifies Ethereum fee regimes before analysing whether stablecoin transfer behaviour changes around high-fee stress events.
 
## Research Questions
 
1. Can Ethereum activity be separated into low-fee, normal-fee, and high-fee stress regimes?
2. Do USDC and USDT transfers involving exchange-related addresses respond differently to gas-fee increases across these regimes?
3. Are genuinely high-fee periods more useful for behavioural stress testing than ordinary relative fee spikes?
4. Can these findings be communicated as transparent and auditable behavioural signals rather than opaque risk scores?
 
## Background and Previous Exploratory Work
 
A previous exploratory pilot analysis, completed for a separate module, compared two Ethereum fee environments using hourly stablecoin transfers to exchange-related addresses.
 
The pilot suggested that gas-fee shocks may not have the same meaning across fee regimes. In low-fee environments, higher gas fees may reflect increased network activity, while in higher-fee environments, extreme gas-fee shocks may be associated with lower transfer activity.
 
This pilot is used only as exploratory background and motivation. It is not treated as final dissertation evidence.
 
## Current Dissertation Progress
 
The dissertation-specific work has now moved into the event-identification and dataset-construction stage.
 
Current progress:
 
- Initial research proposal developed
- Dissertation ethics form submitted
- Previous exploratory pilot analysis completed in a separate module
- Dissertation design refined based on pilot findings
- Dune data extraction pipeline tested
- Approximately two years of Ethereum fee and stablecoin transfer data extracted at six-hour intervals
- Long-term fee-regime detection script implemented
- Candidate high-fee event detection implemented
- Initial event catalogue structure created
 
Current practical limitation:
 
- Dune API credit limits currently restrict further extraction of event-window data.
 
Next steps:
 
- Manually review and classify candidate high-fee events
- Finalise eligible event windows
- Extract remaining event-window data after Dune credits refresh
- Construct the entity-level main analysis dataset
- Run main statistical analysis and robustness checks
- Prepare dissertation figures, tables, and final write-up
 
## Data
 
The project uses secondary digital data derived from publicly accessible Ethereum blockchain activity, primarily structured through Dune Analytics.
 
The data may include:
 
- Ethereum block timestamps
- Gas-fee measures
- USDC and USDT transfer amounts
- Transaction counts
- Token type
- Wallet or address labels
- Exchange-related address classifications
- Time-based market and network activity measures
 
Transfers involving exchange-related addresses are treated as a proxy for exchange-related stablecoin movement. They are not treated as direct evidence of fiat cash-out, money laundering, or criminal behaviour.
 
Raw address-level files are not uploaded to the public repository and remain stored locally under the ignored `data/` directory.
 
## Methodological Plan
 
The planned workflow is:
 
1. Extract and clean long-term Ethereum fee and stablecoin transfer data
2. Construct six-hour interval datasets for regime detection
3. Identify low-fee, normal-fee, and high-fee regimes
4. Detect candidate high-fee stress events
5. Review and classify candidate events
6. Extract event-window and entity-level stablecoin transfer data
7. Build the main analysis dataset
8. Run statistical analysis and robustness checks
9. Interpret findings for auditable crypto-AML analytics
 
Potential methods include descriptive time-series analysis, event-study analysis, regression with time-series controls, panel regression, placebo tests, sensitivity checks, and negative-control analysis.
 
## Repository Structure
 
```text
.
├── README.md
├── requirements.txt
├── LICENSE
├── docs/
│   ├── analysis_decisions.md
│   ├── analysis_status.md
│   ├── data_contract.md
│   ├── discussion_limitations_draft.md
│   ├── dissertation_methods_draft.md
│   ├── dissertation_structure.md
│   ├── final_analysis_protocol.md
│   ├── literature_review_draft.md
│   └── pilot_results_draft.md
├── results/
│   ├── data_quality/
│   ├── event_catalog/
│   ├── pilot_analysis/
│   ├── pilot_robustness/
│   ├── regime_detection/
│   └── schema_audit/
├── scripts/
│   ├── audit_dune_schema.py
│   ├── audit_pilot_sender_labels.py
│   ├── build_analysis_panels.py
│   ├── build_event_catalog.py
│   ├── check_final_readiness.py
│   ├── detect_fee_regime_events.py
│   ├── extract_entity_event_transfers.py
│   ├── extract_hourly_market_controls.py
│   ├── extract_negative_control_outcomes.py
│   ├── run_negative_control_analysis.py
│   ├── run_pilot_analysis.py
│   ├── run_pilot_robustness.py
│   ├── screen_events_for_market_stability.py
│   └── validate_pipeline.py
└── data/
    ├── raw/
    ├── interim/
    └── processed/
```
 
The `data/` directory is ignored by Git and is used only for local raw, intermediate, or address-level data.
 
## Reproducibility
 
The repository includes scripts for data extraction, event detection, event screening, panel construction, pilot analysis, robustness checks, and pipeline validation.
 
Some steps require available Dune API credits.
 
Example commands from the repository root:
 
```powershell
python scripts/detect_fee_regime_events.py
python scripts/build_event_catalog.py
python scripts/extract_hourly_market_controls.py
python scripts/screen_events_for_market_stability.py
python scripts/extract_entity_event_transfers.py --all-eligible
python scripts/build_analysis_panels.py
python scripts/validate_pipeline.py
```
 
## Ethics and Responsible Data Use
 
This project does not involve interviews, surveys, experiments, or direct interaction with human participants.
 
Wallet addresses are treated as pseudonymous technical identifiers.
 
The project will not:
 
- Attempt to identify or deanonymise wallet holders
- Link blockchain addresses to real-world individuals
- Use private KYC records, leaked data, police data, or private exchange records
- Make allegations about identifiable individuals or organisations
- Treat behavioural patterns as proof of criminal intent
 
Results will primarily be reported at aggregate, group, regime, or pseudonymous level.
 
## Limitations
 
The project does not directly observe:
 
- The identity of wallet holders
- The motivation behind transactions
- Fiat withdrawal from exchanges
- Whether a transaction is illicit
- Whether an address is controlled by one person or multiple entities
 
Any detected pattern should therefore be interpreted as a behavioural or operational signal, not as evidence of criminal intent.
 
## Author
 
**Xinnuo Li**  
MSc Crime Science with Data Science  
University College London
 
## Academic Use
 
This repository is part of an MSc dissertation project.
 
Materials may change during the research process, and preliminary outputs should not be treated as final findings.
