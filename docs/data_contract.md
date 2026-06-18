# Data Contract

## Long-run six-hour screening data

Expected file:
`data/processed_regime/ethereum_regime_6h.parquet`

Required fields:

- `time`
- `avg_gas_gwei`
- `median_gas_gwei`
- `max_gas_gwei`
- `block_count`
- `stablecoin_volume_usd`
- `transfer_count`
- `transaction_count`

## Event catalogue

Expected output:
`results/event_catalog/analysis_events.csv`

Required fields:

- `event_id`
- `event_start`
- `event_end`
- `peak_time`
- `peak_avg_gas_gwei`
- `lagged_threshold_gwei`
- `event_interval_count`
- `window_start`
- `window_end`
- `market_stable`
- `analysis_eligible`
- `exclusion_reason`

## Entity-hour event panel

Expected output:
`data/processed_panel/entity_hour_event_panel.parquet`

Required fields:

- `event_id`
- `hour`
- `relative_hour`
- `entity_id`
- `token_symbol`
- `cex_name`
- `transfer_any`
- `transfer_count`
- `transaction_count`
- `volume_token`
- `volume_usd`
- `network_base_fee_gwei`
- `network_priority_fee_gwei`
- `eth_price_usd`
- `eth_return_1h`
- `eth_volatility_24h`
- `stablecoin_depeg_abs`
- `is_fee_shock`
- `known_positive`
- `positive_label_source`

## Privacy and reporting

- Raw addresses remain local and are excluded from version control.
- Published tables use salted hashes or aggregate identifiers.
- No attempt is made to identify natural persons.
- Unlabelled entities are never called negative, legitimate, or clean.

