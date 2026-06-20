"""Estimate CEX-bound versus non-CEX hourly stablecoin fee sensitivity.

Run after `extract_negative_control_outcomes.py`. The interaction between CEX
destination and network fee is the primary aggregate estimand.
"""

from __future__ import annotations

import argparse
import json
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bootstrap-reps",
        type=int,
        default=9999,
        help="Wild-cluster score bootstrap replications for the primary term.",
    )
    parser.add_argument("--seed", type=int, default=20260620)
    return parser.parse_args()


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


def wild_cluster_score_test(
    model,
    groups: pd.Series,
    target_term: str,
    repetitions: int,
    seed: int,
) -> dict[str, float | int | str]:
    """Rademacher wild-cluster score test for one coefficient under H0=0.

    The target regressor and outcome are residualised against all nuisance
    regressors. The null cluster scores are sign-flipped at event level. This
    avoids treating hourly rows as independent evidence.
    """

    names = list(model.model.exog_names)
    if target_term not in names:
        raise ValueError(f"Target term not found: {target_term}")

    target_index = names.index(target_term)
    x_all = np.asarray(model.model.exog, dtype=float)
    y = np.asarray(model.model.endog, dtype=float)
    x = x_all[:, target_index]
    z = np.delete(x_all, target_index, axis=1)

    gamma_x = np.linalg.lstsq(z, x, rcond=None)[0]
    gamma_y = np.linalg.lstsq(z, y, rcond=None)[0]
    x_tilde = x - z @ gamma_x
    u_null = y - z @ gamma_y

    denominator = float(x_tilde @ x_tilde)
    beta = float((x_tilde @ y) / denominator)
    u_full = u_null - beta * x_tilde

    group_codes, unique_groups = pd.factorize(groups, sort=True)
    cluster_scores_full = np.bincount(
        group_codes,
        weights=x_tilde * u_full,
        minlength=len(unique_groups),
    )
    cluster_scores_null = np.bincount(
        group_codes,
        weights=x_tilde * u_null,
        minlength=len(unique_groups),
    )
    cluster_count = len(unique_groups)
    observation_count = len(y)
    parameter_count = x_all.shape[1]
    correction = (
        cluster_count
        / (cluster_count - 1)
        * (observation_count - 1)
        / (observation_count - parameter_count)
    )
    variance = (
        correction
        * float(cluster_scores_full @ cluster_scores_full)
        / denominator**2
    )
    standard_error = float(np.sqrt(variance))
    observed_t = beta / standard_error

    rng = np.random.default_rng(seed)
    weights = rng.choice(
        np.array([-1.0, 1.0]),
        size=(repetitions, cluster_count),
    )
    numerator = weights @ cluster_scores_null
    score_scale = np.sqrt(
        correction
        * float(cluster_scores_null @ cluster_scores_null)
    )
    bootstrap_t = numerator / score_scale
    p_value = float(
        (1 + np.count_nonzero(np.abs(bootstrap_t) >= abs(observed_t)))
        / (repetitions + 1)
    )

    return {
        "term": target_term,
        "coefficient": beta,
        "cluster_standard_error": standard_error,
        "observed_t": observed_t,
        "wild_cluster_score_p_value": p_value,
        "bootstrap_repetitions": repetitions,
        "clusters": cluster_count,
        "seed": seed,
        "weight_distribution": "Rademacher",
    }


def main() -> None:
    args = parse_args()
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

    primary_bootstrap = wild_cluster_score_test(
        model=models["transactions"],
        groups=panel["event_id"],
        target_term="is_cex_bound:log_fee",
        repetitions=args.bootstrap_reps,
        seed=args.seed,
    )
    (OUTPUT / "primary_wild_cluster_test.json").write_text(
        json.dumps(primary_bootstrap, indent=2),
        encoding="utf-8",
    )
    print(
        coefficients.loc[
            coefficients["term"].isin(
                ["is_cex_bound:log_fee", "is_cex_bound:shock_window"]
            )
        ].to_string(index=False)
    )
    print("\nPrimary wild-cluster score test:")
    print(json.dumps(primary_bootstrap, indent=2))
    print(f"Saved outputs to: {OUTPUT}")


if __name__ == "__main__":
    main()
