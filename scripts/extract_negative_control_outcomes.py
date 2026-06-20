"""Extract hourly CEX-bound and non-CEX stablecoin outcomes by event.

The non-CEX series is a negative-control outcome for general Ethereum activity.
It is required before interpreting a CEX-bound decline as cash-out-specific.
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
MAX_RETRIES = 4

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
    parser.add_argument("--event-ids", nargs="+")
    parser.add_argument("--all-eligible", action="store_true")
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


def build_sql(event: pd.Series) -> str:
    start = event["window_start"].strftime("%Y-%m-%d %H:%M:%S")
    end = event["window_end"].strftime("%Y-%m-%d %H:%M:%S")
    start_date = event["window_start"].strftime("%Y-%m-%d")
    end_date = event["window_end"].strftime("%Y-%m-%d")
    event_id = event["event_id"]

    return f"""
    WITH cex_addresses AS (
        SELECT DISTINCT address
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category = 'cex users'
    ),
    transfers AS (
        SELECT
            DATE_TRUNC('hour', tt.block_time) AS hour,
            tt.tx_hash,
            tt."from" AS sender,
            tt.amount_usd,
            CASE WHEN cex.address IS NULL
                THEN 'non_cex'
                ELSE 'cex_bound'
            END AS destination_group
        FROM tokens.transfers tt
        LEFT JOIN cex_addresses cex
            ON tt."to" = cex.address
        WHERE tt.blockchain = 'ethereum'
          AND tt.block_time >= TIMESTAMP '{start}'
          AND tt.block_time < TIMESTAMP '{end}'
          AND tt.block_date >= DATE '{start_date}'
          AND tt.block_date <= DATE '{end_date}'
          AND tt.contract_address IN ({USDC}, {USDT})
          AND tt.amount_usd IS NOT NULL
          AND tt."from" IS NOT NULL
          AND tt."to" IS NOT NULL
          AND tt."from" <> tt."to"
    )
    SELECT
        '{event_id}' AS event_id,
        hour,
        destination_group,
        COUNT(*) AS transfer_count,
        COUNT(DISTINCT tx_hash) AS transaction_count,
        COUNT(DISTINCT sender) AS active_senders,
        SUM(amount_usd) AS volume_usd
    FROM transfers
    GROUP BY 1, 2, 3
    ORDER BY 2, 3
    """


def main() -> None:
    args = parse_args()
    if not args.all_eligible and not args.event_ids:
        raise ValueError("Pass --event-ids or --all-eligible.")

    events = pd.read_csv(
        EVENT_FILE,
        parse_dates=["window_start", "window_end", "peak_time"],
    )
    events = events.loc[events["analysis_eligible"].astype(str).eq("True")]
    if args.event_ids:
        requested = set(args.event_ids)
        unknown = requested.difference(events["event_id"])
        if unknown:
            raise ValueError(f"Unknown or ineligible event IDs: {sorted(unknown)}")
        events = events.loc[events["event_id"].isin(requested)]

    load_dotenv(ROOT / ".env")
    if not os.getenv("DUNE_API_KEY"):
        raise ValueError("DUNE_API_KEY is missing from the project .env file.")
    client = DuneClient(os.environ["DUNE_API_KEY"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for _, event in events.sort_values("peak_time").iterrows():
        output = OUTPUT_DIR / f"{event['event_id']}_destination_groups.csv"
        if output.exists() and not args.force:
            print(f"Loading existing extraction: {output.name}")
            continue

        print(f"Fetching negative controls for {event['event_id']}")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                frame = pd.DataFrame(run_query(client, build_sql(event)))
                if not frame.empty:
                    frame["hour"] = (
                        pd.to_datetime(frame["hour"], utc=True)
                        .dt.tz_localize(None)
                    )
                frame.to_csv(output, index=False)
                print(f"Rows: {len(frame):,}; saved: {output.name}")
                break
            except Exception as exc:
                if is_http_402(exc):
                    raise RuntimeError(
                        "Dune returned HTTP 402 (credits/payment required)."
                    ) from exc
                if attempt == MAX_RETRIES:
                    raise
                wait = 30 * attempt
                print(f"Attempt {attempt} failed: {exc}; retrying in {wait}s")
                time.sleep(wait)


if __name__ == "__main__":
    main()
