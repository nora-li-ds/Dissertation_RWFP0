"""Run small Dune metadata queries needed before the main extraction.

The output is a local JSON audit record. It contains no API key and no wallet
level transfer data.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

# The checked-in project environments were created before the project folder
# was renamed and may have a stale interpreter path. Reuse their installed
# packages when the active interpreter does not already provide dune-client.
try:
    from dune_client.client import DuneClient
    from dotenv import load_dotenv
except ImportError:
    site_packages = ROOT / "venv" / "Lib" / "site-packages"
    sys.path.insert(0, str(site_packages))
    from dune_client.client import DuneClient
    from dotenv import load_dotenv


OUTPUT = ROOT / "results" / "schema_audit" / "dune_schema_audit.json"


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
        except TypeError as exc:  # client versions expose different signatures
            last_error = exc
            continue
        except Exception:
            raise
    raise RuntimeError(f"Dune query failed: {last_error}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("DUNE_API_KEY"):
        raise ValueError("DUNE_API_KEY is missing from the project .env file.")

    client = DuneClient(os.environ["DUNE_API_KEY"])
    queries = {
        "ethereum_label_categories": """
            SELECT category, COUNT(*) AS address_count
            FROM labels.addresses
            WHERE blockchain = 'ethereum'
            GROUP BY 1
            ORDER BY address_count DESC
        """,
        "required_table_columns": """
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE
                (table_schema = 'tokens' AND table_name = 'transfers')
                OR (table_schema = 'ethereum' AND table_name = 'blocks')
                OR (table_schema = 'labels' AND table_name = 'addresses')
                OR (table_schema = 'prices' AND table_name IN ('hour', 'usd'))
            ORDER BY table_schema, table_name, ordinal_position
        """,
    }

    audit: dict[str, Any] = {
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "queries": {},
    }
    for name, sql in queries.items():
        print(f"Running metadata query: {name}")
        try:
            audit["queries"][name] = {
                "status": "ok",
                "rows": run_query(client, sql),
            }
        except Exception as exc:
            audit["queries"][name] = {
                "status": "error",
                "error": str(exc),
            }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
