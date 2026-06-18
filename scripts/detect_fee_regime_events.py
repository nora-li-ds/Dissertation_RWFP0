
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
from dotenv import load_dotenv
from dune_client.client import DuneClient


# ============================================================
# 1. Paths and configuration
# ============================================================

load_dotenv()

ROOT = Path.cwd().parent if Path.cwd().name == "scripts" else Path.cwd()

RAW_DIR = ROOT / "data" / "raw_regime"
PROCESSED_DIR = ROOT / "data" / "processed_regime"
RESULTS_DIR = ROOT / "results" / "regime_detection"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DUNE_API_KEY = os.getenv("DUNE_API_KEY")

if not DUNE_API_KEY:
    raise ValueError(
        "DUNE_API_KEY was not found. "
        "Create a .env file containing DUNE_API_KEY=your_key_here"
    )

client = DuneClient(DUNE_API_KEY)


# ============================================================
# 2. Research period and aggregation settings
# ============================================================

START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2026, 5, 1)

# Number of days retrieved in each Dune query
QUERY_BATCH_DAYS = 7

# Long-term regime classification interval
AGGREGATION_HOURS = 6

# Event identification settings
ROLLING_WINDOW_DAYS = 90
ROLLING_QUANTILE = 0.99

# Initial absolute threshold.
# This can later be changed after inspecting the full distribution.
ABSOLUTE_GAS_THRESHOLD_GWEI = 30.0

# Minimum number of consecutive 6-hour intervals for an event
MIN_EVENT_INTERVALS = 1

MAX_RETRIES = 4
REQUEST_DELAY_SECONDS = 10


# ============================================================
# 3. Dune helpers
# ============================================================

def extract_rows(result):
    """
    Extract rows from different dune-client response formats.
    """
    if hasattr(result, "rows"):
        return result.rows

    if hasattr(result, "result") and hasattr(result.result, "rows"):
        return result.result.rows

    raise ValueError("Could not find rows in the Dune result object.")


def run_dune_sql(query_sql: str):
    """
    Run raw SQL while supporting several dune-client versions.
    """
    attempts = [
        lambda: client.run_sql(query_sql=query_sql),
        lambda: client.run_sql(sql=query_sql),
        lambda: client.run_sql(query_sql),
    ]

    last_error = None

    for attempt in attempts:
        try:
            result = attempt()
            return extract_rows(result)
        except TypeError as exc:
            last_error = exc
            print(f"Attempt format failed: {exc}")
        except Exception:
            raise

    raise RuntimeError(
        f"All Dune SQL execution attempts failed. Last error: {last_error}"
    )


# ============================================================
# 4. SQL generator
# ============================================================

def build_regime_sql(
    period_start: datetime,
    period_end: datetime,
    aggregation_hours: int = 6,
) -> str:
    """
    Generate SQL for long-term fee-regime classification.

    The query aggregates Ethereum gas fees and stablecoin transfers
    to exchange-related addresses into fixed multi-hour intervals.
    """

    start_timestamp = period_start.strftime("%Y-%m-%d %H:%M:%S")
    end_timestamp = period_end.strftime("%Y-%m-%d %H:%M:%S")

    start_date = period_start.strftime("%Y-%m-%d")
    end_date = period_end.strftime("%Y-%m-%d")

    interval_seconds = aggregation_hours * 60 * 60

    return f"""
    WITH cex_addresses AS (
        SELECT DISTINCT
            address
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category = 'cex users'
    ),

    stablecoin_transfers AS (
        SELECT
            FROM_UNIXTIME(
                FLOOR(TO_UNIXTIME(tt.block_time) / {interval_seconds})
                * {interval_seconds}
            ) AS interval_start,
            tt.tx_hash,
            tt.amount_usd
        FROM tokens.transfers tt
        INNER JOIN cex_addresses cex
            ON tt."to" = cex.address
        WHERE tt.blockchain = 'ethereum'
          AND tt.block_time >= CAST('{start_timestamp}' AS TIMESTAMP)
          AND tt.block_time < CAST('{end_timestamp}' AS TIMESTAMP)
          AND tt.block_date >= DATE '{start_date}'
          AND tt.block_date <= DATE '{end_date}'
          AND tt.contract_address IN (
              0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,
              0xdac17f958d2ee523a2206206994597c13d831ec7
          )
          AND tt.amount_usd IS NOT NULL
    ),

    aggregated_volume AS (
        SELECT
            interval_start,
            SUM(amount_usd) AS stablecoin_volume_usd,
            COUNT(*) AS transfer_count,
            COUNT(DISTINCT tx_hash) AS transaction_count
        FROM stablecoin_transfers
        GROUP BY 1
    ),

    aggregated_gas AS (
        SELECT
            FROM_UNIXTIME(
                FLOOR(TO_UNIXTIME(time) / {interval_seconds})
                * {interval_seconds}
            ) AS interval_start,

            AVG(base_fee_per_gas) / 1e9 AS avg_gas_gwei,
            APPROX_PERCENTILE(base_fee_per_gas / 1e9, 0.50)
                AS median_gas_gwei,
            MAX(base_fee_per_gas) / 1e9 AS max_gas_gwei,
            COUNT(*) AS block_count

        FROM ethereum.blocks
        WHERE time >= CAST('{start_timestamp}' AS TIMESTAMP)
          AND time < CAST('{end_timestamp}' AS TIMESTAMP)
          AND date >= DATE '{start_date}'
          AND date <= DATE '{end_date}'
        GROUP BY 1
    )

    SELECT
        g.interval_start AS time,
        COALESCE(v.stablecoin_volume_usd, 0) AS stablecoin_volume_usd,
        COALESCE(v.transfer_count, 0) AS transfer_count,
        COALESCE(v.transaction_count, 0) AS transaction_count,
        g.avg_gas_gwei,
        g.median_gas_gwei,
        g.max_gas_gwei,
        g.block_count
    FROM aggregated_gas g
    LEFT JOIN aggregated_volume v
        ON g.interval_start = v.interval_start
    ORDER BY 1
    """


# ============================================================
# 5. Fetch long-term data in batches
# ============================================================

def fetch_regime_batches() -> pl.DataFrame:
    """
    Fetch long-term regime data in multi-day batches.

    Existing parquet files are reused, allowing interrupted
    downloads to resume without repeating completed queries.
    """

    frames = []
    current_start = START_DATE

    while current_start < END_DATE:
        current_end = min(
            current_start + timedelta(days=QUERY_BATCH_DAYS),
            END_DATE,
        )

        file_name = (
            f"regime_{current_start:%Y-%m-%d}"
            f"_to_{current_end:%Y-%m-%d}"
            f"_{AGGREGATION_HOURS}h.parquet"
        )

        raw_path = RAW_DIR / file_name

        if raw_path.exists():
            print(f"\nLoading existing batch: {raw_path.name}")

            existing_df = pl.read_parquet(raw_path)

            if existing_df.height > 0:
                frames.append(existing_df)

            current_start = current_end
            continue

        print(
            f"\nFetching {current_start:%Y-%m-%d} "
            f"to {current_end:%Y-%m-%d}..."
        )

        query_sql = build_regime_sql(
            period_start=current_start,
            period_end=current_end,
            aggregation_hours=AGGREGATION_HOURS,
        )

        success = False

        for attempt_number in range(1, MAX_RETRIES + 1):
            try:
                rows = run_dune_sql(query_sql)

                print(f"Rows returned: {len(rows)}")

                if rows:
                    batch_df = pl.DataFrame(rows)
                    batch_df.write_parquet(raw_path)
                    frames.append(batch_df)
                else:
                    print("No rows returned for this batch.")

                success = True
                break

            except Exception as exc:
                wait_seconds = 30 * attempt_number

                print(
                    f"Attempt {attempt_number}/{MAX_RETRIES} failed: {exc}"
                )
                print(f"Waiting {wait_seconds} seconds...")

                time.sleep(wait_seconds)

        if not success:
            print(
                f"Batch failed after {MAX_RETRIES} attempts: "
                f"{current_start:%Y-%m-%d} to {current_end:%Y-%m-%d}"
            )

        time.sleep(REQUEST_DELAY_SECONDS)
        current_start = current_end

    if not frames:
        raise RuntimeError(
            "No data were fetched or loaded. "
            "Check the API key, SQL query, date range and Dune credits."
        )

    return pl.concat(frames, how="vertical_relaxed")


# ============================================================
# 6. Clean long-term dataset
# ============================================================

def process_regime_data(df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and transform the long-term regime dataset.
    """

    print("\nRaw schema:")
    print(df.schema)

    if "time" not in df.columns:
        raise ValueError("Expected a 'time' column in the Dune output.")

    if df.schema["time"] == pl.Utf8:
        df = df.with_columns(
            pl.col("time")
            # Remove trailing UTC text, for example:
            # "2026-04-18 00:00:00.000 UTC"
            .str.replace(r"\s+UTC$", "")

            # Remove numeric timezone suffixes, for example:
            # "2026-04-18 00:00:00+00:00"
            # "2026-04-18 00:00:00.000+0000"
            .str.replace(r"[+-]\d{2}:?\d{2}$", "")

            # Parse the remaining timezone-free timestamp
            .str.to_datetime(strict=False)
            .alias("time")
        )

    if isinstance(df.schema["time"], pl.Datetime):
        df = df.with_columns(
            pl.col("time")
            .dt.replace_time_zone(None)
            .alias("time")
        )

    numeric_columns = [
        "stablecoin_volume_usd",
        "avg_gas_gwei",
        "median_gas_gwei",
        "max_gas_gwei",
    ]

    integer_columns = [
        "transfer_count",
        "transaction_count",
        "block_count",
    ]

    available_numeric = [
        column for column in numeric_columns if column in df.columns
    ]

    available_integer = [
        column for column in integer_columns if column in df.columns
    ]

    df = (
        df
        .with_columns(
            [
                pl.col(column).cast(pl.Float64)
                for column in available_numeric
            ]
            + [
                pl.col(column).cast(pl.Int64)
                for column in available_integer
            ]
        )
        .sort("time")
        .unique(subset=["time"], keep="last")
        .drop_nulls(subset=["avg_gas_gwei"])
        .with_columns([
            (pl.col("stablecoin_volume_usd") + 1)
            .log()
            .alias("log_volume"),

            (pl.col("avg_gas_gwei") + 1)
            .log()
            .alias("log_avg_gas"),

            (pl.col("max_gas_gwei") + 1)
            .log()
            .alias("log_max_gas"),
        ])
    )

    print("\nProcessed schema:")
    print(df.schema)

    return df


# ============================================================
# 7. Classify fee regimes
# ============================================================

def classify_fee_regimes(df: pl.DataFrame) -> pl.DataFrame:
    """
    Assign low, normal and high fee regimes using the full-period
    gas-fee distribution.

    These labels are intended for initial exploration. The final
    dissertation may replace them with change-point detection,
    hidden Markov models, clustering, or another regime method.
    """

    low_threshold = df.select(
        pl.col("avg_gas_gwei").quantile(0.25)
    ).item()

    high_threshold = df.select(
        pl.col("avg_gas_gwei").quantile(0.75)
    ).item()

    print(f"\n25th percentile: {low_threshold:.4f} Gwei")
    print(f"75th percentile: {high_threshold:.4f} Gwei")

    return df.with_columns(
        pl.when(pl.col("avg_gas_gwei") <= low_threshold)
        .then(pl.lit("low"))
        .when(pl.col("avg_gas_gwei") >= high_threshold)
        .then(pl.lit("high"))
        .otherwise(pl.lit("normal"))
        .alias("fee_regime")
    )


# ============================================================
# 8. Detect high-fee stress intervals
# ============================================================

def detect_fee_shocks(df: pl.DataFrame) -> pl.DataFrame:
    """
    Detect candidate fee shocks using both:

    1. a rolling 99th-percentile threshold; and
    2. an absolute gas-fee threshold.

    This avoids labelling a relatively high but still economically
    trivial gas value as a genuine stress event.
    """

    periods_per_day = 24 // AGGREGATION_HOURS
    rolling_window_size = ROLLING_WINDOW_DAYS * periods_per_day

    if rolling_window_size < 2:
        raise ValueError("Rolling window must contain at least two rows.")

    df = df.with_columns(
        pl.col("avg_gas_gwei")
        .rolling_quantile(
            quantile=ROLLING_QUANTILE,
            window_size=rolling_window_size,
            min_samples=max(10, rolling_window_size // 4),
        )
        .alias("rolling_gas_threshold")
    )

    df = df.with_columns([
        (
            pl.col("avg_gas_gwei")
            >= pl.col("rolling_gas_threshold")
        )
        .cast(pl.Int8)
        .alias("relative_shock"),

        (
            pl.col("avg_gas_gwei")
            >= ABSOLUTE_GAS_THRESHOLD_GWEI
        )
        .cast(pl.Int8)
        .alias("absolute_shock"),
    ])

    df = df.with_columns(
        (
            (pl.col("relative_shock") == 1)
            & (pl.col("absolute_shock") == 1)
        )
        .cast(pl.Int8)
        .alias("fee_shock")
    )

    return df


# ============================================================
# 9. Group consecutive shock intervals into events
# ============================================================

def create_event_table(df: pl.DataFrame) -> pl.DataFrame:
    """
    Group consecutive shock intervals into candidate fee events.
    """

    shock_df = (
        df
        .filter(pl.col("fee_shock") == 1)
        .select([
            "time",
            "avg_gas_gwei",
            "max_gas_gwei",
            "stablecoin_volume_usd",
        ])
        .sort("time")
    )

    if shock_df.height == 0:
        print("\nNo fee shocks were detected.")
        return pl.DataFrame({
            "event_id": [],
            "event_start": [],
            "event_end": [],
            "interval_count": [],
            "peak_avg_gas_gwei": [],
            "peak_max_gas_gwei": [],
            "total_stablecoin_volume_usd": [],
        })

    expected_gap_seconds = AGGREGATION_HOURS * 60 * 60

    shock_df = shock_df.with_columns(
        pl.col("time")
        .diff()
        .dt.total_seconds()
        .fill_null(expected_gap_seconds)
        .alias("gap_seconds")
    )

    shock_df = shock_df.with_columns(
        (
            pl.col("gap_seconds") > expected_gap_seconds
        )
        .cast(pl.Int64)
        .cum_sum()
        .alias("event_group")
    )

    event_table = (
        shock_df
        .group_by("event_group")
        .agg([
            pl.col("time").min().alias("event_start"),
            pl.col("time").max().alias("event_end"),
            pl.len().alias("interval_count"),
            pl.col("avg_gas_gwei")
            .max()
            .alias("peak_avg_gas_gwei"),
            pl.col("max_gas_gwei")
            .max()
            .alias("peak_max_gas_gwei"),
            pl.col("stablecoin_volume_usd")
            .sum()
            .alias("total_stablecoin_volume_usd"),
        ])
        .filter(pl.col("interval_count") >= MIN_EVENT_INTERVALS)
        .sort("peak_avg_gas_gwei", descending=True)
        .with_row_index("event_id", offset=1)
        .drop("event_group")
    )

    return event_table


# ============================================================
# 10. Create event windows
# ============================================================

def create_event_windows(
    event_table: pl.DataFrame,
    days_before: int = 7,
    days_after: int = 7,
) -> pl.DataFrame:
    """
    Create recommended hourly extraction windows around each event.
    """

    if event_table.height == 0:
        return event_table

    return event_table.with_columns([
        (
            pl.col("event_start")
            - pl.duration(days=days_before)
        ).alias("window_start"),

        (
            pl.col("event_end")
            + pl.duration(days=days_after)
        ).alias("window_end"),
    ])


# ============================================================
# 11. Plots
# ============================================================

def plot_regime_series(df: pl.DataFrame) -> None:
    """
    Plot gas fees over the full study period.
    """

    pdf = df.to_pandas()

    fig, ax = plt.subplots(figsize=(15, 7))

    ax.plot(
        pdf["time"],
        pdf["avg_gas_gwei"],
        linewidth=0.8,
        label="Average gas fee",
    )

    if "rolling_gas_threshold" in pdf.columns:
        ax.plot(
            pdf["time"],
            pdf["rolling_gas_threshold"],
            linewidth=1.0,
            label="Rolling 99th-percentile threshold",
        )

    shock_rows = pdf[pdf["fee_shock"] == 1]

    if not shock_rows.empty:
        ax.scatter(
            shock_rows["time"],
            shock_rows["avg_gas_gwei"],
            s=18,
            label="Candidate fee shock",
        )

    ax.set_xlabel("Time")
    ax.set_ylabel("Average Ethereum base fee, Gwei")
    ax.set_title("Ethereum Fee Regimes and Candidate Stress Events")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()

    fig.tight_layout()

    output_path = RESULTS_DIR / "ethereum_fee_regimes.png"
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print(f"Plot saved: {output_path}")


def plot_fee_distribution(df: pl.DataFrame) -> None:
    """
    Plot the long-term distribution of average gas fees.
    """

    pdf = df.to_pandas()

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(
        pdf["avg_gas_gwei"].dropna(),
        bins=100,
    )

    ax.set_xlabel("Average Ethereum base fee, Gwei")
    ax.set_ylabel("Number of intervals")
    ax.set_title("Distribution of Ethereum Gas Fees")
    ax.set_yscale("log")
    ax.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()

    output_path = RESULTS_DIR / "gas_fee_distribution.png"
    plt.savefig(output_path, dpi=300)
    plt.close(fig)

    print(f"Plot saved: {output_path}")


# ============================================================
# 12. Save outputs
# ============================================================

def save_outputs(
    regime_df: pl.DataFrame,
    event_table: pl.DataFrame,
    event_windows: pl.DataFrame,
) -> None:
    """
    Save processed data, candidate events and extraction windows.
    """

    regime_parquet = (
        PROCESSED_DIR
        / f"ethereum_regime_{AGGREGATION_HOURS}h.parquet"
    )

    regime_csv = (
        PROCESSED_DIR
        / f"ethereum_regime_{AGGREGATION_HOURS}h.csv"
    )

    event_csv = RESULTS_DIR / "candidate_fee_events.csv"
    event_window_csv = RESULTS_DIR / "candidate_event_windows.csv"

    regime_df.write_parquet(regime_parquet)
    regime_df.write_csv(regime_csv)

    event_table.write_csv(event_csv)
    event_windows.write_csv(event_window_csv)

    print(f"Processed parquet saved: {regime_parquet}")
    print(f"Processed CSV saved: {regime_csv}")
    print(f"Candidate events saved: {event_csv}")
    print(f"Event windows saved: {event_window_csv}")


# ============================================================
# 13. Main
# ============================================================

def main() -> None:
    print("Starting long-term Ethereum regime extraction...")
    print(
        f"Study period: {START_DATE:%Y-%m-%d} "
        f"to {END_DATE:%Y-%m-%d}"
    )
    print(f"Aggregation interval: {AGGREGATION_HOURS} hours")
    print(f"Dune batch length: {QUERY_BATCH_DAYS} days")

    raw_df = fetch_regime_batches()

    print(f"\nCombined raw rows: {raw_df.height}")

    regime_df = process_regime_data(raw_df)
    regime_df = classify_fee_regimes(regime_df)
    regime_df = detect_fee_shocks(regime_df)

    event_table = create_event_table(regime_df)

    event_windows = create_event_windows(
        event_table,
        days_before=7,
        days_after=7,
    )

    save_outputs(
        regime_df=regime_df,
        event_table=event_table,
        event_windows=event_windows,
    )

    plot_regime_series(regime_df)
    plot_fee_distribution(regime_df)

    print("\nTop candidate events:")

    if event_windows.height > 0:
        print(
            event_windows.select([
                "event_id",
                "event_start",
                "event_end",
                "peak_avg_gas_gwei",
                "peak_max_gas_gwei",
                "window_start",
                "window_end",
            ]).head(20)
        )
    else:
        print("No candidate fee events detected.")

    print("\nLong-term regime extraction completed.")


if __name__ == "__main__":
    main()

