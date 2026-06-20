"""Audit whether the repository is ready for final dissertation inference."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "results" / "event_catalog" / "eligible_events.csv"
ENTITY_DIR = ROOT / "data" / "raw_entity_events"
CONTROL_DIR = ROOT / "data" / "raw_negative_controls"
OUTPUT = ROOT / "results" / "data_quality" / "final_readiness.json"


def extracted_ids(directory: Path, suffix: str) -> set[str]:
    if not directory.exists():
        return set()
    return {
        path.name.removesuffix(suffix)
        for path in directory.glob(f"*{suffix}")
    }


def main() -> None:
    events = pd.read_csv(EVENTS)
    eligible = set(
        events.loc[
            events["analysis_eligible"].astype(str).eq("True"), "event_id"
        ]
    )
    entity_ids = extracted_ids(
        ENTITY_DIR, "_entity_hour_transfers.csv"
    )
    control_ids = extracted_ids(
        CONTROL_DIR, "_destination_groups.csv"
    )

    missing_entity = sorted(eligible.difference(entity_ids))
    missing_control = sorted(eligible.difference(control_ids))
    confirmatory_minimum = 15

    report = {
        "eligible_event_count": len(eligible),
        "entity_event_count": len(eligible.intersection(entity_ids)),
        "negative_control_event_count": len(
            eligible.intersection(control_ids)
        ),
        "missing_entity_events": missing_entity,
        "missing_negative_control_events": missing_control,
        "confirmatory_minimum_events": confirmatory_minimum,
        "entity_sample_meets_minimum": (
            len(eligible.intersection(entity_ids)) >= confirmatory_minimum
        ),
        "negative_control_sample_meets_minimum": (
            len(eligible.intersection(control_ids)) >= confirmatory_minimum
        ),
        "final_inference_ready": (
            len(eligible.intersection(entity_ids)) >= confirmatory_minimum
            and len(eligible.intersection(control_ids))
            >= confirmatory_minimum
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
