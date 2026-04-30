import os
import time
from pathlib import Path
from datetime import datetime, timedelta

import polars as pl
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from dune_client.client import DuneClient


# ============================================================
# 1. Path and config
# ============================================================

load_dotenv()

ROOT = Path.cwd().parent if Path.cwd().name == "scripts" else Path.cwd()

RAW_DIR = ROOT / "data" / "raw_2026"
PROCESSED_DIR = ROOT / "data" / "processed_2026"
PLOT_DIR = ROOT / "results"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)

DUNE_API_KEY = "yOBqrXxcE9rjIM9h4UhxvGDHwOSlsyDO"
if not DUNE_API_KEY:
    raise ValueError("DUNE_API_KEY not found. Please put it in your .env file.")


# ============================================================
# 2. Date range
# ============================================================
START_DATE = datetime(2026, 3, 1)
END_DATE = datetime(2026, 4, 20)  


# ============================================================
# 3. Dune helper
# ============================================================

client = DuneClient(DUNE_API_KEY)


def extract_rows(result):
    """
    Handle different dune-client result object formats.
    """
    if hasattr(result, "rows"):
        return result.rows
    if hasattr(result, "result") and hasattr(result.result, "rows"):
        return result.result.rows
    raise ValueError("Cannot find rows in Dune result object.")


def run_dune_sql(query_sql: str):
    """
    Execute raw SQL using dune-client.

    Different dune-client versions use slightly different argument names,
    so this function tries the common options in order.
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
        except Exception as e:
            last_error = e
            print(f"Attempt failed: {e}")

    raise RuntimeError(f"All run_sql attempts failed. Last error: {last_error}")

# ============================================================
# 4. SQL generator
# ============================================================

def build_daily_sql(day_start: datetime, day_end: datetime) -> str:
    start_str = day_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = day_end.strftime("%Y-%m-%d %H:%M:%S")
    start_date = day_start.strftime("%Y-%m-%d")
    end_date = day_end.strftime("%Y-%m-%d")

    query_sql = f"""
    WITH cex_addresses AS (
        SELECT DISTINCT
            address
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category = 'cex users'
    ),

    stablecoin_transfers AS (
        SELECT
            date_trunc('hour', tt.block_time) AS time,
            tt.tx_hash,
            tt.amount_usd
        FROM tokens.transfers tt
        INNER JOIN cex_addresses cex
            ON tt."to" = cex.address
        WHERE tt.blockchain = 'ethereum'
          AND tt.block_time >= CAST('{start_str}' AS TIMESTAMP)
          AND tt.block_time < CAST('{end_str}' AS TIMESTAMP)
          AND tt.block_date >= DATE '{start_date}'
          AND tt.block_date <= DATE '{end_date}'
          AND tt.contract_address IN (
              0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48, -- USDC
              0xdac17f958d2ee523a2206206994597c13d831ec7  -- USDT
          )
          AND tt.amount_usd IS NOT NULL
    ),

    hourly_volume AS (
        SELECT
            time,
            SUM(amount_usd) AS cashout_volume_usd,
            COUNT(*) AS transfer_count
        FROM stablecoin_transfers
        GROUP BY 1
    ),

    hourly_gas AS (
        SELECT
            date_trunc('hour', time) AS time,
            AVG(base_fee_per_gas) / 1e9 AS avg_gas_gwei
        FROM ethereum.blocks
        WHERE time >= CAST('{start_str}' AS TIMESTAMP)
          AND time < CAST('{end_str}' AS TIMESTAMP)
          AND date >= DATE '{start_date}'
          AND date <= DATE '{end_date}'
        GROUP BY 1
    )

    SELECT
        COALESCE(v.time, g.time) AS time,
        COALESCE(v.cashout_volume_usd, 0) AS cashout_volume_usd,
        COALESCE(v.transfer_count, 0) AS transfer_count,
        g.avg_gas_gwei
    FROM hourly_gas g
    LEFT JOIN hourly_volume v
        ON v.time = g.time
    ORDER BY time
    """
    return query_sql


# ============================================================
# 5. Fetch data day by day
# ============================================================

def fetch_daily_batches():
    all_frames = []
    current = START_DATE

    while current < END_DATE:
        next_day = current + timedelta(days=1)
        raw_path = RAW_DIR / f"dune_hourly_{current.date()}.parquet"

        # If this day was already fetched, load local file instead of querying Dune again
        if raw_path.exists():
            print(f"\n📦 Loading existing file for {current.date()}: {raw_path}")
            daily_df = pl.read_parquet(raw_path)
            all_frames.append(daily_df)
            current = next_day
            continue

        print(f"\n🚀 Fetching {current.date()} ...")
        sql = build_daily_sql(current, next_day)

        max_retries = 4
        success = False

        for attempt in range(1, max_retries + 1):
            try:
                rows = run_dune_sql(sql)
                print(f"✅ Rows returned: {len(rows)}")

                if rows:
                    daily_df = pl.DataFrame(rows)
                else:
                    # still save an empty placeholder with correct columns
                    daily_df = pl.DataFrame({
                        "time": [],
                        "cashout_volume_usd": [],
                        "transfer_count": [],
                        "avg_gas_gwei": []
                    })

                daily_df.write_parquet(raw_path)
                all_frames.append(daily_df)
                print(f"💾 Saved raw daily file: {raw_path}")
                success = True
                break

            except Exception as e:
                wait_seconds = 30 * attempt
                print(f"❌ Attempt {attempt}/{max_retries} failed on {current.date()}: {e}")
                print(f"⏳ Waiting {wait_seconds} seconds before retrying...")
                time.sleep(wait_seconds)

        if not success:
            print(f"⚠️ Skipping {current.date()} after {max_retries} failed attempts.")

        # Slow down to avoid Dune API 429 rate limits
        time.sleep(10)
        current = next_day

    if not all_frames:
        raise RuntimeError("No data fetched or loaded. Check SQL, API key, or date range.")

    return pl.concat(all_frames, how="vertical")


# ============================================================
# 6. Clean, define shock, save processed data
# ============================================================

def process_hourly(df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean hourly Dune output, parse timestamps safely, define shock,
    and create log-transformed variables.
    """

    print("\nSchema before processing:")
    print(df.schema)

    # Robust time parsing.
    # Dune may return time as:
    # 1) Python datetime / Polars Datetime
    # 2) string like "2024-08-01 00:00:00.000 UTC"
    # 3) string like "2024-08-01 00:00:00+00:00"
    if df.schema["time"] == pl.Utf8:
        df = df.with_columns(
            pl.col("time")
            .str.replace(" UTC", "+00:00")
            .str.to_datetime(format="%Y-%m-%d %H:%M:%S%.3f%z", strict=False)
            .alias("time")
        )

    # Remove timezone to make CSV/R import simpler
    if isinstance(df.schema["time"], pl.Datetime):
        df = df.with_columns(
            pl.col("time").dt.replace_time_zone(None).alias("time")
        )

    df = (
        df
        .with_columns([
            pl.col("cashout_volume_usd").cast(pl.Float64),
            pl.col("transfer_count").cast(pl.Int64),
            pl.col("avg_gas_gwei").cast(pl.Float64),
        ])
        .sort("time")
        .drop_nulls(subset=["avg_gas_gwei"])
    )

    # Define shock as top 10% gas hours
    gas_threshold = df.select(
        pl.col("avg_gas_gwei").quantile(0.90)
    ).item()

    print(f"\n📌 Gas shock threshold, 90th percentile: {gas_threshold:.2f} Gwei")

    df = df.with_columns([
        (pl.col("avg_gas_gwei") >= gas_threshold).cast(pl.Int8).alias("shock"),
        (pl.col("cashout_volume_usd") + 1).log().alias("log_volume"),
        (pl.col("avg_gas_gwei") + 1).log().alias("log_gas"),
    ])

    print("\nSchema after processing:")
    print(df.schema)

    return df


# ============================================================
# 7. Plot
# ============================================================

def plot_hourly(df: pl.DataFrame):
    pdf = df.to_pandas()

    fig, ax1 = plt.subplots(figsize=(14, 7))

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Average gas fee, Gwei")
    ax1.plot(pdf["time"], pdf["avg_gas_gwei"], linewidth=1.2, label="Average gas fee")
    ax1.grid(True, linestyle="--", alpha=0.4)

    ax2 = ax1.twinx()
    ax2.set_ylabel("Stablecoin transfer volume to cex users, USD")
    ax2.plot(pdf["time"], pdf["cashout_volume_usd"], linewidth=1.2, label="Cash-out proxy volume")

    plt.title("Ethereum stablecoin transfer volume and gas fee over time")
    fig.tight_layout()

    plot_path = PLOT_DIR / "gas_vs_cashout_volume.png"
    plt.savefig(plot_path, dpi=300)
    print(f"🖼️ Plot saved: {plot_path}")
    plt.show()


# ============================================================
# 8. Main
# ============================================================

def main():
    print("Starting Dune batch fetch...")
    print(f"Date range: {START_DATE.date()} to {END_DATE.date()}")

    raw_df = fetch_daily_batches()
    print(f"\n✅ Combined raw rows: {raw_df.height}")

    hourly_df = process_hourly(raw_df)

    parquet_path = PROCESSED_DIR / "dune_stablecoin_cex_hourly.parquet"
    csv_path = PROCESSED_DIR / "dune_stablecoin_cex_hourly.csv"

    hourly_df.write_parquet(parquet_path)
    hourly_df.write_csv(csv_path)

    print(f"💾 Processed parquet saved: {parquet_path}")
    print(f"💾 Processed csv saved: {csv_path}")

    print("\nPreview:")
    print(hourly_df.head(10))

    plot_hourly(hourly_df)


if __name__ == "__main__":
    main()