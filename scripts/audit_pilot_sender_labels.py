"""Audit Dune label coverage among senders in one pilot event window."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "results" / "event_catalog" / "eligible_events.csv"
OUTPUT = ROOT / "results" / "schema_audit" / "pilot_sender_labels.json"
PILOT_EVENT_ID = "E002"

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


def main() -> None:
    events = pd.read_csv(
        EVENTS, parse_dates=["event_start", "window_start", "window_end"]
    )
    event = events.loc[events["event_id"].eq(PILOT_EVENT_ID)].iloc[0]
    start = event["window_start"].strftime("%Y-%m-%d %H:%M:%S")
    end = event["window_end"].strftime("%Y-%m-%d %H:%M:%S")
    start_date = event["window_start"].strftime("%Y-%m-%d")
    end_date = event["window_end"].strftime("%Y-%m-%d")

    sql = f"""
    WITH cex_addresses AS (
        SELECT DISTINCT address
        FROM labels.addresses
        WHERE blockchain = 'ethereum'
          AND category = 'cex users'
    ),
    pilot_senders AS (
        SELECT DISTINCT tt."from" AS address
        FROM tokens.transfers tt
        INNER JOIN cex_addresses cex ON tt."to" = cex.address
        WHERE tt.blockchain = 'ethereum'
          AND tt.block_time >= TIMESTAMP '{start}'
          AND tt.block_time < TIMESTAMP '{end}'
          AND tt.block_date >= DATE '{start_date}'
          AND tt.block_date <= DATE '{end_date}'
          AND tt.contract_address IN ({USDC}, {USDT})
          AND tt."from" IS NOT NULL
    )
    SELECT
        COALESCE(l.category, '__unlabelled__') AS category,
        COUNT(DISTINCT s.address) AS sender_count,
        MAX(l.source) AS example_source,
        MAX(l.label_type) AS example_label_type,
        MAX(l.model_name) AS example_model_name
    FROM pilot_senders s
    LEFT JOIN labels.addresses l
      ON s.address = l.address
     AND l.blockchain = 'ethereum'
    GROUP BY 1
    ORDER BY sender_count DESC
    """

    load_dotenv(ROOT / ".env")
    client = DuneClient(os.environ["DUNE_API_KEY"])
    try:
        result = client.run_sql(query_sql=sql)
    except TypeError:
        result = client.run_sql(sql=sql)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {"event_id": PILOT_EVENT_ID, "rows": extract_rows(result)},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
