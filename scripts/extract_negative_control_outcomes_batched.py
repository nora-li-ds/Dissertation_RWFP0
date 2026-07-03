"""Credit-efficient extraction of CEX/non-CEX hourly stablecoin outcomes.

This batches multiple event windows into one Dune query and writes one local
CSV per event, matching the format expected by run_negative_control_analysis.py.
No raw addresses are returned.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVENT_FILE = ROOT / "results" / "event_catalog" / "eligible_events.csv"
OUTPUT_DIR = ROOT / "data" / "raw_negative_controls"
MAX_RETRIES = 3

USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT = "0xdac17f958d2ee523a2206206994597c13d831ec7"


try:
    from dune_client.client import DuneClient
    from dotenv import load_dotenv
except ImportError:
    sys.path.insert(0, str(ROOT / "venv" / "Lib" / "site-packages"))
    from dune_client.client import DuneClient
    from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--event-ids", nargs="+")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


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


def is_http_402(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return response is not None and getattr(response, "status_code", None) == 402


def load_events(force: bool, event_ids: list[str] | None) -> pd.DataFrame:
    events = pd.read_csv(
        EVENT_FILE,
        parse_dates=["window_start", "window_end", "peak_time"],
    )
    events = events.loc[events["analysis_eligible"].astype(str).eq("True")].copy()
    if event_ids:
        requested = set(event_ids)
        unknown = requested.difference(events["event_id"])
        if unknown:
            raise ValueError(f"Unknown or ineligible event IDs: {sorted(unknown)}")
        events = events.loc[events["event_id"].isin(requested)]

    if not force:
        existing = {
            path.name.removesuffix("_destination_groups.csv")
            for path in OUTPUT_DIR.glob("*_destination_groups.csv")
        }
        events = events.loc[~events["event_id"].isin(existing)]
    return events.sort_values("peak_time")


def build_values(batch: pd.DataFrame) -> str:
    rows = []
    for _, row in batch.iterrows():
        rows.append(
            "('{event_id}', TIMESTAMP '{start}', TIMESTAMP '{end}')".format(
                event_id=row["event_id"],
                start=row["window_start"].strftime("%Y-%m-%d %H:%M:%S"),
                end=row["window_end"].strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    return ",\n        ".join(rows)


def build_sql(batch: pd.DataFrame) -> str:
    values = build_values(batch)
    min_start = batch["window_start"].min().strftime("%Y-%m-%d %H:%M:%S")
    max_end = batch["window_end"].max().strftime("%Y-%m-%d %H:%M:%S")
    min_date = batch["window_start"].min().strftime("%Y-%m-%d")
    max_date = batch["window_end"].max().strftime("%Y-%m-%d")

    return f"""
    WITH event_windows(event_id, window_start, window_end) AS (
        VALUES
        {values}
    ),
    cex_addresses AS (
        SELECT DISTINCT address
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category = 'cex users'
    ),
    transfers AS (
        SELECT
            ew.event_id,
            DATE_TRUNC('hour', tt.block_time) AS hour,
            tt.tx_hash,
            tt."from" AS sender,
            tt.amount_usd,
            CASE WHEN cex.address IS NULL
                THEN 'non_cex'
                ELSE 'cex_bound'
            END AS destination_group
        FROM event_windows ew
        INNER JOIN tokens.transfers tt
            ON tt.block_time >= ew.window_start
           AND tt.block_time < ew.window_end
        LEFT JOIN cex_addresses cex
            ON tt."to" = cex.address
        WHERE tt.blockchain = 'ethereum'
          AND tt.block_time >= TIMESTAMP '{min_start}'
          AND tt.block_time < TIMESTAMP '{max_end}'
          AND tt.block_date >= DATE '{min_date}'
          AND tt.block_date <= DATE '{max_date}'
          AND tt.contract_address IN ({USDC}, {USDT})
          AND tt.amount_usd IS NOT NULL
          AND tt."from" IS NOT NULL
          AND tt."to" IS NOT NULL
          AND tt."from" <> tt."to"
    )
    SELECT
        event_id,
        hour,
        destination_group,
        COUNT(*) AS transfer_count,
        COUNT(DISTINCT tx_hash) AS transaction_count,
        COUNT(DISTINCT sender) AS active_senders,
        SUM(amount_usd) AS volume_usd
    FROM transfers
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
    """


def write_event_files(frame: pd.DataFrame, batch: pd.DataFrame) -> None:
    if not frame.empty:
        frame["hour"] = pd.to_datetime(frame["hour"], utc=True).dt.tz_localize(None)
    for event_id in batch["event_id"]:
        output = OUTPUT_DIR / f"{event_id}_destination_groups.csv"
        event_frame = frame.loc[frame["event_id"].eq(event_id)].copy()
        event_frame.to_csv(output, index=False)
        print(f"{event_id}: rows={len(event_frame):,}; saved={output.name}")


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(args.force, args.event_ids)
    if events.empty:
        print("No negative-control events need extraction.")
        return

    load_dotenv(ROOT / ".env")
    if not os.getenv("DUNE_API_KEY"):
        raise ValueError("DUNE_API_KEY is missing from the project .env file.")
    client = DuneClient(os.environ["DUNE_API_KEY"])

    batches = [
        events.iloc[start : start + args.batch_size]
        for start in range(0, len(events), args.batch_size)
    ]
    for index, batch in enumerate(batches, start=1):
        ids = ", ".join(batch["event_id"])
        print(f"Fetching batch {index}/{len(batches)}: {ids}")
        sql = build_sql(batch)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                rows = run_query(client, sql)
                write_event_files(pd.DataFrame(rows), batch)
                break
            except Exception as exc:
                if is_http_402(exc):
                    raise RuntimeError(
                        "Dune returned HTTP 402 (credits/payment required)."
                    ) from exc
                if attempt == MAX_RETRIES:
                    raise
                wait = 45 * attempt
                print(f"Attempt {attempt} failed: {exc}; retrying in {wait}s")
                time.sleep(wait)


if __name__ == "__main__":
    main()
