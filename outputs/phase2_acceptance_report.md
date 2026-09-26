PAIMANA PHASE 2 ACCEPTANCE REPORT

Overall Status: PASS

Dataset:
- completed_cleaned.csv (100 source projects, 7766 snapshots)
- Model rows exclude terminal completed snapshots and unlabeled projects

Projects:
- 100

Observations:
- 7666

Cost Model:
ROC-AUC: 0.7162 ± 0.0994
PR-AUC: 0.7455 ± 0.0515
F1: 0.6328 ± 0.0429
Precision: 0.6984 ± 0.1113
Recall: 0.6040 ± 0.1190

Schedule Model:
ROC-AUC: 0.6402 ± 0.0794
PR-AUC: 0.7288 ± 0.1071
F1: 0.7392 ± 0.0427
Precision: 0.7278 ± 0.0595
Recall: 0.7545 ± 0.0542

Risk Combination:
Method: LogisticRegression on nested GroupKFold out-of-fold cost and schedule probabilities; final combiner is fit on base-model OOF probabilities.
Output Range: 0.192723 to 0.815332

Risk Thresholds:
LOW: overall_risk_probability <= 0.440457
MEDIUM: 0.440457 < overall_risk_probability <= 0.519482
HIGH: 0.519482 < overall_risk_probability <= 0.646974
CRITICAL: overall_risk_probability > 0.646974

Leakage Audit: PASS

GroupKFold: PASS

Temporal Integrity: PASS

Artifact Load Test: PASS

Ongoing Inference: PASS

End-to-End Pipeline: PASS

Remaining Issues:
- None

Next Phase:
- Integrate saved Phase 2 probabilities into the API risk contract without training on ongoing projects.
- Keep Phase 1 cleaning as the only source of completed_cleaned.csv / ongoing_cleaned.csv.

## AC checklist

| Criterion | Status |
|---|---|
| AC-01 Repository integrity | PASS |
| AC-02 Dataset integrity | PASS |
| AC-03 Prediction unit | PASS |
| AC-04 Six-month features | PASS |
| AC-05 Targets | PASS |
| AC-06 Leakage audit | PASS |
| AC-07 GroupKFold | PASS |
| AC-08 Preprocessing isolation | PASS |
| AC-09 Cost model | PASS |
| AC-10 Schedule model | PASS |
| AC-11 Reproducibility | PASS |
| AC-12 Risk combination | PASS |
| AC-13 Risk categories | PASS |
| AC-14 Artifacts | PASS |
| AC-15 Metadata | PASS |
| AC-16 Inference | PASS |
| AC-17 Ongoing scoring | PASS |
| AC-18 Temporal integrity | PASS |
| AC-19 End-to-end execution | PASS |
| AC-20 Notebook | PASS |
| AC-21 Code quality | PASS |
| AC-22 Documentation | PASS |
