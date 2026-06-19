"""Build modelling panels from locally extracted event-transfer files.

The main entity risk set requires at least two pre-event transactions by
default. This inclusion rule uses no post-treatment information.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw_entity_events"
EVENTS = ROOT / "results" / "event_catalog" / "eligible_events.csv"
CONTROLS = ROOT / "data" / "processed_market" / "hourly_market_controls.csv"
OUTPUT_DIR = ROOT / "data" / "processed_panel"
SUMMARY = ROOT / "results" / "data_quality" / "panel_build_summary.csv"

PERIODS = {
    "baseline": (-168, -25),
    "anticipatory": (-24, -1),
    "shock": (0, 6),
    "recovery": (7, 24),
    "post": (25, 168),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minimum-pre-transactions",
        type=int,
        default=2,
        help="Pre-treatment activity threshold for the main entity panel.",
    )
    return parser.parse_args()


def entity_hash(address: str) -> str:
    return hashlib.sha256(address.lower().encode("utf-8")).hexdigest()[:24]


def assign_period(relative_hour: pd.Series) -> pd.Series:
    result = pd.Series(pd.NA, index=relative_hour.index, dtype="string")
    for name, (lower, upper) in PERIODS.items():
        result.loc[relative_hour.between(lower, upper)] = name
    return result


def build_event_hour_panel(
    data: pd.DataFrame,
    event: pd.Series,
    controls: pd.DataFrame,
) -> pd.DataFrame:
    grouped = data.groupby("hour", as_index=False).agg(
        volume_usd=("volume_usd", "sum"),
        transfer_count=("transfer_count", "sum"),
        transaction_count=("transaction_count", "sum"),
        active_entities=("entity_address", "nunique"),
    )
    hours = pd.DataFrame(
        {
            "hour": pd.date_range(
                event["window_start"],
                event["window_end"] - pd.Timedelta(hours=1),
                freq="1h",
            )
        }
    )
    panel = hours.merge(grouped, on="hour", how="left")
    outcome_columns = [
        "volume_usd",
        "transfer_count",
        "transaction_count",
        "active_entities",
    ]
    panel[outcome_columns] = panel[outcome_columns].fillna(0)
    panel.insert(0, "event_id", event["event_id"])
    panel["relative_hour"] = (
        (panel["hour"] - event["peak_time"]).dt.total_seconds() / 3600
    ).astype(int)
    panel["is_candidate_shock_hour"] = panel["hour"].between(
        event["event_start"], event["event_end"]
    )
    panel = panel.merge(controls, on="hour", how="left", validate="one_to_one")
    panel["log1p_volume_usd"] = np.log1p(panel["volume_usd"])
    panel["log1p_transaction_count"] = np.log1p(panel["transaction_count"])
    return panel


def build_entity_period_panel(
    data: pd.DataFrame,
    event: pd.Series,
    minimum_pre_transactions: int,
) -> tuple[pd.DataFrame, dict[str, object]]:
    data = data.copy()
    data["relative_hour"] = (
        (data["hour"] - event["peak_time"]).dt.total_seconds() / 3600
    ).astype(int)
    baseline_lower, baseline_upper = PERIODS["baseline"]
    baseline = data.loc[
        data["relative_hour"].between(baseline_lower, baseline_upper)
    ]
    pre_stats = baseline.groupby("entity_address", as_index=False).agg(
        pre_transaction_count=("transaction_count", "sum"),
        pre_transfer_count=("transfer_count", "sum"),
        pre_active_hours=("hour", "nunique"),
        pre_volume_usd=("volume_usd", "sum"),
    )
    eligible = pre_stats.loc[
        pre_stats["pre_transaction_count"].ge(minimum_pre_transactions)
    ].copy()

    filtered = data.loc[data["entity_address"].isin(eligible["entity_address"])].copy()
    filtered["period"] = assign_period(filtered["relative_hour"])
    filtered = filtered.dropna(subset=["period"])

    for column in ["ofac_sanction_label", "tornado_cash_label"]:
        if column not in filtered:
            filtered[column] = 0

    aggregated = filtered.groupby(
        ["entity_address", "period"], as_index=False, observed=True
    ).agg(
        volume_usd=("volume_usd", "sum"),
        transfer_count=("transfer_count", "sum"),
        transaction_count=("transaction_count", "sum"),
        active_hours=("hour", "nunique"),
        ofac_sanction_label=("ofac_sanction_label", "max"),
        tornado_cash_label=("tornado_cash_label", "max"),
    )

    index = pd.MultiIndex.from_product(
        [eligible["entity_address"], list(PERIODS)],
        names=["entity_address", "period"],
    )
    panel = (
        aggregated.set_index(["entity_address", "period"])
        .reindex(index)
        .reset_index()
    )
    zero_columns = [
        "volume_usd",
        "transfer_count",
        "transaction_count",
        "active_hours",
        "ofac_sanction_label",
        "tornado_cash_label",
    ]
    panel[zero_columns] = panel[zero_columns].fillna(0)
    panel = panel.merge(eligible, on="entity_address", how="left")
    panel.insert(0, "event_id", event["event_id"])
    panel["entity_id"] = panel["entity_address"].map(entity_hash)
    panel["period_hours"] = panel["period"].map(
        {name: upper - lower + 1 for name, (lower, upper) in PERIODS.items()}
    )
    panel["volume_usd_per_hour"] = panel["volume_usd"] / panel["period_hours"]
    panel["transactions_per_hour"] = (
        panel["transaction_count"] / panel["period_hours"]
    )
    panel["log1p_volume_rate"] = np.log1p(panel["volume_usd_per_hour"])
    panel["log1p_transaction_rate"] = np.log1p(
        panel["transactions_per_hour"]
    )
    panel["peak_avg_gas_gwei"] = event["peak_avg_gas_gwei"]
    panel["shock_ratio"] = event["shock_ratio"]

    summary = {
        "event_id": event["event_id"],
        "raw_nonzero_rows": len(data),
        "pre_active_entities": pre_stats["entity_address"].nunique(),
        "model_entities": eligible["entity_address"].nunique(),
        "minimum_pre_transactions": minimum_pre_transactions,
        "ofac_entities": panel.loc[
            panel["ofac_sanction_label"].eq(1), "entity_address"
        ].nunique(),
        "tornado_cash_entities": panel.loc[
            panel["tornado_cash_label"].eq(1), "entity_address"
        ].nunique(),
    }

    return panel.drop(columns="entity_address"), summary


def main() -> None:
    args = parse_args()
    event_metadata = pd.read_csv(
        EVENTS,
        parse_dates=[
            "event_start",
            "event_end",
            "peak_time",
            "window_start",
            "window_end",
        ],
    ).set_index("event_id")
    controls = pd.read_csv(CONTROLS, parse_dates=["hour"])

    hourly_frames: list[pd.DataFrame] = []
    entity_frames: list[pd.DataFrame] = []
    summaries: list[dict[str, object]] = []

    files = sorted(RAW_DIR.glob("*_entity_hour_transfers.csv"))
    if not files:
        raise FileNotFoundError(f"No event transfer files found in {RAW_DIR}")

    for path in files:
        event_id = path.name.split("_entity_hour_transfers.csv")[0]
        if event_id not in event_metadata.index:
            print(f"Skipping unknown event file: {path.name}")
            continue

        print(f"Building panels for {event_id}")
        data = pd.read_csv(path, parse_dates=["hour"])
        event = event_metadata.loc[event_id].copy()
        event["event_id"] = event_id
        hourly_frames.append(build_event_hour_panel(data, event, controls))
        entity_panel, summary = build_entity_period_panel(
            data, event, args.minimum_pre_transactions
        )
        entity_frames.append(entity_panel)
        summaries.append(summary)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hourly_output = OUTPUT_DIR / "event_hour_panel.csv.gz"
    entity_output = OUTPUT_DIR / "entity_event_period_panel.csv.gz"
    pd.concat(hourly_frames, ignore_index=True).to_csv(
        hourly_output, index=False, compression="gzip"
    )
    pd.concat(entity_frames, ignore_index=True).to_csv(
        entity_output, index=False, compression="gzip"
    )

    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summaries).to_csv(SUMMARY, index=False)
    print(f"Saved: {hourly_output}")
    print(f"Saved: {entity_output}")
    print(f"Saved: {SUMMARY}")


if __name__ == "__main__":
    main()
