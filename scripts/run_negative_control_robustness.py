"""Local robustness checks for the negative-control aggregate model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "venv" / "Lib" / "site-packages"))

import numpy as np
import pandas as pd

import run_negative_control_analysis as nca


OUTPUT = ROOT / "results" / "negative_control_analysis"


def coefficient_for(panel: pd.DataFrame, label: str) -> dict[str, object]:
    model = nca.fit_model(panel, "log_transactions")
    table = nca.coefficient_frame(model, "transactions")
    row = table.loc[table["term"].eq("is_cex_bound:log_fee")].iloc[0]
    return {
        "specification": label,
        "events": panel["event_id"].nunique(),
        "coefficient": row["coefficient"],
        "standard_error": row["standard_error"],
        "p_value": row["p_value"],
        "ci_lower": row["ci_lower"],
        "ci_upper": row["ci_upper"],
    }


def main() -> None:
    panel = nca.build_panel()
    rows: list[dict[str, object]] = []
    rows.append(coefficient_for(panel, "all_events"))

    for event_id in sorted(panel["event_id"].unique()):
        rows.append(
            coefficient_for(
                panel.loc[panel["event_id"].ne(event_id)].copy(),
                f"omit_{event_id}",
            )
        )

    # E010 is an extreme event-level ratio outlier in the diagnostic table.
    if "E010" in set(panel["event_id"]):
        rows.append(
            coefficient_for(
                panel.loc[panel["event_id"].ne("E010")].copy(),
                "pre_specified_after_diagnostic_omit_E010",
            )
        )

    table = pd.DataFrame(rows)
    table.to_csv(OUTPUT / "negative_control_leave_one_out.csv", index=False)
    print(table.to_string(index=False))
    print(f"Saved: {OUTPUT / 'negative_control_leave_one_out.csv'}")


if __name__ == "__main__":
    main()
