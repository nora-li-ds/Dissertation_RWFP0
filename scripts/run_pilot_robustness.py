"""Pilot robustness checks that do not require additional Dune queries.

These checks validate definitions and code paths. With only three extracted
events, they are not a substitute for final event-clustered inference.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "venv" / "Lib" / "site-packages"))

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


HOURLY = ROOT / "data" / "processed_panel" / "event_hour_panel.csv.gz"
EVENTS = ROOT / "results" / "event_catalog" / "eligible_events.csv"
RAW_DIR = ROOT / "data" / "raw_entity_events"
OUTPUT = ROOT / "results" / "pilot_robustness"


def fit_elasticity(data: pd.DataFrame) -> pd.Series:
    frame = data.copy()
    frame["log_fee"] = np.log1p(frame["avg_base_fee_gwei"])
    frame["log_transactions"] = np.log1p(frame["transaction_count"])
    frame["hour"] = pd.to_datetime(frame["hour"])
    frame["hour_of_week"] = frame["hour"].dt.dayofweek * 24 + frame["hour"].dt.hour
    model = smf.ols(
        "log_transactions ~ log_fee + eth_abs_return_1h + "
        "eth_volatility_24h + stablecoin_depeg_abs + block_utilisation + "
        "C(event_id) + C(hour_of_week)",
        data=frame,
    ).fit(cov_type="HAC", cov_kwds={"maxlags": 24})
    return pd.Series(
        {
            "coefficient": model.params["log_fee"],
            "standard_error": model.bse["log_fee"],
            "p_value": model.pvalues["log_fee"],
            "ci_lower": model.conf_int().loc["log_fee", 0],
            "ci_upper": model.conf_int().loc["log_fee", 1],
            "observations": int(model.nobs),
            "events": frame["event_id"].nunique(),
        }
    )


def aggregation_sensitivity(hourly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for hours in [1, 3, 6]:
        if hours == 1:
            aggregated = hourly.copy()
        else:
            frame = hourly.copy()
            frame["bin"] = np.floor(frame["relative_hour"] / hours).astype(int)
            aggregated = (
                frame.groupby(["event_id", "bin"], as_index=False)
                .agg(
                    hour=("hour", "min"),
                    relative_hour=("relative_hour", "min"),
                    transaction_count=("transaction_count", "sum"),
                    avg_base_fee_gwei=("avg_base_fee_gwei", "mean"),
                    eth_abs_return_1h=("eth_abs_return_1h", "max"),
                    eth_volatility_24h=("eth_volatility_24h", "mean"),
                    stablecoin_depeg_abs=("stablecoin_depeg_abs", "max"),
                    block_utilisation=("block_utilisation", "mean"),
                )
            )
        result = fit_elasticity(aggregated)
        result["aggregation_hours"] = hours
        rows.append(result)
    return pd.DataFrame(rows)


def leave_one_event_out(hourly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for omitted in sorted(hourly["event_id"].unique()):
        result = fit_elasticity(hourly.loc[hourly["event_id"].ne(omitted)])
        result["omitted_event"] = omitted
        rows.append(result)
    return pd.DataFrame(rows)


def placebo_windows(hourly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    real_window = (0, 6)
    placebo_starts = [-144, -120, -96, -72, -48]
    for event_id, group in hourly.groupby("event_id"):
        baseline = group.loc[group["relative_hour"].between(-168, -25)]
        baseline_rate = baseline["transaction_count"].mean()
        windows = [("real", *real_window)] + [
            (f"placebo_{start}", start, start + 6) for start in placebo_starts
        ]
        for name, lower, upper in windows:
            window = group.loc[group["relative_hour"].between(lower, upper)]
            mean_rate = window["transaction_count"].mean()
            rows.append(
                {
                    "event_id": event_id,
                    "window": name,
                    "relative_hour_start": lower,
                    "relative_hour_end": upper,
                    "window_hours": len(window),
                    "mean_hourly_transactions": mean_rate,
                    "baseline_mean_hourly_transactions": baseline_rate,
                    "rate_ratio": mean_rate / baseline_rate,
                    "log_rate_ratio": np.log(
                        (mean_rate + 0.5) / (baseline_rate + 0.5)
                    ),
                }
            )
    return pd.DataFrame(rows)


def activity_threshold_sensitivity(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metadata = events.set_index("event_id")
    for path in sorted(RAW_DIR.glob("*_entity_hour_transfers.csv")):
        event_id = path.name.split("_entity_hour_transfers.csv")[0]
        if event_id not in metadata.index:
            continue
        event = metadata.loc[event_id]
        data = pd.read_csv(path, parse_dates=["hour"])
        data["relative_hour"] = (
            (data["hour"] - event["peak_time"]).dt.total_seconds() / 3600
        ).astype(int)
        baseline = data.loc[data["relative_hour"].between(-168, -25)]
        shock = data.loc[data["relative_hour"].between(0, 6)]
        baseline_counts = baseline.groupby("entity_address")[
            "transaction_count"
        ].sum()
        shock_counts = shock.groupby("entity_address")[
            "transaction_count"
        ].sum()

        for threshold in [1, 2, 3, 5, 10]:
            eligible = baseline_counts.loc[baseline_counts.ge(threshold)].index
            observed = shock_counts.reindex(eligible, fill_value=0)
            expected = baseline_counts.loc[eligible] / 144 * 7
            rows.append(
                {
                    "event_id": event_id,
                    "minimum_baseline_transactions": threshold,
                    "entities": len(eligible),
                    "share_any_shock_transfer": observed.gt(0).mean(),
                    "observed_shock_transactions": observed.sum(),
                    "expected_shock_transactions": expected.sum(),
                    "observed_expected_ratio": (
                        observed.sum() / expected.sum()
                        if expected.sum() > 0
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def dynamically_calibrated_placebos(events: pd.DataFrame) -> pd.DataFrame:
    """Compare real and pseudo shocks with separately defined prior risk sets.

    Each test point uses only the preceding 48 hours to select entities and
    estimate their expected seven-hour activity. This removes the strongest
    mechanical advantage given to the actual pre-event period by the original
    event-specific risk-set extraction.
    """

    rows = []
    metadata = events.set_index("event_id")
    test_peaks = {
        "placebo_-96": -96,
        "placebo_-72": -72,
        "placebo_-48": -48,
        "real": 0,
    }
    for path in sorted(RAW_DIR.glob("*_entity_hour_transfers.csv")):
        event_id = path.name.split("_entity_hour_transfers.csv")[0]
        if event_id not in metadata.index:
            continue
        event = metadata.loc[event_id]
        data = pd.read_csv(path, parse_dates=["hour"])
        data["relative_hour"] = (
            (data["hour"] - event["peak_time"]).dt.total_seconds() / 3600
        ).astype(int)

        for name, peak in test_peaks.items():
            baseline = data.loc[
                data["relative_hour"].between(peak - 48, peak - 1)
            ]
            outcome = data.loc[
                data["relative_hour"].between(peak, peak + 6)
            ]
            baseline_counts = baseline.groupby("entity_address")[
                "transaction_count"
            ].sum()
            outcome_counts = outcome.groupby("entity_address")[
                "transaction_count"
            ].sum()
            for threshold in [1, 2, 3, 5]:
                eligible = baseline_counts.loc[
                    baseline_counts.ge(threshold)
                ].index
                observed = outcome_counts.reindex(eligible, fill_value=0)
                expected = baseline_counts.loc[eligible] / 48 * 7
                rows.append(
                    {
                        "event_id": event_id,
                        "window": name,
                        "minimum_prior_48h_transactions": threshold,
                        "entities": len(eligible),
                        "share_any_next_7h_transfer": observed.gt(0).mean(),
                        "observed_transactions": observed.sum(),
                        "expected_transactions": expected.sum(),
                        "observed_expected_ratio": (
                            observed.sum() / expected.sum()
                            if expected.sum() > 0
                            else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    hourly = pd.read_csv(HOURLY, parse_dates=["hour"])
    events = pd.read_csv(
        EVENTS,
        parse_dates=["event_start", "event_end", "peak_time"],
    )

    aggregation = aggregation_sensitivity(hourly)
    leave_out = leave_one_event_out(hourly)
    placebos = placebo_windows(hourly)
    thresholds = activity_threshold_sensitivity(events)
    dynamic_placebos = dynamically_calibrated_placebos(events)

    aggregation.to_csv(OUTPUT / "aggregation_sensitivity.csv", index=False)
    leave_out.to_csv(OUTPUT / "leave_one_event_out.csv", index=False)
    placebos.to_csv(OUTPUT / "placebo_windows.csv", index=False)
    thresholds.to_csv(
        OUTPUT / "activity_threshold_sensitivity.csv", index=False
    )
    dynamic_placebos.to_csv(
        OUTPUT / "dynamic_risk_set_placebos.csv", index=False
    )
    (OUTPUT / "PILOT_ROBUSTNESS_STATUS.txt").write_text(
        "Definition and pipeline checks only. Final robustness requires all "
        "eligible events and event-level uncertainty.\n",
        encoding="utf-8",
    )

    print("Aggregation sensitivity:")
    print(aggregation.to_string(index=False))
    print("\nLeave-one-event-out:")
    print(leave_out.to_string(index=False))
    print("\nReal and placebo rate ratios:")
    print(
        placebos.pivot(
            index="event_id", columns="window", values="rate_ratio"
        ).to_string()
    )
    print("\nActivity threshold sensitivity:")
    print(thresholds.to_string(index=False))
    print("\nDynamically calibrated real/placebo windows:")
    print(
        dynamic_placebos.pivot_table(
            index=[
                "event_id",
                "minimum_prior_48h_transactions",
            ],
            columns="window",
            values="observed_expected_ratio",
        ).to_string()
    )
    print(f"\nSaved outputs to: {OUTPUT}")


if __name__ == "__main__":
    main()
