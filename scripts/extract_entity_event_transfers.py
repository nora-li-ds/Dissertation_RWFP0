"""Extract entity-hour CEX-bound USDC/USDT transfers for eligible events.

Only entities active before an event are retained. This defines the event risk
set without conditioning inclusion on post-shock behaviour.
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
RAW_DIR = ROOT / "data" / "raw_entity_events"
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
    parser.add_argument(
        "--event-ids",
        nargs="+",
        help="Eligible event IDs to extract, for example E001 E002.",
    )
    parser.add_argument(
        "--all-eligible",
        action="store_true",
        help="Extract every event passing the market-stability screen.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing event extractions.",
    )
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
    event_id = event["event_id"]
    event_start = event["event_start"].strftime("%Y-%m-%d %H:%M:%S")
    window_start = event["window_start"].strftime("%Y-%m-%d %H:%M:%S")
    window_end = event["window_end"].strftime("%Y-%m-%d %H:%M:%S")
    start_date = event["window_start"].strftime("%Y-%m-%d")
    end_date = event["window_end"].strftime("%Y-%m-%d")

    return f"""
    WITH cex_addresses AS (
        SELECT
            address,
            MAX(name) AS cex_name,
            MAX(source) AS cex_label_source
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category = 'cex users'
        GROUP BY 1
    ),
    risk_labels AS (
        SELECT
            address,
            MAX(
                CASE WHEN category = 'ofac_sanction' THEN 1 ELSE 0 END
            ) AS ofac_sanction_label,
            MAX(
                CASE WHEN category = 'tornado_cash' THEN 1 ELSE 0 END
            ) AS tornado_cash_label
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category IN ('ofac_sanction', 'tornado_cash')
        GROUP BY 1
    ),
    qualifying_transfers AS (
        SELECT
            tt.block_time,
            tt.tx_hash,
            tt."from" AS entity_address,
            tt."to" AS cex_address,
            tt.symbol AS token_symbol,
            tt.amount,
            tt.amount_usd,
            cex.cex_name,
            cex.cex_label_source
        FROM tokens.transfers tt
        INNER JOIN cex_addresses cex
            ON tt."to" = cex.address
        WHERE tt.blockchain = 'ethereum'
          AND tt.block_time >= TIMESTAMP '{window_start}'
          AND tt.block_time < TIMESTAMP '{window_end}'
          AND tt.block_date >= DATE '{start_date}'
          AND tt.block_date <= DATE '{end_date}'
          AND tt.contract_address IN ({USDC}, {USDT})
          AND tt.amount IS NOT NULL
          AND tt.amount_usd IS NOT NULL
          AND tt."from" IS NOT NULL
    ),
    pre_active_entities AS (
        SELECT entity_address
        FROM qualifying_transfers
        WHERE block_time < TIMESTAMP '{event_start}'
        GROUP BY 1
    )
    SELECT
        '{event_id}' AS event_id,
        DATE_TRUNC('hour', qt.block_time) AS hour,
        CONCAT('0x', TO_HEX(qt.entity_address)) AS entity_address,
        qt.token_symbol,
        COUNT(*) AS transfer_count,
        COUNT(DISTINCT qt.tx_hash) AS transaction_count,
        SUM(qt.amount) AS volume_token,
        SUM(qt.amount_usd) AS volume_usd,
        COUNT(DISTINCT qt.cex_address) AS distinct_cex_addresses,
        MAX(qt.cex_name) AS example_cex_name,
        MAX(qt.cex_label_source) AS cex_label_source,
        COALESCE(MAX(risk.ofac_sanction_label), 0)
            AS ofac_sanction_label,
        COALESCE(MAX(risk.tornado_cash_label), 0)
            AS tornado_cash_label
    FROM qualifying_transfers qt
    INNER JOIN pre_active_entities active
        ON qt.entity_address = active.entity_address
    LEFT JOIN risk_labels risk
        ON qt.entity_address = risk.address
    GROUP BY 1, 2, 3, 4
    ORDER BY 2, 3, 4
    """


def main() -> None:
    args = parse_args()
    if not args.all_eligible and not args.event_ids:
        raise ValueError("Pass --event-ids or --all-eligible.")

    events = pd.read_csv(
        EVENT_FILE,
        parse_dates=[
            "event_start",
            "event_end",
            "peak_time",
            "window_start",
            "window_end",
        ],
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
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for _, event in events.sort_values("peak_time").iterrows():
        event_id = event["event_id"]
        output = RAW_DIR / f"{event_id}_entity_hour_transfers.csv"
        if output.exists() and not args.force:
            print(f"Loading existing extraction: {output.name}")
            continue

        print(
            f"Fetching {event_id}: "
            f"{event['window_start']} to {event['window_end']}"
        )
        sql = build_sql(event)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                rows = run_query(client, sql)
                frame = pd.DataFrame(rows)
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
                        "Dune returned HTTP 402 (credits/payment required). "
                        "No retry was attempted."
                    ) from exc
                if attempt == MAX_RETRIES:
                    raise
                wait = 30 * attempt
                print(f"Attempt {attempt} failed: {exc}; retrying in {wait}s")
                time.sleep(wait)


if __name__ == "__main__":
    main()
