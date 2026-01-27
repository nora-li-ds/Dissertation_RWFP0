

## Overview
This project develops a **Causal Stress Testing** framework to satisfy the explainability requirements of **MiCA Article 63**. 

### The Core Logic (The "Lie Detector")
We utilize Ethereum Gas Price fluctuations as a natural experiment to distinguish between:
1. **Cost-Elastic Entities (Normal Users):** Rational actors who pause transactions during high gas fee regimes.
2. **Cost-Rigid Entities (Laundering Scripts):** Actors constrained by non-market factors (e.g., enforcement risk) who must exit the system regardless of costs.

## Methodology
- **Step A:** Data ingestion via Dune Analytics (SQL).
- **Step B:** Regime filtering and Entity clustering.
- **Step C:** Causal inference via SCM & Causal-GNN.