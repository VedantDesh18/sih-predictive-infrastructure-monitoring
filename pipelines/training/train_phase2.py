"""Audit and train the PAIMANA Phase 2 baseline models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.phase2 import (  # noqa: E402
    ARTIFACT_DIR,
    COMPLETED_PATH,
    COST_OVERRUN_THRESHOLD,
    ONGOING_PATH,
    OUTPUT_PATH,
    SCHEDULE_OVERRUN_THRESHOLD_MONTHS,
    audit_cleaned_data,
    score_ongoing_projects,
    train_phase2,
    validate_fresh_process_load,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true", help="Write schema/target/leakage audits without fitting models")
    parser.add_argument("--validate-artifacts-only", action="store_true", help="Load saved artifacts in a fresh Python process")
    parser.add_argument("--score-only", action="store_true", help="Score ongoing_cleaned.csv from saved artifacts without retraining")
    parser.add_argument("--completed", type=Path, default=COMPLETED_PATH)
    parser.add_argument("--ongoing", type=Path, default=ONGOING_PATH)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--cost-threshold", type=float, default=COST_OVERRUN_THRESHOLD, help="Material cost overrun threshold in percent (default: 10)")
    parser.add_argument("--schedule-threshold-months", type=float, default=SCHEDULE_OVERRUN_THRESHOLD_MONTHS, help="Material schedule overrun threshold in months (default: 3)")
    args = parser.parse_args()

    if args.validate_artifacts_only:
        validate_fresh_process_load(args.artifact_dir)
        print("Fresh-process artifact loading passed.")
        return
    if args.score_only:
        scored = score_ongoing_projects(
            ongoing_path=args.ongoing,
            artifact_dir=args.artifact_dir,
            output_path=args.output,
        )
        print(json.dumps({
            "retraining_performed": False,
            "rows_scored": scored["report"]["rows_scored"],
            "projects_scored": scored["report"]["projects_scored"],
            "failed_or_invalid_prediction_rows": scored["report"]["failed_or_invalid_prediction_rows"],
            "output": str(args.output),
        }, indent=2))
        return
    if args.audit_only:
        audit = audit_cleaned_data(
            args.completed,
            args.ongoing,
            cost_threshold=args.cost_threshold,
            schedule_threshold_months=args.schedule_threshold_months,
        )
        print(json.dumps({"audit_written": True, "completed_projects": audit["datasets"]["completed_cleaned.csv"]["project_count"]}, indent=2))
        return

    result = train_phase2(
        completed_path=args.completed,
        ongoing_path=args.ongoing,
        artifact_dir=args.artifact_dir,
        output_path=args.output,
        cost_threshold=args.cost_threshold,
        schedule_threshold_months=args.schedule_threshold_months,
    )
    validate_fresh_process_load(args.artifact_dir)
    print(json.dumps({
        "cost_metrics_mean_std": result["model_metrics"]["cost_model"]["summary_mean_std"],
        "schedule_metrics_mean_std": result["model_metrics"]["schedule_model"]["summary_mean_std"],
        "risk_metrics_mean_std": result["model_metrics"]["risk_combination"]["summary_mean_std"],
        "risk_thresholds": result["risk_thresholds"]["threshold_values"],
        "completed_example": result["completed_example"],
        "ongoing_rows": len(result["ongoing_output"]),
        "artifact_dir": str(args.artifact_dir),
        "ongoing_output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
