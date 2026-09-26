# PAIMANA Phase 2 modeling

Phase 2 trains leakage-safe snapshot models from Phase-1 cleaned CSVs only.
It does not rewrite Phase-1 cleaning and does not fit models on
`ongoing_cleaned.csv`.

## Documented commands

Install runtime libraries, then run from the repository root:

```powershell
.\venv\Scripts\python.exe -m pip install -r ml\requirements-phase2.txt
.\venv\Scripts\python.exe pipelines\training\train_phase2.py --audit-only
.\venv\Scripts\python.exe pipelines\training\train_phase2.py
.\venv\Scripts\python.exe pipelines\training\train_phase2.py --validate-artifacts-only
.\venv\Scripts\python.exe pipelines\training\train_phase2.py --score-only
```

Phase-1 cleaning (unchanged) remains:

```powershell
.\venv\Scripts\python.exe pipelines\transformation\phase1_clean.py
```

The development notebook is `notebooks/phase2_model_development.ipynb`. It calls
the same functions as the training CLI; it does not implement a second pipeline.

## 1. Dataset

Training uses `data/processed/completed_cleaned.csv` only.
Inference uses `data/processed/ongoing_cleaned.csv` only.

Every training observation must have a valid `Project_ID` and a parsed
`Snapshot_Date`. Duplicate `Project_ID + Snapshot_Date` rows keep the last
record after a chronological sort. Unique project counts, missingness, and
target class counts are written to `modeling/feature_target_audit.md` and
`modeling/feature_target_audit.json`.

## 2. Prediction unit

One model row is one `Project_ID + Snapshot_Date`. The snapshot date is stored
on the feature row and on `outputs/ongoing_risk_predictions.csv`.

## 3. Feature definitions

Approved families (expenditure, progress, schedule, staleness, status, static)
are listed in `models/paimana_phase2/feature_list.json` and documented in
`ml/phase2.py` (`FEATURE_SOURCE_MAPPING`). All lags, rolling statistics, and
staleness features use dates `<=` the snapshot date inside a six-month window
where applicable.

Insufficient history is allowed: missing lags stay missing and are imputed
inside each GroupKFold training fold. No forward fill is performed.

## 4. Target definitions

Saved in `models/paimana_phase2/target_definition.json`.

- `Cost_Overrun_Flag = 1` when latest project `Cost_Overrun_Percent >=` the
  configurable threshold (default 10).
- `Schedule_Overrun_Flag = 1` when latest project `Time_Overrun_Months >=` the
  configurable threshold (default 3 months).

Thresholds are CLI options `--cost-threshold` and `--schedule-threshold-months`.
Terminal completed snapshots have null outcome fields in this extract, so labels
use the latest non-null project-level values. Labels are never used as features.

## 5. Leakage controls

`modeling/leakage_audit.md` is generated before fitting. Forbidden predictors
include final overrun metrics, future completion fields, `Project_ID`,
`Project_Name`, and target-derived flags. Residual risk: Phase-1 modal
`Sector`/`Agency` cannot prove per-snapshot historical availability.

## 6. Validation methodology

`GroupKFold(n_splits=5)` with `groups = Project_ID`. Every fold asserts
`train_project_ids ∩ validation_project_ids = ∅`. No row-level random split.

## 7. Model configuration

L2-regularized `LogisticRegression` (`penalty="l2"`, `C=1.0`, `solver="lbfgs"`,
`random_state=42`) for cost, schedule, and the risk combination layer.
`class_weight="balanced"` is used when minority prevalence is below 0.35.
Project-equal sample weights prevent long time series from dominating.

## 8. Evaluation metrics

Fold metrics: ROC-AUC, PR-AUC (average precision), precision, recall, F1,
confusion matrix, Brier score. Summaries are `mean ± std` across five folds in
`models/paimana_phase2/model_metrics.json`.

## 9. Risk calculation

The combination model is `LogisticRegression` on
`[cost_overrun_probability, schedule_overrun_probability]` predicting
`Cost_Overrun_Flag OR Schedule_Overrun_Flag`. Nested GroupKFold out-of-fold
base predictions train the combiner; the final combiner is fit on base OOF
probabilities, never in-sample base scores.

## 10. Threshold calculation

LOW / MEDIUM / HIGH / CRITICAL cutoffs are the 25th / 50th / 75th percentiles
of nested OOF overall-risk probabilities on completed-project snapshots. Values
are stored in `models/paimana_phase2/risk_thresholds.json`. Each scored row
receives exactly one category.

## 11. Artifact locations

```
models/paimana_phase2/
  cost_model.pkl
  schedule_model.pkl
  risk_combination_model.pkl
  preprocessing.pkl
  feature_list.json
  target_definition.json
  risk_thresholds.json
  model_metrics.json
  model_metadata.json
```

Pickles are gitignored and reproduced by the training command. JSON metadata
is written beside them.

## 12. Inference procedure

From a fresh Python process, without retraining:

```python
from pipelines.inference.phase2_inference import (
    predict_cost_overrun,
    predict_schedule_overrun,
    predict_project_risk,
)

predict_project_risk(project_timeseries_dataframe)
```

Batch scoring:

```powershell
.\venv\Scripts\python.exe pipelines\training\train_phase2.py --score-only
```

Output: `outputs/ongoing_risk_predictions.csv` with `Project_ID`,
`Snapshot_Date`, cost/schedule/overall probabilities, and `Risk_Level`.
Missing-feature counts are reported in
`outputs/ongoing_inference_report.json` and as
`Missing_Approved_Feature_Count`. Missing lags are not forward-filled from
later snapshots.

Acceptance output: `outputs/phase2_acceptance_report.md`.
