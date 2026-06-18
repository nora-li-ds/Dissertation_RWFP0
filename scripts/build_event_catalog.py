"""Build a de-duplicated fee-shock event catalogue from the six-hour series.

This script deliberately separates long-run event discovery from the later
hourly causal analysis. It does not use stablecoin-transfer outcomes to define
events.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path("data/processed_regime/ethereum_regime_6h.csv")
DEFAULT_OUTPUT_DIR = Path("results/event_catalog")


def project_root() -> Path:
    cwd = Path.cwd()
    return cwd.parent if cwd.name == "scripts" else cwd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--aggregation-hours", type=int, default=6)
    parser.add_argument("--rolling-days", type=int, default=90)
    parser.add_argument("--rolling-quantile", type=float, default=0.99)
    parser.add_argument("--minimum-ratio", type=float, default=1.50)
    parser.add_argument("--minimum-increase-gwei", type=float, default=5.0)
    parser.add_argument("--merge-gap-hours", type=int, default=12)
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument(
        "--minimum-event-separation-days",
        type=int,
        default=14,
        help="Greedy separation around event peaks to avoid contaminated windows.",
    )
    return parser.parse_args()


def resolve_path(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def load_series(path: Path, aggregation_hours: int) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["time"]).sort_values("time")
    required = {"time", "avg_gas_gwei", "median_gas_gwei", "max_gas_gwei"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if frame["time"].duplicated().any():
        raise ValueError("The input contains duplicate timestamps.")

    gaps = frame["time"].diff().dropna()
    expected = pd.Timedelta(hours=aggregation_hours)
    if not gaps.eq(expected).all():
        bad = frame.loc[gaps.ne(expected).reindex(frame.index, fill_value=False)]
        raise ValueError(f"Non-{aggregation_hours}h timestamp gaps detected:\n{bad.head()}")

    return frame


def add_pre_determined_thresholds(
    frame: pd.DataFrame,
    aggregation_hours: int,
    rolling_days: int,
    rolling_quantile: float,
    minimum_ratio: float,
    minimum_increase_gwei: float,
) -> pd.DataFrame:
    periods_per_day = 24 // aggregation_hours
    window = rolling_days * periods_per_day
    minimum_history = max(30 * periods_per_day, window // 2)

    # Shift by one interval so the candidate observation cannot set its own
    # threshold or baseline.
    prior_fee = frame["avg_gas_gwei"].shift(1)
    frame["lagged_threshold_gwei"] = prior_fee.rolling(
        window, min_periods=minimum_history
    ).quantile(rolling_quantile)
    frame["lagged_median_gwei"] = prior_fee.rolling(
        window, min_periods=minimum_history
    ).median()
    frame["shock_ratio"] = (
        frame["avg_gas_gwei"] / frame["lagged_median_gwei"].replace(0, np.nan)
    )
    frame["shock_increase_gwei"] = (
        frame["avg_gas_gwei"] - frame["lagged_median_gwei"]
    )
    frame["relative_candidate"] = (
        frame["lagged_threshold_gwei"].notna()
        & frame["avg_gas_gwei"].ge(frame["lagged_threshold_gwei"])
        & frame["shock_ratio"].ge(minimum_ratio)
        & frame["shock_increase_gwei"].ge(minimum_increase_gwei)
    )
    return frame


def group_candidates(frame: pd.DataFrame, merge_gap_hours: int) -> pd.DataFrame:
    candidates = frame.loc[frame["relative_candidate"]].copy()
    if candidates.empty:
        return pd.DataFrame()

    candidates["candidate_group"] = (
        candidates["time"]
        .diff()
        .gt(pd.Timedelta(hours=merge_gap_hours))
        .cumsum()
    )

    rows: list[dict[str, object]] = []
    for _, group in candidates.groupby("candidate_group", sort=True):
        peak_index = group["avg_gas_gwei"].idxmax()
        peak = group.loc[peak_index]
        rows.append(
            {
                "event_start": group["time"].min(),
                "event_end": group["time"].max(),
                "peak_time": peak["time"],
                "peak_avg_gas_gwei": peak["avg_gas_gwei"],
                "peak_median_gas_gwei": peak["median_gas_gwei"],
                "peak_max_gas_gwei": peak["max_gas_gwei"],
                "lagged_threshold_gwei": peak["lagged_threshold_gwei"],
                "lagged_median_gwei": peak["lagged_median_gwei"],
                "shock_ratio": peak["shock_ratio"],
                "shock_increase_gwei": peak["shock_increase_gwei"],
                "event_interval_count": len(group),
            }
        )

    return pd.DataFrame(rows).sort_values("peak_time").reset_index(drop=True)


def mark_non_overlapping_events(
    events: pd.DataFrame,
    minimum_separation_days: int,
) -> pd.DataFrame:
    if events.empty:
        return events

    events = events.copy()
    events["selected_non_overlapping"] = False
    events["overlap_with_peak_time"] = pd.NaT
    separation = pd.Timedelta(days=minimum_separation_days)
    selected_peaks: list[pd.Timestamp] = []

    # Prefer the strongest shocks, then restore chronological order.
    ranking = events.sort_values(
        ["shock_ratio", "peak_avg_gas_gwei"], ascending=False
    )
    for index, row in ranking.iterrows():
        peak = row["peak_time"]
        conflicting = next(
            (
                selected
                for selected in selected_peaks
                if abs(peak - selected) < separation
            ),
            None,
        )
        if conflicting is None:
            events.loc[index, "selected_non_overlapping"] = True
            selected_peaks.append(peak)
        else:
            events.loc[index, "overlap_with_peak_time"] = conflicting

    return events.sort_values("peak_time").reset_index(drop=True)


def finalise_catalogue(
    events: pd.DataFrame,
    window_days: int,
) -> pd.DataFrame:
    if events.empty:
        return events

    events = events.copy()
    events.insert(0, "event_id", [f"E{i:03d}" for i in range(1, len(events) + 1)])
    events["window_start"] = events["event_start"] - pd.Timedelta(days=window_days)
    events["window_end"] = events["event_end"] + pd.Timedelta(days=window_days)

    # Filled after hourly market-control extraction.
    events["market_stable"] = pd.NA
    events["analysis_eligible"] = pd.NA
    events["exclusion_reason"] = np.where(
        events["selected_non_overlapping"],
        "pending_market_stability_screen",
        "overlapping_event_window",
    )
    return events


def main() -> None:
    args = parse_args()
    root = project_root()
    input_path = resolve_path(root, args.input)
    output_dir = resolve_path(root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = load_series(input_path, args.aggregation_hours)
    frame = add_pre_determined_thresholds(
        frame=frame,
        aggregation_hours=args.aggregation_hours,
        rolling_days=args.rolling_days,
        rolling_quantile=args.rolling_quantile,
        minimum_ratio=args.minimum_ratio,
        minimum_increase_gwei=args.minimum_increase_gwei,
    )
    events = group_candidates(frame, args.merge_gap_hours)
    events = mark_non_overlapping_events(
        events, args.minimum_event_separation_days
    )
    events = finalise_catalogue(events, args.window_days)

    diagnostic_path = output_dir / "screening_series.csv"
    event_path = output_dir / "candidate_events.csv"
    analysis_path = output_dir / "analysis_events.csv"

    frame.to_csv(diagnostic_path, index=False)
    events.to_csv(event_path, index=False)
    events.loc[events["selected_non_overlapping"]].to_csv(
        analysis_path, index=False
    )

    print(f"Input rows: {len(frame):,}")
    print(f"Candidate events: {len(events):,}")
    print(
        "Non-overlapping events pending market screen: "
        f"{events['selected_non_overlapping'].sum():,}"
    )
    print(f"Saved: {event_path}")
    print(f"Saved: {analysis_path}")


if __name__ == "__main__":
    main()
