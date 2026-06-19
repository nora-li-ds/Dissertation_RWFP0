"""Validate reproducibility and privacy invariants for current local outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def validate_events() -> None:
    path = ROOT / "results" / "event_catalog" / "eligible_events.csv"
    events = pd.read_csv(
        path,
        parse_dates=[
            "event_start",
            "event_end",
            "peak_time",
            "window_start",
            "window_end",
        ],
    )
    require(events["event_id"].is_unique, "event IDs are unique")
    require(
        events["event_start"].le(events["peak_time"]).all()
        and events["peak_time"].le(events["event_end"]).all(),
        "event peaks lie inside event intervals",
    )
    eligible = events.loc[events["analysis_eligible"].astype(str).eq("True")]
    require(len(eligible) == 20, "20 events pass the current stability screen")
    ordered = eligible.sort_values("peak_time")
    require(
        ordered["peak_time"].diff().dropna().ge(pd.Timedelta(days=14)).all(),
        "eligible event peaks are separated by at least 14 days",
    )


def validate_market_controls() -> None:
    path = (
        ROOT / "data" / "processed_market" / "hourly_market_controls.csv"
    )
    controls = pd.read_csv(path, parse_dates=["hour"])
    require(len(controls) == 37944, "hourly market-control row count is complete")
    require(controls["hour"].is_unique, "market-control timestamps are unique")
    require(
        controls["hour"].diff().dropna().eq(pd.Timedelta(hours=1)).all(),
        "market controls have continuous hourly spacing",
    )
    core = [
        "avg_base_fee_gwei",
        "eth_price_usd",
        "usdc_price_usd",
        "usdt_price_usd",
    ]
    require(
        not controls[core].isna().any().any(),
        "core market-control fields contain no missing values",
    )


def validate_panels() -> None:
    hourly_path = (
        ROOT / "data" / "processed_panel" / "event_hour_panel.csv.gz"
    )
    entity_path = (
        ROOT
        / "data"
        / "processed_panel"
        / "entity_event_period_panel.csv.gz"
    )
    hourly = pd.read_csv(hourly_path)
    entity = pd.read_csv(entity_path)

    require(
        not hourly.duplicated(["event_id", "hour"]).any(),
        "event-hour panel keys are unique",
    )
    require(
        not entity.duplicated(["event_id", "entity_id", "period"]).any(),
        "entity-event-period panel keys are unique",
    )
    require(
        set(entity["period"])
        == {"baseline", "anticipatory", "shock", "recovery", "post"},
        "entity panel contains all five periods",
    )
    require(
        entity.groupby(["event_id", "entity_id"]).size().eq(5).all(),
        "every modelled entity has exactly five period rows",
    )
    require(
        "entity_address" not in entity.columns,
        "processed entity panel contains no raw address column",
    )
    require(
        entity["entity_id"].str.fullmatch(r"[0-9a-f]{24}").all(),
        "entity IDs are fixed-length pseudonymous hashes",
    )
    outcome_columns = [
        "volume_usd",
        "transaction_count",
        "transfer_count",
    ]
    require(
        entity[outcome_columns].ge(0).all().all(),
        "entity outcomes are non-negative",
    )


def validate_pilot_outputs() -> None:
    result_dir = ROOT / "results" / "pilot_analysis"
    robustness_dir = ROOT / "results" / "pilot_robustness"
    required = [
        result_dir / "event_period_summary.csv",
        result_dir / "hourly_model_coefficients.csv",
        result_dir / "pu_enrichment.csv",
        robustness_dir / "aggregation_sensitivity.csv",
        robustness_dir / "dynamic_risk_set_placebos.csv",
    ]
    require(
        all(path.exists() and path.stat().st_size > 0 for path in required),
        "required pilot result files exist and are non-empty",
    )


def main() -> None:
    validate_events()
    validate_market_controls()
    validate_panels()
    validate_pilot_outputs()
    print("\nAll current pipeline validations passed.")


if __name__ == "__main__":
    main()
