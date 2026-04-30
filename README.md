# Gas Stress Test AML

This project is a pilot time-series analysis of Ethereum gas fees and stablecoin transfer behaviour. It was developed as part of a statistical modelling and causal inference coursework project.

The main idea is to explore whether Ethereum gas fees can be used as an interpretable behavioural signal for crypto-AML analytics. In particular, the project examines whether stablecoin transfers into Dune-labelled `cex users` addresses respond differently across low-fee and higher-fee market environments.

## Project Aim

The original motivation was to test whether high transaction costs could act as a behavioural stress test. If gas fees become expensive, cost-sensitive users may reduce transfer activity, while more rigid or urgent actors may continue transacting.

The current analysis takes a more cautious approach. It does not claim to identify illicit intent. Instead, it asks:

- Are Ethereum gas fees associated with stablecoin transfer volume?
- Does this relationship differ between a recent low-fee period and a historical higher-fee period?
- Can gas fees be used as a regime-dependent behavioural feature for AML risk modelling?

## Data

The data is extracted from Dune Analytics using the Dune API.

The main dataset contains hourly observations of:

- USDC/USDT transfer volume into Dune-labelled `cex users` addresses
- transfer count
- average Ethereum gas fee
- a sample-defined high-fee shock indicator
- log-transformed volume and gas variables

Two periods are used:

| Period | Description |
|---|---|
| August 2024 | Historical higher-fee comparison window |
| March–April 2026 | Recent low-fee baseline window |

Transfers into `cex users` addresses are used as a proxy for exchange-related cash-out activity. This is not direct evidence of fiat withdrawal.

## Methods

The analysis uses three main approaches:

1. **Descriptive comparison**
   - Compare gas fee levels and stablecoin transfer volume across the two periods.

2. **ARIMAX time-series models**
   - Separate ARIMAX models are estimated for each period.
   - This accounts for serial correlation in hourly transfer volume.

3. **Combined interaction model**
   - A pooled OLS model with interaction terms is used to compare whether the gas-volume relationship differs across the two fee environments.

This is not a formal Difference-in-Differences design, because there is no clean untreated control group or policy intervention. It is best understood as a comparative time-series pilot study.

## Key Finding

The results suggest that gas fees should not be mechanically interpreted as transaction-cost shocks.

In the recent low-fee 2026 period, higher gas fees are associated with higher stablecoin transfer volume, suggesting that gas fees mainly capture wider network activity.

In the higher-fee 2024 period, extreme high-fee hours appear to have a different relationship with transfer volume, suggesting that genuinely high gas spikes may begin to operate as transaction-cost pressure.

Overall, gas fees may be useful as an interpretable behavioural feature in crypto-AML modelling, but only when interpreted within the broader market-fee regime.

## Project Structure

```text
Gas-Stress-Test-AML/
├── data/
│   ├── raw/
│   │   └── 2024 daily Dune parquet files
│   ├── raw_2026/
│   │   └── 2026 daily Dune parquet files
│   ├── processed_2024/
│   │   └── dune_stablecoin_cex_hourly.csv
│   └── processed_2026/
│       └── dune_stablecoin_cex_hourly.csv
│
├── results_2026/
│   └── single-period 2026 model outputs
│
├── results_two_periods/
│   └── comparative ARIMAX and interaction model outputs
│
├── scripts/
│   ├── fetch_dune_hourly.py
│   ├── process_2024_existing.py
│   ├── analysis_arimax.R
│   └── analysis_two_periods.R
│
└── README.md
