"""Apply a pre-specified market-stability screen to fee-shock events."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "results" / "event_catalog" / "analysis_events.csv"
CONTROLS = (
    ROOT / "data" / "processed_market" / "hourly_market_controls.csv"
)
OUTPUT = ROOT / "results" / "event_catalog" / "eligible_events.csv"

RETURN_LIMIT = 0.05
DEPEG_LIMIT = 0.02
VOLATILITY_HISTORY_DAYS = 365
VOLATILITY_QUANTILE = 0.95
SCREEN_HOURS_BEFORE = 6
SCREEN_HOURS_AFTER = 6


def main() -> None:
    events = pd.read_csv(
        EVENTS,
        parse_dates=[
            "event_start",
            "event_end",
            "peak_time",
            "window_start",
            "window_end",
        ],
    )
    controls = pd.read_csv(CONTROLS, parse_dates=["hour"]).sort_values("hour")

    history_hours = VOLATILITY_HISTORY_DAYS * 24
    controls["lagged_volatility_limit"] = (
        controls["eth_volatility_24h"]
        .shift(1)
        .rolling(history_hours, min_periods=90 * 24)
        .quantile(VOLATILITY_QUANTILE)
    )

    summaries: list[dict[str, object]] = []
    for _, event in events.iterrows():
        screen_start = event["event_start"] - pd.Timedelta(
            hours=SCREEN_HOURS_BEFORE
        )
        screen_end = event["event_end"] + pd.Timedelta(
            hours=SCREEN_HOURS_AFTER
        )
        window = controls.loc[
            controls["hour"].between(screen_start, screen_end)
        ].copy()

        missing_controls = (
            window.empty
            or window[
                [
                    "eth_abs_return_1h",
                    "eth_volatility_24h",
                    "lagged_volatility_limit",
                    "stablecoin_depeg_abs",
                ]
            ]
            .isna()
            .any()
            .any()
        )
        max_return = window["eth_abs_return_1h"].max()
        max_depeg = window["stablecoin_depeg_abs"].max()
        volatility_breach = (
            window["eth_volatility_24h"]
            > window["lagged_volatility_limit"]
        ).any()

        reasons: list[str] = []
        if missing_controls:
            reasons.append("missing_market_controls")
        if pd.notna(max_return) and max_return > RETURN_LIMIT:
            reasons.append("eth_return_spike")
        if pd.notna(max_depeg) and max_depeg > DEPEG_LIMIT:
            reasons.append("stablecoin_depeg")
        if volatility_breach:
            reasons.append("elevated_eth_volatility")

        stable = not reasons
        summaries.append(
            {
                "event_id": event["event_id"],
                "market_stable": stable,
                "analysis_eligible": stable,
                "exclusion_reason": "" if stable else ";".join(reasons),
                "screen_max_eth_abs_return_1h": max_return,
                "screen_max_stablecoin_depeg_abs": max_depeg,
                "screen_volatility_breach": bool(volatility_breach),
                "screen_observation_count": len(window),
            }
        )

    summaries_frame = pd.DataFrame(summaries)
    output = events.drop(
        columns=["market_stable", "analysis_eligible", "exclusion_reason"],
        errors="ignore",
    ).merge(summaries_frame, on="event_id", how="left")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT, index=False)

    print(f"Screened events: {len(output):,}")
    print(f"Eligible stable-market events: {output['analysis_eligible'].sum():,}")
    print("Exclusion reasons:")
    print(output["exclusion_reason"].replace("", "eligible").value_counts())
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
