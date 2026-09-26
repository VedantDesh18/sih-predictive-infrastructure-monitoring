"""
PAIMANA Phase-1 Data-Cleaning Pipeline
========================================
Processes two PAIMANA CSV files (ongoing monitoring targets + completed
training set) through six ordered cleaning steps:

  1. Static-field resolution (Sector, Agency, Project_Name → modal value per Project_ID)
  2. Corruption detection on Project_Name / Agency
  3. Original_Cost_Crore numeric coercion
  4. Sentinel / outlier handling (zero-cost → NaN, cap overruns)
  5. Row-level ₹2 Cr exclusion
  6. Tolerant date parsing

Outputs:
  • data/processed/ongoing_cleaned.csv
  • data/processed/completed_cleaned.csv
  • data/processed/phase1_quality_report.md

Outlier-cap rationale (Step 4):
  - Cost_Overrun_Percent  capped at  1 000 %
  - Time_Overrun_Months   capped at  1 000 months  (~83 years)
  These caps sit just above the 99.5-th percentile of both files' clean data
  (p99.5 ≈ 612 % cost, 568 months time in ongoing; 351 % cost, 459 months
  time in completed).  Values above the cap are virtually always data-entry
  artefacts — for example, Time_Overrun_Months reaching 92 580 or
  Cost_Overrun_Percent reaching 799 900 — while true extreme projects
  (India's oldest mega-project overruns top out around 600–850 months /
  660 % cost) are preserved.  Capped values are set to NaN (not clipped)
  so downstream models don't train on fabricated ceiling values.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STATIC_FIELDS = ["Sector", "Agency", "Project_Name"]
MODAL_COVERAGE_THRESHOLD = 0.60        # flag projects below this

COST_OVERRUN_CAP = 1_000.0             # percent
TIME_OVERRUN_CAP = 1_000.0             # months
COST_MIN_CRORE = 2.0                   # row-level exclusion

DATE_COLS = [
    "Snapshot_Date",
    "Date_of_Approval",
    "Original_DoC",
    "Revised_or_Anticipated_DoC",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _modal_value(series: pd.Series) -> tuple[str | None, float]:
    """Return (modal_value, coverage_fraction) for a Series of strings.

    Ignores NaN, bare '{', and values matching the '- [' corruption pattern.
    """
    clean = series.dropna()
    clean = clean[~clean.astype(str).str.strip().eq("{")]
    clean = clean[~clean.astype(str).str.contains(r"- \[", na=False)]
    if clean.empty:
        return None, 0.0
    counts = clean.value_counts()
    modal = counts.index[0]
    coverage = counts.iloc[0] / len(series)  # vs total rows (incl NaN)
    return modal, coverage


def _is_corrupt(value: str | None, modal: str | None, project_id: str) -> bool:
    """Return True if *value* matches any of the three corruption patterns."""
    if value is None or pd.isna(value):
        return False
    s = str(value).strip()
    # Pattern 1: bare '{'
    if s == "{":
        return True
    # Pattern 2: contains '- [' followed by the Project_ID
    if re.search(rf"- \[.*{re.escape(str(project_id))}", s):
        return True
    # simpler form: ends with '- [' (even without the full ID present)
    if s.endswith("- ["):
        return True
    # Pattern 3: truncated prefix of modal name
    if modal and s != modal and modal.startswith(s) and len(s) < len(modal):
        return True
    return False


def _tolerant_parse_date(val):
    """Parse a date string tolerantly.  Returns pd.NaT on failure."""
    if pd.isna(val):
        return pd.NaT
    s = str(val).strip()
    if not s:
        return pd.NaT
    # Try YYYY-MM first (most common in this data)
    try:
        return pd.Timestamp(s + "-01")  # e.g. "2023-03" → 2023-03-01
    except Exception:
        pass
    # Fallback: let pandas infer
    try:
        return pd.to_datetime(s, dayfirst=True)
    except Exception:
        return pd.NaT


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

class QualityReport:
    """Accumulates counts for the audit report."""

    def __init__(self, label: str):
        self.label = label
        self.rows_in = 0
        self.rows_out = 0
        self.projects_in = 0
        self.projects_out = 0

        # Step 1 – static-field resolution
        self.static_resolved: dict[str, int] = {}          # col → rows changed
        self.low_coverage_projects: list[dict] = []         # flagged projects

        # Step 2 – corruption
        self.corruption_detected_raw: dict[str, int] = {}   # col → count (pre-step-1)
        self.corruption_nulled: dict[str, int] = {}         # col → count (post-step-1 residual)

        # Step 3 – cost coercion
        self.cost_coercion_failed = 0

        # Step 4 – sentinels / outliers
        self.zero_cost_nulled = 0
        self.cost_overrun_capped = 0
        self.time_overrun_capped = 0

        # Step 5 – row exclusion
        self.rows_excluded_under_2cr = 0

        # Step 6 – dates parsed
        self.dates_parsed: dict[str, int] = {}              # col → non-NaT count
        self.dates_failed: dict[str, int] = {}              # col → NaT (was non-null)

    def to_markdown(self) -> str:
        lines = [
            f"## {self.label}",
            f"- Rows in: **{self.rows_in:,}** → Rows out: **{self.rows_out:,}**",
            f"- Projects in: **{self.projects_in}** → Projects out: **{self.projects_out}**",
            "",
            "### Step 1 — Static-field resolution",
        ]
        for col, n in self.static_resolved.items():
            lines.append(f"- `{col}`: {n:,} rows back-filled to modal value")
        if self.low_coverage_projects:
            lines.append("")
            lines.append(
                f"⚠️ **{len(self.low_coverage_projects)} project(s) flagged "
                f"(modal coverage < {MODAL_COVERAGE_THRESHOLD:.0%}):**"
            )
            for p in self.low_coverage_projects:
                lines.append(
                    f"  - `{p['Project_ID']}` — `{p['field']}` "
                    f"modal coverage = {p['coverage']:.1%} "
                    f"(modal = \"{p['modal_value'][:60] if p['modal_value'] else 'N/A'}\")"
                )
        else:
            lines.append("- No projects flagged for low modal coverage ✓")

        lines += [
            "",
            "### Step 2 — Corruption detection (Project_Name / Agency)",
        ]
        for col in ["Project_Name", "Agency"]:
            raw = self.corruption_detected_raw.get(col, 0)
            residual = self.corruption_nulled.get(col, 0)
            lines.append(
                f"- `{col}`: **{raw:,}** corrupt values in raw data "
                f"(resolved by modal back-fill in Step 1; "
                f"**{residual:,}** residual nulled post-step-1)"
            )

        lines += [
            "",
            "### Step 3 — Original_Cost_Crore numeric coercion",
            f"- **{self.cost_coercion_failed:,}** values failed coercion → NaN",
            "",
            "### Step 4 — Sentinel / outlier handling",
            f"- Zero-cost rows nulled: **{self.zero_cost_nulled:,}**",
            f"- Cost_Overrun_Percent nulled (>{COST_OVERRUN_CAP:,.0f}%): "
            f"**{self.cost_overrun_capped:,}**",
            f"- Time_Overrun_Months nulled (>{TIME_OVERRUN_CAP:,.0f} mo): "
            f"**{self.time_overrun_capped:,}**",
            "",
            "### Step 5 — Row-level ₹2 Cr exclusion",
            f"- Rows excluded (Original_Cost_Crore < {COST_MIN_CRORE}): "
            f"**{self.rows_excluded_under_2cr:,}**",
            "",
            "### Step 6 — Tolerant date parsing",
        ]
        for col in DATE_COLS:
            ok = self.dates_parsed.get(col, 0)
            fail = self.dates_failed.get(col, 0)
            lines.append(f"- `{col}`: {ok:,} parsed, {fail:,} unparseable → NaT")
        lines.append("")
        return "\n".join(lines)


def clean_frame(df: pd.DataFrame, label: str) -> tuple[pd.DataFrame, QualityReport]:
    """Apply all six cleaning steps. Returns (cleaned_df, report)."""

    rpt = QualityReport(label)
    rpt.rows_in = len(df)
    rpt.projects_in = df["Project_ID"].nunique()
    df = df.copy()

    # ------------------------------------------------------------------
    # PRE-STEP: Compute modal values and count raw corruption
    # ------------------------------------------------------------------
    modal_lookup: dict[str, dict[str, str | None]] = {}   # pid -> {col: modal}
    for pid, grp in df.groupby("Project_ID"):
        modal_lookup[pid] = {}
        for col in STATIC_FIELDS:
            modal, coverage = _modal_value(grp[col])
            modal_lookup[pid][col] = modal
            if coverage < MODAL_COVERAGE_THRESHOLD:
                rpt.low_coverage_projects.append(
                    {
                        "Project_ID": pid,
                        "field": col,
                        "coverage": coverage,
                        "modal_value": modal,
                    }
                )

    # Count corruption on RAW data (before Step 1 overwrites)
    for col in ["Project_Name", "Agency"]:
        raw_corrupt = 0
        for pid, grp in df.groupby("Project_ID"):
            modal = modal_lookup[pid].get(col)
            for _, val in grp[col].items():
                if _is_corrupt(val, modal, pid):
                    raw_corrupt += 1
        rpt.corruption_detected_raw[col] = raw_corrupt

    # ------------------------------------------------------------------
    # STEP 1: Static-field resolution
    # ------------------------------------------------------------------
    for col in STATIC_FIELDS:
        rpt.static_resolved[col] = 0

    for col in STATIC_FIELDS:
        before = df[col].copy()
        df[col] = df.apply(
            lambda row, _c=col: modal_lookup[row["Project_ID"]][_c], axis=1
        )
        changed = (before.fillna("__NA__") != df[col].fillna("__NA__")).sum()
        rpt.static_resolved[col] = int(changed)

    # ------------------------------------------------------------------
    # STEP 2: Corruption detection (Project_Name, Agency) — safety net
    #   Step 1 resolves most corruption via modal back-fill. This step
    #   catches any residual cases (e.g. if the modal itself were corrupt).
    # ------------------------------------------------------------------
    for col in ["Project_Name", "Agency"]:
        rpt.corruption_nulled[col] = 0
        mask = pd.Series(False, index=df.index)
        for pid, grp in df.groupby("Project_ID"):
            modal = modal_lookup[pid].get(col)
            for idx, val in grp[col].items():
                if _is_corrupt(val, modal, pid):
                    mask.at[idx] = True
        nulled = mask.sum()
        df.loc[mask, col] = pd.NA
        rpt.corruption_nulled[col] = int(nulled)

    # ------------------------------------------------------------------
    # STEP 3: Original_Cost_Crore numeric coercion
    # ------------------------------------------------------------------
    before_na = df["Original_Cost_Crore"].isna().sum()
    df["Original_Cost_Crore"] = pd.to_numeric(
        df["Original_Cost_Crore"], errors="coerce"
    )
    after_na = df["Original_Cost_Crore"].isna().sum()
    rpt.cost_coercion_failed = int(after_na - before_na)

    # ------------------------------------------------------------------
    # STEP 4: Sentinel / outlier handling
    # ------------------------------------------------------------------
    # 4a. Zero cost → NaN
    zero_mask = df["Original_Cost_Crore"] == 0
    rpt.zero_cost_nulled = int(zero_mask.sum())
    df.loc[zero_mask, "Original_Cost_Crore"] = pd.NA

    # 4b. Cap Cost_Overrun_Percent
    df["Cost_Overrun_Percent"] = pd.to_numeric(
        df["Cost_Overrun_Percent"], errors="coerce"
    )
    cap_mask = df["Cost_Overrun_Percent"].abs() > COST_OVERRUN_CAP
    rpt.cost_overrun_capped = int(cap_mask.sum())
    df.loc[cap_mask, "Cost_Overrun_Percent"] = pd.NA

    # 4c. Cap Time_Overrun_Months
    df["Time_Overrun_Months"] = pd.to_numeric(
        df["Time_Overrun_Months"], errors="coerce"
    )
    cap_mask = df["Time_Overrun_Months"].abs() > TIME_OVERRUN_CAP
    rpt.time_overrun_capped = int(cap_mask.sum())
    df.loc[cap_mask, "Time_Overrun_Months"] = pd.NA

    # ------------------------------------------------------------------
    # STEP 5: Row-level ₹2 Cr exclusion
    # ------------------------------------------------------------------
    keep_mask = df["Original_Cost_Crore"].isna() | (
        df["Original_Cost_Crore"] >= COST_MIN_CRORE
    )
    rpt.rows_excluded_under_2cr = int((~keep_mask).sum())
    df = df[keep_mask].copy()

    # ------------------------------------------------------------------
    # STEP 6: Tolerant date parsing
    # ------------------------------------------------------------------
    for col in DATE_COLS:
        if col not in df.columns:
            continue
        was_notna = df[col].notna().sum()
        df[col] = df[col].apply(_tolerant_parse_date)
        now_notna = df[col].notna().sum()
        rpt.dates_parsed[col] = int(now_notna)
        rpt.dates_failed[col] = int(was_notna - now_notna)

    rpt.rows_out = len(df)
    rpt.projects_out = df["Project_ID"].nunique()
    return df, rpt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(
    ongoing_path: str | Path,
    completed_path: str | Path,
    output_dir: str | Path,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_parts = [
        "# PAIMANA Phase-1 Data-Quality Report",
        f"_Generated: {ts}_\n",
        f"**Outlier caps applied:** Cost_Overrun_Percent > ±{COST_OVERRUN_CAP:,.0f}% → NaN | "
        f"Time_Overrun_Months > ±{TIME_OVERRUN_CAP:,.0f} months → NaN\n",
    ]

    for label, path in [
        ("Ongoing (monitoring target)", ongoing_path),
        ("Completed (training set)", completed_path),
    ]:
        print(f"\n{'='*60}")
        print(f"Processing: {label}")
        print(f"  Source: {path}")
        df = pd.read_csv(path, low_memory=False)
        cleaned, rpt = clean_frame(df, label)

        tag = "ongoing" if "ongoing" in label.lower() else "completed"
        out_csv = output_dir / f"{tag}_cleaned.csv"
        cleaned.to_csv(out_csv, index=False)
        print(f"  -> Saved {out_csv}  ({len(cleaned):,} rows)")

        report_parts.append(rpt.to_markdown())

    report_md = "\n".join(report_parts)
    report_path = output_dir / "phase1_quality_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\n[OK] Quality report: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PAIMANA Phase-1 data cleaning pipeline"
    )
    parser.add_argument(
        "--ongoing",
        default=str(REPO_ROOT / "CODE" / "PAIMANA_100_low_ambiguity_ongoing_projects_full_journey.csv"),
        help="Path to the ongoing-projects CSV",
    )
    parser.add_argument(
        "--completed",
        default=str(REPO_ROOT / "CODE" / "PAIMANA_ML_Prototype_Completed_TimeSeries.csv"),
        help="Path to the completed-projects CSV",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "data" / "processed"),
        help="Directory for cleaned outputs",
    )
    args = parser.parse_args()
    main(args.ongoing, args.completed, args.output_dir)
