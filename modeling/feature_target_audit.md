# Phase 2 Feature and Target Audit

Generated: 2026-09-25T19:22:09.209955+00:00

## Dataset inventory
### `completed_cleaned.csv`
- Rows/projects: 7,766 rows / 100 projects
- Snapshot range: 2017-04-01T00:00:00 to 2025-06-01T00:00:00; missing dates: 0
- Observations/project: min 28, median 83.0, max 97
- Unique Sector/Agency counts: 13 / 38
- Exact columns and dtypes:
  - `Project_ID`: `str`, missing 0.0%
  - `Project_Name`: `str`, missing 0.0%
  - `Snapshot_Date`: `str`, missing 0.0%
  - `Time_Index`: `int64`, missing 0.0%
  - `Is_Completed_Snapshot`: `int64`, missing 0.0%
  - `Agency`: `str`, missing 0.0%
  - `Sector`: `str`, missing 0.0%
  - `Project_Status`: `str`, missing 23.6%
  - `Date_of_Approval`: `str`, missing 6.9%
  - `Original_DoC`: `str`, missing 17.8%
  - `Revised_or_Anticipated_DoC`: `str`, missing 26.1%
  - `Original_Cost_Crore`: `float64`, missing 2.8%
  - `Revised_or_Anticipated_Cost_Crore`: `str`, missing 3.9%
  - `Cumulative_Expenditure_Crore`: `str`, missing 8.7%
  - `Milestones_Achieved`: `float64`, missing 56.6%
  - `Milestones_Total`: `float64`, missing 56.6%
  - `Milestone_Percent`: `float64`, missing 56.6%
  - `Time_Overrun_Months`: `float64`, missing 32.1%
  - `Cost_Overrun_Percent`: `float64`, missing 10.0%
  - `Delay_Months`: `str`, missing 71.6%
  - `Delay_Reason`: `str`, missing 88.4%
  - `Has_Fixed_DoC`: `str`, missing 0.2%
  - `Has_Milestones`: `str`, missing 0.0%
  - `Completed_In_Snapshot`: `str`, missing 0.0%
  - `Completion_Month`: `str`, missing 98.7%
  - `Physical_Progress (%)`: `float64`, missing 96.7%
### `ongoing_cleaned.csv`
- Rows/projects: 6,511 rows / 100 projects
- Snapshot range: 2017-04-01T00:00:00 to 2025-06-01T00:00:00; missing dates: 0
- Observations/project: min 7, median 73.0, max 97
- Unique Sector/Agency counts: 7 / 34
- Exact columns and dtypes:
  - `Project_ID`: `str`, missing 0.0%
  - `Project_Name`: `str`, missing 0.0%
  - `Agency`: `str`, missing 0.0%
  - `Sector`: `str`, missing 0.0%
  - `Project_Status`: `str`, missing 25.5%
  - `Snapshot_Date`: `str`, missing 0.0%
  - `Date_of_Approval`: `str`, missing 13.2%
  - `Original_DoC`: `str`, missing 32.8%
  - `Revised_or_Anticipated_DoC`: `str`, missing 34.8%
  - `Original_Cost_Crore`: `float64`, missing 3.5%
  - `Revised_or_Anticipated_Cost_Crore`: `str`, missing 4.1%
  - `Cumulative_Expenditure_Crore`: `str`, missing 7.4%
  - `Milestones_Achieved`: `float64`, missing 82.6%
  - `Milestones_Total`: `float64`, missing 82.6%
  - `Milestone_Percent`: `float64`, missing 82.6%
  - `Time_Overrun_Months`: `float64`, missing 46.1%
  - `Cost_Overrun_Percent`: `float64`, missing 16.5%
  - `Delay_Months`: `str`, missing 83.3%
  - `Delay_Reason`: `str`, missing 89.6%
  - `Has_Fixed_DoC`: `str`, missing 0.2%
  - `Has_Milestones`: `str`, missing 0.0%
  - `Completed_In_Snapshot`: `str`, missing 0.0%
  - `Completion_Month`: `str`, missing 99.9%
  - `Physical_Progress (%)`: `float64`, missing 90.3%

## Outcomes and targets
- Terminal completed rows: 100; cost/schedule outcome values on those rows: 0/0.
- Therefore the target source mapping is the latest non-null outcome value per project in the cleaned completed history, which is retained as a project-level label only. This is the closest available project-level final outcome; the actual terminal row has no target value.
- Cost outcomes (project-level latest): n=100, min=-51.37, median=2.79, p75=52.53, max=350.75; target `Cost_Overrun_Flag = 1` when latest `Cost_Overrun_Percent >= 10`. Class counts: `{'0': 54, '1': 46}`.
- Schedule outcomes (project-level latest): n=100, min=0.00, median=24.50, p75=77.25, max=862.00; target `Schedule_Overrun_Flag = 1` when latest `Time_Overrun_Months >= 3`. Class counts: `{'1': 64, '0': 36}`.
- No target threshold was defined in existing architecture/docs. Thresholds are configurable via the Phase-2 training CLI; 10% and 3 months are explicit material-overrun defaults, not architecture specifications.

## Field families and model inputs
- Cost fields: `Original_Cost_Crore`, `Revised_or_Anticipated_Cost_Crore`, `Cumulative_Expenditure_Crore`, and target-only `Cost_Overrun_Percent`.
- Schedule/date fields: `Snapshot_Date`, `Date_of_Approval`, `Original_DoC`, `Revised_or_Anticipated_DoC`; `Completion_Month` is excluded.
- Progress: `Physical_Progress (%)`, `Milestone_Percent`, `Milestones_Achieved`, `Milestones_Total`; progress percentages outside 0–100 are treated as missing only in feature engineering.
- Status/static: `Project_Status`, `Sector`, `Agency`; `Project_Name` is excluded.
- Numeric feature list (55): `original_cost_crore`, `revised_budget_crore`, `revised_budget_to_original_ratio`, `cumulative_expenditure_crore`, `expenditure_ratio`, `expenditure_lag_1m_crore`, `expenditure_lag_3m_crore`, `expenditure_lag_6m_crore`, `expenditure_velocity_crore_per_month`, `expenditure_growth_1m_pct`, `expenditure_growth_3m_pct`, `expenditure_3m_trend_crore_per_month`, `expenditure_6m_trend_crore_per_month`, `expenditure_rolling_mean_6m_crore`, `expenditure_rolling_volatility_6m_crore`, `expenditure_observations_6m`, `months_since_expenditure_update`, `physical_progress_pct`, `physical_progress_lag_1m_pct`, `physical_progress_lag_3m_pct`, `physical_progress_lag_6m_pct`, `physical_progress_velocity_pct_per_month`, `physical_progress_acceleration_pct_per_month2`, `physical_progress_rolling_trend_6m_pct_per_month`, `milestone_progress_pct`, `milestone_progress_lag_1m_pct`, `milestone_progress_lag_3m_pct`, `milestone_progress_lag_6m_pct`, `milestone_progress_velocity_pct_per_month`, `milestone_progress_acceleration_pct_per_month2`, `milestone_progress_rolling_trend_6m_pct_per_month`, `progress_current_pct`, `progress_velocity_pct_per_month`, `progress_acceleration_pct_per_month2`, `progress_rolling_trend_6m_pct_per_month`, `months_since_physical_progress_update`, `months_since_milestone_progress_update`, `months_since_progress_update`, `planned_duration_months`, `elapsed_since_approval_months`, `schedule_slippage_months`, `original_doc_slippage_months`, `revised_doc_slippage_months`, `revised_doc_shift_from_original_months`, `revised_doc_movement_1m_months`, `delay_growth_1m_months`, `delay_growth_3m_months`, `delay_growth_6m_months`, `milestone_slippage_vs_elapsed_pct_points`, `months_since_status_update`, `status_changes_6m`, `status_change_frequency_6m`, `status_recently_changed`, `history_months_available`, `lookback_observation_count_6m`
- Categorical feature list: `Sector`, `Agency`, `Project_Status`

## Temporal and missing-history policy
- Prediction row: `Project_ID + Snapshot_Date`, sorted chronologically. All shifts, trends, rolling windows, status changes, and staleness checks use rows at or before the prediction date and no older than six calendar months where applicable.
- No minimum history is required. Missing lags are explicitly left missing, then imputed within each GroupKFold training fold; no forward fill is performed. Completed terminal rows are excluded; no rows are removed for insufficient six-month history.
- Phase-1 modal resolution for Sector/Agency is retained as requested; its use of full-project modal values is documented as residual historical-availability risk in the leakage audit.
