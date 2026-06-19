"""Estimate CEX-bound versus non-CEX hourly stablecoin fee sensitivity.

Run after `extract_negative_control_outcomes.py`. The interaction between CEX
destination and network fee is the primary aggregate estimand.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "venv" / "Lib" / "site-packages"))

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


RAW_DIR = ROOT / "data" / "raw_negative_controls"
EVENTS = ROOT / "results" / "event_catalog" / "eligible_events.csv"
CONTROLS = ROOT / "data" / "processed_market" / "hourly_market_controls.csv"
OUTPUT = ROOT / "results" / "negative_control_analysis"


def build_panel() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("*_destination_groups.csv"))
    if not files:
        raise FileNotFoundError(
            "No negative-control files found. Run "
            "extract_negative_control_outcomes.py first."
        )
    outcomes = pd.concat(
        [pd.read_csv(path, parse_dates=["hour"]) for path in files],
        ignore_index=True,
    )
    events = pd.read_csv(
        EVENTS,
        parse_dates=["peak_time", "window_start", "window_end"],
    ).set_index("event_id")
    controls = pd.read_csv(CONTROLS, parse_dates=["hour"])

    frames = []
    for event_id, group in outcomes.groupby("event_id"):
        event = events.loc[event_id]
        hours = pd.date_range(
            event["window_start"],
            event["window_end"] - pd.Timedelta(hours=1),
            freq="1h",
        )
        index = pd.MultiIndex.from_product(
            [hours, ["cex_bound", "non_cex"]],
            names=["hour", "destination_group"],
        )
        frame = (
            group.set_index(["hour", "destination_group"])
            .reindex(index)
            .reset_index()
        )
        frame["event_id"] = event_id
        frame["relative_hour"] = (
            (frame["hour"] - event["peak_time"]).dt.total_seconds() / 3600
        ).astype(int)
        frames.append(frame)

    panel = pd.concat(frames, ignore_index=True)
    outcomes_to_zero = [
        "transfer_count",
        "transaction_count",
        "active_senders",
        "volume_usd",
    ]
    panel[outcomes_to_zero] = panel[outcomes_to_zero].fillna(0)
    panel = panel.merge(controls, on="hour", how="left", validate="many_to_one")
    panel["is_cex_bound"] = panel["destination_group"].eq("cex_bound").astype(int)
    panel["shock_window"] = panel["relative_hour"].between(0, 6).astype(int)
    panel["log_fee"] = np.log1p(panel["avg_base_fee_gwei"])
    panel["log_transactions"] = np.log1p(panel["transaction_count"])
    panel["log_volume"] = np.log1p(panel["volume_usd"])
    panel["hour_of_week"] = (
        panel["hour"].dt.dayofweek * 24 + panel["hour"].dt.hour
    )
    return panel


def fit_model(panel: pd.DataFrame, outcome: str):
    formula = (
        f"{outcome} ~ is_cex_bound * log_fee + "
        "is_cex_bound * shock_window + "
        "eth_abs_return_1h + eth_volatility_24h + "
        "stablecoin_depeg_abs + block_utilisation + "
        "C(event_id) + C(hour_of_week)"
    )
    model = smf.ols(formula, data=panel).fit()
    event_count = panel["event_id"].nunique()
    if event_count >= 10:
        model = model.get_robustcov_results(
            cov_type="cluster",
            groups=panel["event_id"],
            use_correction=True,
        )
    else:
        model = smf.ols(formula, data=panel).fit(
            cov_type="HAC", cov_kwds={"maxlags": 24}
        )
    return model


def coefficient_frame(model, model_name: str) -> pd.DataFrame:
    names = model.model.exog_names
    intervals = np.asarray(model.conf_int())
    return pd.DataFrame(
        {
            "model": model_name,
            "term": names,
            "coefficient": np.asarray(model.params),
            "standard_error": np.asarray(model.bse),
            "p_value": np.asarray(model.pvalues),
            "ci_lower": intervals[:, 0],
            "ci_upper": intervals[:, 1],
        }
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    panel = build_panel()
    models = {
        "transactions": fit_model(panel, "log_transactions"),
        "volume": fit_model(panel, "log_volume"),
    }
    coefficients = pd.concat(
        [
            coefficient_frame(model, model_name)
            for model_name, model in models.items()
        ],
        ignore_index=True,
    )
    coefficients.to_csv(OUTPUT / "model_coefficients.csv", index=False)
    for name, model in models.items():
        (OUTPUT / f"{name}_model_summary.txt").write_text(
            model.summary().as_text(), encoding="utf-8"
        )

    descriptive = (
        panel.groupby(
            ["event_id", "destination_group", "shock_window"],
            as_index=False,
        )
        .agg(
            mean_hourly_transactions=("transaction_count", "mean"),
            mean_hourly_volume=("volume_usd", "mean"),
            hours=("hour", "nunique"),
        )
    )
    descriptive.to_csv(OUTPUT / "descriptive_comparison.csv", index=False)
    print(
        coefficients.loc[
            coefficients["term"].isin(
                ["is_cex_bound:log_fee", "is_cex_bound:shock_window"]
            )
        ].to_string(index=False)
    )
    print(f"Saved outputs to: {OUTPUT}")


if __name__ == "__main__":
    main()
