"""Extract hourly Ethereum fees and market controls from Dune.

The extraction is batched and resumable. It intentionally contains no
entity-level wallet data.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw_market_controls"
OUTPUT = ROOT / "data" / "processed_market" / "hourly_market_controls.csv"

START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2026, 5, 1)
BATCH_DAYS = 90
MAX_RETRIES = 4

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT = "0xdac17f958d2ee523a2206206994597c13d831ec7"


try:
    from dune_client.client import DuneClient
    from dotenv import load_dotenv
except ImportError:
    sys.path.insert(0, str(ROOT / "venv" / "Lib" / "site-packages"))
    from dune_client.client import DuneClient
    from dotenv import load_dotenv


def extract_rows(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "rows"):
        return result.rows
    if hasattr(result, "result") and hasattr(result.result, "rows"):
        return result.result.rows
    raise ValueError("Could not locate rows in the Dune response.")


def run_query(client: DuneClient, sql: str) -> list[dict[str, Any]]:
    attempts = [
        lambda: client.run_sql(query_sql=sql),
        lambda: client.run_sql(sql=sql),
        lambda: client.run_sql(sql),
    ]
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            return extract_rows(attempt())
        except TypeError as exc:
            last_error = exc
            continue
        except Exception:
            raise
    raise RuntimeError(f"Dune query failed: {last_error}")


def build_sql(start: datetime, end: datetime) -> str:
    start_ts = start.strftime("%Y-%m-%d %H:%M:%S")
    end_ts = end.strftime("%Y-%m-%d %H:%M:%S")
    start_date = start.strftime("%Y-%m-%d")
    end_date = (end - timedelta(seconds=1)).strftime("%Y-%m-%d")

    return f"""
    WITH hourly_blocks AS (
        SELECT
            DATE_TRUNC('hour', time) AS hour,
            AVG(base_fee_per_gas) / 1e9 AS avg_base_fee_gwei,
            APPROX_PERCENTILE(base_fee_per_gas / 1e9, 0.50)
                AS median_base_fee_gwei,
            MAX(base_fee_per_gas) / 1e9 AS max_base_fee_gwei,
            SUM(gas_used) / NULLIF(SUM(gas_limit), 0) AS block_utilisation,
            COUNT(*) AS block_count
        FROM ethereum.blocks
        WHERE time >= TIMESTAMP '{start_ts}'
          AND time < TIMESTAMP '{end_ts}'
          AND date >= DATE '{start_date}'
          AND date <= DATE '{end_date}'
        GROUP BY 1
    ),
    hourly_prices AS (
        SELECT
            DATE_TRUNC('hour', timestamp) AS hour,
            APPROX_PERCENTILE(
                CASE WHEN contract_address = {WETH} THEN price END, 0.50
            ) AS eth_price_usd,
            APPROX_PERCENTILE(
                CASE WHEN contract_address = {USDC} THEN price END, 0.50
            ) AS usdc_price_usd,
            APPROX_PERCENTILE(
                CASE WHEN contract_address = {USDT} THEN price END, 0.50
            ) AS usdt_price_usd
        FROM prices.hour
        WHERE blockchain = 'ethereum'
          AND timestamp >= TIMESTAMP '{start_ts}'
          AND timestamp < TIMESTAMP '{end_ts}'
          AND contract_address IN ({WETH}, {USDC}, {USDT})
        GROUP BY 1
    )
    SELECT
        hour,
        b.avg_base_fee_gwei,
        b.median_base_fee_gwei,
        b.max_base_fee_gwei,
        b.block_utilisation,
        b.block_count,
        p.eth_price_usd,
        p.usdc_price_usd,
        p.usdt_price_usd
    FROM hourly_blocks b
    LEFT JOIN hourly_prices p USING (hour)
    ORDER BY hour
    """


def fetch_batches(client: DuneClient) -> pd.DataFrame:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    current = START_DATE

    while current < END_DATE:
        end = min(current + timedelta(days=BATCH_DAYS), END_DATE)
        path = RAW_DIR / f"market_{current:%Y-%m-%d}_{end:%Y-%m-%d}.csv"

        if path.exists():
            print(f"Loading existing batch: {path.name}")
            frames.append(pd.read_csv(path, parse_dates=["hour"]))
            current = end
            continue

        print(f"Fetching market controls: {current:%Y-%m-%d} to {end:%Y-%m-%d}")
        sql = build_sql(current, end)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                rows = run_query(client, sql)
                batch = pd.DataFrame(rows)
                if batch.empty:
                    raise RuntimeError("Dune returned no rows.")
                batch["hour"] = pd.to_datetime(batch["hour"], utc=True).dt.tz_localize(None)
                batch.to_csv(path, index=False)
                frames.append(batch)
                break
            except Exception as exc:
                if attempt == MAX_RETRIES:
                    raise
                wait = 20 * attempt
                print(f"Attempt {attempt} failed: {exc}; retrying in {wait}s")
                time.sleep(wait)

        current = end

    return pd.concat(frames, ignore_index=True)


def process(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values("hour").drop_duplicates("hour", keep="last")
    frame["hour"] = pd.to_datetime(frame["hour"])

    expected = pd.date_range(
        START_DATE, END_DATE - timedelta(hours=1), freq="1h"
    )
    frame = (
        frame.set_index("hour")
        .reindex(expected)
        .rename_axis("hour")
        .reset_index()
    )

    price_columns = ["eth_price_usd", "usdc_price_usd", "usdt_price_usd"]
    frame[price_columns] = frame[price_columns].ffill(limit=3)
    frame["eth_log_return_1h"] = np.log(
        frame["eth_price_usd"].where(frame["eth_price_usd"] > 0)
    ).diff()
    frame["eth_abs_return_1h"] = frame["eth_log_return_1h"].abs()
    frame["eth_volatility_24h"] = (
        frame["eth_log_return_1h"].shift(1).rolling(24, min_periods=18).std()
    )
    frame["usdc_depeg_abs"] = (frame["usdc_price_usd"] - 1).abs()
    frame["usdt_depeg_abs"] = (frame["usdt_price_usd"] - 1).abs()
    frame["stablecoin_depeg_abs"] = frame[
        ["usdc_depeg_abs", "usdt_depeg_abs"]
    ].max(axis=1)
    return frame


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("DUNE_API_KEY"):
        raise ValueError("DUNE_API_KEY is missing from the project .env file.")

    client = DuneClient(os.environ["DUNE_API_KEY"])
    frame = process(fetch_batches(client))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False)
    print(f"Rows: {len(frame):,}")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
