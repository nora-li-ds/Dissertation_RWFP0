"""Run exploratory models on the currently available event extractions.

Outputs are explicitly labelled pilot results until all eligible events have
been extracted. The same script can be rerun without modification afterwards.
"""

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
import statsmodels.formula.api as smf
from scipy.stats import fisher_exact


HOURLY = ROOT / "data" / "processed_panel" / "event_hour_panel.csv.gz"
ENTITY = (
    ROOT / "data" / "processed_panel" / "entity_event_period_panel.csv.gz"
)
OUTPUT = ROOT / "results" / "pilot_analysis"


def period_from_hour(relative_hour: pd.Series) -> pd.Series:
    conditions = [
        relative_hour.between(-168, -25),
        relative_hour.between(-24, -1),
        relative_hour.between(0, 6),
        relative_hour.between(7, 24),
        relative_hour.between(25, 168),
    ]
    names = ["baseline", "anticipatory", "shock", "recovery", "post"]
    return pd.Series(
        np.select(conditions, names, default="outside"),
        index=relative_hour.index,
    )


def build_event_period_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    hourly = hourly.copy()
    hourly["period"] = period_from_hour(hourly["relative_hour"])
    hourly = hourly.loc[hourly["period"].ne("outside")]
    return (
        hourly.groupby(["event_id", "period"], as_index=False)
        .agg(
            hours=("hour", "nunique"),
            total_volume_usd=("volume_usd", "sum"),
            total_transactions=("transaction_count", "sum"),
            mean_hourly_volume_usd=("volume_usd", "mean"),
            mean_hourly_transactions=("transaction_count", "mean"),
            mean_active_entities=("active_entities", "mean"),
            mean_base_fee_gwei=("avg_base_fee_gwei", "mean"),
            max_base_fee_gwei=("max_base_fee_gwei", "max"),
        )
    )


def build_entity_responses(entity: pd.DataFrame) -> pd.DataFrame:
    value_columns = [
        "log1p_volume_rate",
        "log1p_transaction_rate",
        "volume_usd_per_hour",
        "transactions_per_hour",
        "transaction_count",
    ]
    pivot = entity.pivot_table(
        index=["event_id", "entity_id"],
        columns="period",
        values=value_columns,
        aggfunc="first",
    )
    pivot.columns = [f"{metric}_{period}" for metric, period in pivot.columns]
    pivot = pivot.reset_index()

    metadata = entity.groupby(["event_id", "entity_id"], as_index=False).agg(
        pre_transaction_count=("pre_transaction_count", "first"),
        pre_active_hours=("pre_active_hours", "first"),
        pre_volume_usd=("pre_volume_usd", "first"),
        ofac_sanction_label=("ofac_sanction_label", "max"),
        tornado_cash_label=("tornado_cash_label", "max"),
        peak_avg_gas_gwei=("peak_avg_gas_gwei", "first"),
        shock_ratio=("shock_ratio", "first"),
    )
    response = pivot.merge(
        metadata, on=["event_id", "entity_id"], how="left", validate="one_to_one"
    )
    response["delta_log_volume_shock"] = (
        response["log1p_volume_rate_shock"]
        - response["log1p_volume_rate_baseline"]
    )
    response["delta_log_transactions_shock"] = (
        response["log1p_transaction_rate_shock"]
        - response["log1p_transaction_rate_baseline"]
    )
    response["delta_log_volume_recovery"] = (
        response["log1p_volume_rate_recovery"]
        - response["log1p_volume_rate_baseline"]
    )
    response["expected_shock_transactions"] = (
        response["pre_transaction_count"] / 144 * 7
    )
    response["rigidity_residual"] = (
        response["transaction_count_shock"]
        - response["expected_shock_transactions"]
    ) / np.sqrt(response["expected_shock_transactions"] + 1)
    response["rigidity_percentile"] = response.groupby("event_id")[
        "rigidity_residual"
    ].rank(pct=True, method="average")
    return response


def fit_hourly_model(hourly: pd.DataFrame, outcome: str):
    data = hourly.copy()
    data["hour"] = pd.to_datetime(data["hour"])
    data["hour_of_week"] = data["hour"].dt.dayofweek * 24 + data["hour"].dt.hour
    data["log_avg_base_fee"] = np.log1p(data["avg_base_fee_gwei"])
    data["shock_window"] = data["relative_hour"].between(0, 6).astype(int)
    data["recovery_window"] = data["relative_hour"].between(7, 24).astype(int)
    data = data.loc[data["relative_hour"].between(-168, 168)].copy()

    formula = (
        f"{outcome} ~ log_avg_base_fee + shock_window + "
        "recovery_window + eth_abs_return_1h + eth_volatility_24h + "
        "stablecoin_depeg_abs + block_utilisation + "
        "C(event_id) + C(hour_of_week)"
    )
    return smf.ols(formula, data=data).fit(
        cov_type="HAC", cov_kwds={"maxlags": 24}
    )


def pu_enrichment(response: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in ["ofac_sanction_label", "tornado_cash_label"]:
        for event_id, group in response.groupby("event_id"):
            group = group.copy()
            positives = group[label].eq(1)
            top_count = max(1, int(np.ceil(len(group) * 0.10)))
            top = pd.Series(False, index=group.index)
            top.loc[
                group.sort_values(
                    ["rigidity_residual", "pre_transaction_count"],
                    ascending=False,
                ).head(top_count).index
            ] = True
            positive_count = int(positives.sum())
            top_positive_count = int((positives & top).sum())
            if positive_count == 0:
                odds_ratio = np.nan
                p_value = np.nan
                lift = np.nan
            else:
                table = [
                    [top_positive_count, int(top.sum() - top_positive_count)],
                    [
                        int(positive_count - top_positive_count),
                        int((~top).sum() - (positive_count - top_positive_count)),
                    ],
                ]
                odds_ratio, p_value = fisher_exact(
                    table, alternative="greater"
                )
                overall_rate = positive_count / len(group)
                top_rate = top_positive_count / max(int(top.sum()), 1)
                lift = top_rate / overall_rate if overall_rate else np.nan

            rows.append(
                {
                    "event_id": event_id,
                    "label": label,
                    "entities": len(group),
                    "positive_entities": positive_count,
                    "top_decile_entities": int(top.sum()),
                    "top_decile_positives": top_positive_count,
                    "top_decile_lift": lift,
                    "fisher_odds_ratio": odds_ratio,
                    "fisher_one_sided_p": p_value,
                }
            )
    return pd.DataFrame(rows)


def plot_event_study(hourly: pd.DataFrame) -> None:
    plot = hourly.loc[hourly["relative_hour"].between(-72, 72)].copy()
    baseline_volume = (
        hourly.loc[hourly["relative_hour"].between(-168, -25)]
        .groupby("event_id")["volume_usd"]
        .median()
        .rename("baseline_volume")
    )
    baseline_transactions = (
        hourly.loc[hourly["relative_hour"].between(-168, -25)]
        .groupby("event_id")["transaction_count"]
        .median()
        .rename("baseline_transactions")
    )
    plot = plot.merge(baseline_volume, on="event_id", how="left")
    plot = plot.merge(baseline_transactions, on="event_id", how="left")
    plot["normalised_volume"] = plot["volume_usd"] / plot["baseline_volume"]
    plot["normalised_transactions"] = (
        plot["transaction_count"] / plot["baseline_transactions"]
    )
    plot["smoothed_volume"] = plot.groupby("event_id")[
        "normalised_volume"
    ].transform(lambda series: series.rolling(6, center=True, min_periods=1).mean())
    plot["smoothed_transactions"] = plot.groupby("event_id")[
        "normalised_transactions"
    ].transform(lambda series: series.rolling(6, center=True, min_periods=1).mean())

    fig, axes = plt.subplots(2, 1, figsize=(11, 9), sharex=True)
    for event_id, group in plot.groupby("event_id"):
        axes[0].plot(
            group["relative_hour"],
            group["smoothed_transactions"],
            label=event_id,
            linewidth=1.5,
        )
        axes[1].plot(
            group["relative_hour"],
            group["smoothed_volume"],
            label=event_id,
            linewidth=1.5,
        )
    for ax in axes:
        ax.axvline(0, color="black", linestyle="--", linewidth=1)
        ax.axhline(1, color="grey", linestyle=":", linewidth=1)
        ax.grid(alpha=0.25)
    axes[0].set(
        ylabel="Transactions / pre-event median",
        title="Pilot event study: pre-active entities",
    )
    axes[1].set(
        xlabel="Hours relative to fee-shock peak",
        ylabel="CEX-bound volume / pre-event median",
    )
    axes[0].legend(ncol=3)
    fig.tight_layout()
    fig.savefig(OUTPUT / "pilot_event_study_volume.png", dpi=300)
    plt.close(fig)


def plot_entity_responses(response: pd.DataFrame) -> None:
    plot = response.copy()
    plot["pre_activity"] = pd.cut(
        plot["pre_transaction_count"],
        bins=[1, 2, 4, 9, np.inf],
        labels=["2", "3-4", "5-9", "10+"],
        include_lowest=True,
    )
    plot["shock_any"] = plot["transaction_count_shock"].gt(0)
    summary = (
        plot.groupby(["event_id", "pre_activity"], observed=True)["shock_any"]
        .mean()
        .unstack("event_id")
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    summary.plot(kind="bar", ax=ax)
    ax.set(
        xlabel="Baseline transactions in hours -168 to -25",
        ylabel="Share transferring during the 7-hour shock period",
        title="Pilot rigidity by pre-event activity",
    )
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Event")
    fig.tight_layout()
    fig.savefig(OUTPUT / "pilot_entity_response_distribution.png", dpi=300)
    plt.close(fig)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    hourly = pd.read_csv(HOURLY, parse_dates=["hour"])
    entity = pd.read_csv(ENTITY)

    event_summary = build_event_period_summary(hourly)
    response = build_entity_responses(entity)
    response_summary = (
        response.groupby("event_id", as_index=False)
        .agg(
            entities=("entity_id", "nunique"),
            median_delta_log_volume=("delta_log_volume_shock", "median"),
            mean_delta_log_volume=("delta_log_volume_shock", "mean"),
            median_delta_log_transactions=(
                "delta_log_transactions_shock",
                "median",
            ),
            mean_delta_log_transactions=(
                "delta_log_transactions_shock",
                "mean",
            ),
            share_non_decreasing_transactions=(
                "delta_log_transactions_shock",
                lambda series: float(series.ge(0).mean()),
            ),
        )
    )
    models = {
        "transactions": fit_hourly_model(
            hourly, "log1p_transaction_count"
        ),
        "volume": fit_hourly_model(hourly, "log1p_volume_usd"),
    }
    coefficient_tables = []
    for model_name, model in models.items():
        coefficient_tables.append(
            pd.DataFrame(
                {
                    "model": model_name,
                    "term": model.params.index,
                    "coefficient": model.params.values,
                    "standard_error": model.bse.values,
                    "p_value": model.pvalues.values,
                    "ci_lower": model.conf_int()[0].values,
                    "ci_upper": model.conf_int()[1].values,
                }
            )
        )
        (OUTPUT / f"hourly_{model_name}_model_summary.txt").write_text(
            model.summary().as_text(), encoding="utf-8"
        )
    coefficient_table = pd.concat(coefficient_tables, ignore_index=True)
    enrichment = pu_enrichment(response)

    event_summary.to_csv(OUTPUT / "event_period_summary.csv", index=False)
    response_summary.to_csv(
        OUTPUT / "entity_response_summary.csv", index=False
    )
    response.to_csv(
        OUTPUT / "entity_event_responses.csv.gz",
        index=False,
        compression="gzip",
    )
    coefficient_table.to_csv(
        OUTPUT / "hourly_model_coefficients.csv", index=False
    )
    enrichment.to_csv(OUTPUT / "pu_enrichment.csv", index=False)
    (OUTPUT / "PILOT_STATUS.txt").write_text(
        "Exploratory pilot only. Inference must be rerun after extraction of "
        "all eligible stable-market events. HAC uncertainty with three events "
        "is not the final dissertation inference.\n",
        encoding="utf-8",
    )

    plot_event_study(hourly)
    plot_entity_responses(response)

    print(event_summary.to_string(index=False))
    print("\nEntity response summary:")
    print(response_summary.to_string(index=False))
    print("\nPU enrichment:")
    print(enrichment.to_string(index=False))
    print(f"\nSaved outputs to: {OUTPUT}")


if __name__ == "__main__":
    main()
