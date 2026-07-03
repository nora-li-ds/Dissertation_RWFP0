"""Local diagnostics for CEX-bound versus non-CEX negative-control results."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "venv" / "Lib" / "site-packages"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RAW_DIR = ROOT / "data" / "raw_negative_controls"
EVENTS = ROOT / "results" / "event_catalog" / "eligible_events.csv"
OUTPUT = ROOT / "results" / "negative_control_analysis"


def load_panel() -> pd.DataFrame:
    events = pd.read_csv(
        EVENTS,
        parse_dates=["event_start", "event_end", "peak_time", "window_start", "window_end"],
    ).set_index("event_id")
    frames = []
    for path in sorted(RAW_DIR.glob("*_destination_groups.csv")):
        event_id = path.name.removesuffix("_destination_groups.csv")
        frame = pd.read_csv(path, parse_dates=["hour"])
        event = events.loc[event_id]
        frame["relative_hour"] = (
            (frame["hour"] - event["peak_time"]).dt.total_seconds() / 3600
        ).astype(int)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def period_summary(panel: pd.DataFrame) -> pd.DataFrame:
    frame = panel.copy()
    frame["period"] = np.select(
        [
            frame["relative_hour"].between(-168, -25),
            frame["relative_hour"].between(-24, -1),
            frame["relative_hour"].between(0, 6),
            frame["relative_hour"].between(7, 24),
            frame["relative_hour"].between(25, 168),
        ],
        ["baseline", "anticipatory", "shock", "recovery", "post"],
        default="outside",
    )
    frame = frame.loc[frame["period"].ne("outside")]
    summary = (
        frame.groupby(["event_id", "destination_group", "period"], as_index=False)
        .agg(
            hours=("hour", "nunique"),
            mean_transactions=("transaction_count", "mean"),
            mean_volume=("volume_usd", "mean"),
            mean_active_senders=("active_senders", "mean"),
            total_transactions=("transaction_count", "sum"),
            total_volume=("volume_usd", "sum"),
        )
    )
    return summary


def event_shock_ratios(summary: pd.DataFrame) -> pd.DataFrame:
    base = summary.loc[summary["period"].eq("baseline")]
    shock = summary.loc[summary["period"].eq("shock")]
    merged = base.merge(
        shock,
        on=["event_id", "destination_group"],
        suffixes=("_baseline", "_shock"),
        validate="one_to_one",
    )
    merged["transaction_rate_ratio"] = (
        merged["mean_transactions_shock"] / merged["mean_transactions_baseline"]
    )
    merged["volume_rate_ratio"] = (
        merged["mean_volume_shock"] / merged["mean_volume_baseline"]
    )
    wide = merged.pivot(
        index="event_id",
        columns="destination_group",
        values=["transaction_rate_ratio", "volume_rate_ratio"],
    )
    wide.columns = [f"{metric}_{group}" for metric, group in wide.columns]
    wide = wide.reset_index()
    wide["relative_cex_transaction_ratio"] = (
        wide["transaction_rate_ratio_cex_bound"]
        / wide["transaction_rate_ratio_non_cex"]
    )
    wide["relative_cex_volume_ratio"] = (
        wide["volume_rate_ratio_cex_bound"]
        / wide["volume_rate_ratio_non_cex"]
    )
    return wide


def plot_ratios(ratios: pd.DataFrame) -> None:
    plot = ratios.sort_values("relative_cex_transaction_ratio")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(plot["event_id"], plot["relative_cex_transaction_ratio"])
    ax.axhline(1, color="black", linestyle="--", linewidth=1)
    ax.set(
        xlabel="Event",
        ylabel="CEX shock/baseline ratio divided by non-CEX ratio",
        title="Negative-control diagnostic: relative CEX transaction response",
    )
    ax.tick_params(axis="x", rotation=60)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT / "relative_cex_transaction_response.png", dpi=300)
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    summary = period_summary(panel)
    ratios = event_shock_ratios(summary)
    summary.to_csv(OUTPUT / "destination_period_summary.csv", index=False)
    ratios.to_csv(OUTPUT / "event_shock_ratios.csv", index=False)
    plot_ratios(ratios)

    print("Rows:", len(panel))
    print("Events:", panel["event_id"].nunique())
    print("Destination groups:", sorted(panel["destination_group"].unique()))
    print("\nRelative CEX transaction ratios:")
    print(
        ratios[
            [
                "event_id",
                "transaction_rate_ratio_cex_bound",
                "transaction_rate_ratio_non_cex",
                "relative_cex_transaction_ratio",
            ]
        ].sort_values("relative_cex_transaction_ratio").to_string(index=False)
    )
    print("\nSummary:")
    print(ratios["relative_cex_transaction_ratio"].describe().to_string())
    print(f"\nSaved diagnostics to: {OUTPUT}")


if __name__ == "__main__":
    main()
