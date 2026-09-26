# """Extract a validated PAIMANA monthly project time series from text-native PDFs.

# The extractor deliberately uses page coordinates for records.  PDF reading order is
# not trusted: project-code anchors define each record's vertical band and values are
# read from fixed column regions discovered from the table header.  OCR is reserved
# for image-only pages (none in the supplied run).
# """
# from __future__ import annotations

# import argparse
# import csv
# import math
# import re
# from collections import Counter
# from datetime import date
# from pathlib import Path

# import pandas as pd
# import pymupdf


# SCHEMA = [
#     "Project_ID", "Project_Name", "Agency", "Sector", "Ministry",
#     "Project_Status", "Snapshot_Date", "Date_of_Approval", "Start_Date",
#     "Original_DoC", "Revised_or_Anticipated_DoC", "Original_Cost_Crore",
#     "Revised_or_Anticipated_Cost_Crore", "Cumulative_Expenditure_Crore",
#     "Milestones_Achieved", "Milestones_Total", "Milestone_Percent",
#     "Time_Overrun_Months", "Cost_Overrun_Percent", "Delay_Months",
#     "Delay_Reason", "Has_Fixed_DoC", "Has_Milestones",
#     "Completed_In_Snapshot", "Completion_Month", "Physical_Progress_Percent",
# ]

# SECTORS = [
#     "ATOMIC ENERGY", "CIVIL AVIATION", "COAL", "COMMERCE AND INDUSTRY",
#     "COMMUNICATION", "DEFENCE", "DRINKING WATER AND SANITATION", "EDUCATION",
#     "FERTILIZERS", "FINANCE", "HEALTH", "HEAVY INDUSTRY", "HOME AFFAIRS",
#     "HOUSING", "PETROLEUM", "POWER", "RAILWAYS", "ROAD TRANSPORT AND HIGHWAYS",
#     "RURAL DEVELOPMENT", "SHIPPING", "STEEL", "TELECOMMUNICATION",
#     "TEXTILES", "TOURISM", "URBAN DEVELOPMENT", "WATER RESOURCES",
# ]
# ID_RE = re.compile(r"^[A-Z]?\d{8,9}$")
# MONTH_RE = re.compile(r"^(\d{1,2})[/-](\d{2,4})$")
# MON_NAME_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/]?(\d{2,4})$", re.I)


# def clean(text: str) -> str:
#     return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


# def nullify(value):
#     if value is None or (isinstance(value, float) and math.isnan(value)):
#         return None
#     value = clean(str(value))
#     return value or None


# def parse_month(value: str | None) -> str | None:
#     """Normalize a PAIMANA month value to YYYY-MM; never guess malformed dates."""
#     if not value:
#         return None
#     value = clean(value).strip("(){}[] ")
#     if value.upper() in {"N.A.", "NA", "N/A", "-", ""}:
#         return None
#     m = MONTH_RE.match(value)
#     if m:
#         a, b = int(m.group(1)), int(m.group(2))
#         if len(m.group(2)) == 4:
#             month, year = a, b
#         else:
#             month, year = a, (2000 + b if b < 70 else 1900 + b)
#         return f"{year:04d}-{month:02d}" if 1 <= month <= 12 else None
#     m = MON_NAME_RE.match(value)
#     if m:
#         month = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"].index(m.group(1).lower()) + 1
#         y = int(m.group(2))
#         year = y if len(m.group(2)) == 4 else (2000 + y if y < 70 else 1900 + y)
#         return f"{year:04d}-{month:02d}"
#     return None


# def parse_number(value: str | None) -> float | None:
#     if not value:
#         return None
#     value = clean(value).strip("(){}[] ").replace(",", "")
#     if value.upper() in {"N.A.", "NA", "N/A", "-", ""}:
#         return None
#     try:
#         number = float(value)
#         return number if math.isfinite(number) else None
#     except ValueError:
#         return None


# def month_diff(a: str | None, b: str | None) -> int | None:
#     if not a or not b:
#         return None
#     try:
#         ay, am = map(int, a.split("-")); by, bm = map(int, b.split("-"))
#         return (by - ay) * 12 + bm - am
#     except ValueError:
#         return None


# def snapshot_from_text(text: str) -> tuple[str | None, str | None]:
#     m = re.search(
#         r"Ongoing Projects as of\s+(?:\d{1,2}(?:st|nd|rd|th)\s+)?"
#         r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",
#         text, re.I,
#     )
#     if not m:
#         return None, None
#     month_name, year = m.group(1), int(m.group(2))
#     month = pd.to_datetime(month_name, format="%B").month
#     return f"{month}/1/{year}", f"{year:04d}-{month:02d}"


# def grouped_lines(words, x_min: float, x_max: float, y_min: float, y_max: float):
#     """Return coordinate-preserving text lines for one cell column/band."""
#     chosen = [w for w in words if x_min <= w[0] < x_max and y_min < w[1] <= y_max]
#     grouped: dict[int, list[tuple]] = {}
#     for w in chosen:
#         grouped.setdefault(round(w[1]), []).append(w)
#     result = []
#     for y in sorted(grouped):
#         result.append((y, clean(" ".join(w[4] for w in sorted(grouped[y], key=lambda z: z[0])))))
#     return result


# def cell_text(words, x_min, x_max, y_min, y_max) -> str:
#     return clean(" ".join(line for _, line in grouped_lines(words, x_min, x_max, y_min, y_max)))


# def code_anchors(words, page_height: float):
#     anchors = []
#     for w in words:
#         token = re.sub(r"[^A-Z0-9]", "", w[4].upper())
#         # Project-code column; excludes the catalogue/footers and numeric data columns.
#         if 145 <= w[0] <= 290 and w[1] < page_height - 35 and ID_RE.fullmatch(token):
#             anchors.append((w[1], token, w[0]))
#     # A code can be emitted twice by an overlapping text object. Retain one anchor.
#     dedup = []
#     for anchor in sorted(anchors):
#         if not dedup or anchor[1] != dedup[-1][1] or abs(anchor[0] - dedup[-1][0]) > 3:
#             dedup.append(anchor)
#     return dedup


# def sector_events(words):
#     events = []
#     # Sector headings live in the column immediately right of State. Search a short
#     # vertical window to reconstruct wrapped headings such as ROAD TRANSPORT/HIGHWAYS.
#     ys = sorted({round(w[1]) for w in words if 70 <= w[0] < 140})
#     for y in ys:
#         sample = re.sub(r"\b\d+\b", "", cell_text(words, 70, 140, y - 2, y + 45).upper())
#         sample = clean(sample)
#         for sector in SECTORS:
#             if sector in sample:
#                 events.append((y, sector))
#     return sorted(set(events))


# def values_from_column(text: str, kind: str) -> list[str]:
#     if kind == "date":
#         tokens = re.findall(r"[({]?\s*(?:\d{1,2}[/-]\d{2,4}|[A-Za-z]{3,9}[-/]?\d{2,4}|N\.?A\.?)\s*[)}]?", text)
#     else:
#         tokens = re.findall(r"[({]?\s*(?:[\d,]+(?:\.\d+)?|N\.?A\.?)\s*[)}]?", text)
#     return [clean(x) for x in tokens]


# def pick_source_value(tokens: list[str], marker: str) -> str | None:
#     """Select brace anticipated value, then parenthesized revised, then original."""
#     if not tokens:
#         return None
#     if marker == "original":
#         return tokens[0]
#     bracketed = [x for x in tokens if "{" in x]
#     if bracketed:
#         return bracketed[-1]
#     paren = [x for x in tokens[1:] if "(" in x]
#     return paren[-1] if paren else (tokens[-1] if len(tokens) > 1 else None)


# def name_and_agency(words, y_start, y_end, project_left, approval_left):
#     # The serial-number column is immediately to the left of Project Name and shifts
#     # between report generations.  Anchor the name column on the code's x-position.
#     lines = grouped_lines(words, project_left - 1, approval_left - 3, y_start, y_end)
#     code_line = None
#     for index, (y, line) in enumerate(lines):
#         if ID_RE.search(re.sub(r"[^A-Z0-9]", "", line.upper())):
#             code_line = index
#             break
#     if code_line is None:
#         code_line = len(lines)
#     before_code = lines[:code_line]
#     agency = None
#     agency_line = None
#     for y, line in reversed(before_code):
#         groups = re.findall(r"\(([^()]*)\)", line)
#         if groups:
#             candidate = clean(groups[-1])
#             if candidate and not ID_RE.fullmatch(re.sub(r"[^A-Z0-9]", "", candidate.upper())):
#                 agency, agency_line = candidate, y
#                 break
#     name_lines = [line for y, line in before_code if agency_line is None or y < agency_line]
#     name = clean(" ".join(name_lines))
#     # A one-line agency can share a line with its project name in some layouts.
#     if agency and name.endswith(f"({agency})"):
#         name = clean(name[:-(len(agency) + 2)])
#     return name or None, agency or None


# def page_layout(words):
#     """Read table column positions from the page header; use known safe defaults on continuation pages."""
#     def first_x(token, minimum=0):
#         values = [w[0] for w in words if w[4].strip(".:").lower() == token and w[0] >= minimum and w[1] < 160]
#         return min(values) if values else None
#     approval = first_x("approval", 250)
#     commissioning = first_x("commissioning", 300)
#     cumulative = first_x("cumulative", 460)
#     physical = first_x("physical", 520) or first_x("progress", 520)
#     costs = [w[0] for w in words if w[4].strip(".:").lower() == "cost" and 380 < w[0] < 480 and w[1] < 160]
#     cost = min(costs) if costs else None
#     if not all((approval, commissioning, cost, cumulative, physical)):
#         return None
#     return {"approval": approval, "commissioning": commissioning, "cost": cost, "cumulative": cumulative, "physical": physical}


# def extract_page_records(words, page_height, snapshot_display, snapshot_iso, previous_sector, layout):
#     anchors = code_anchors(words, page_height)
#     if not anchors:
#         return [], previous_sector
#     events = sector_events(words)
#     records = []
#     current_sector = previous_sector
#     previous_y = 150.0
#     for code_y, project_id, code_x in anchors:
#         for event_y, sector in events:
#             if previous_y - 2 <= event_y <= code_y:
#                 current_sector = sector
#         project_name, agency = name_and_agency(words, previous_y, code_y + 2, code_x, layout["approval"])
#         approval = pick_source_value(values_from_column(cell_text(words, layout["approval"] - 8, layout["commissioning"] - 6, previous_y, code_y + 2), "date"), "original")
#         doc_tokens = values_from_column(cell_text(words, layout["commissioning"] - 8, layout["cost"] - 6, previous_y, code_y + 2), "date")
#         cost_tokens = values_from_column(cell_text(words, layout["cost"] - 8, layout["cumulative"] - 6, previous_y, code_y + 2), "number")
#         expenditure_tokens = values_from_column(cell_text(words, layout["cumulative"] - 8, layout["physical"] - 6, previous_y, code_y + 2), "number")
#         progress_tokens = values_from_column(cell_text(words, layout["physical"] - 8, layout["physical"] + 55, previous_y, code_y + 2), "number")
#         original_doc = parse_month(pick_source_value(doc_tokens, "original"))
#         anticipated_doc = parse_month(pick_source_value(doc_tokens, "anticipated"))
#         original_cost = parse_number(pick_source_value(cost_tokens, "original"))
#         revised_cost = parse_number(pick_source_value(cost_tokens, "anticipated"))
#         expenditure = parse_number(pick_source_value(expenditure_tokens, "original"))
#         progress = parse_number(pick_source_value(progress_tokens, "original"))
#         overrun = month_diff(original_doc, anticipated_doc)
#         cost_overrun = None
#         if original_cost not in (None, 0) and revised_cost is not None:
#             cost_overrun = round((revised_cost - original_cost) * 100 / original_cost, 4)
#         records.append({
#             "Project_ID": project_id, "Project_Name": project_name, "Agency": agency,
#             "Sector": current_sector, "Ministry": None, "Project_Status": "Ongoing",
#             "Snapshot_Date": snapshot_display, "Date_of_Approval": parse_month(approval),
#             "Start_Date": None, "Original_DoC": original_doc,
#             "Revised_or_Anticipated_DoC": anticipated_doc,
#             "Original_Cost_Crore": original_cost,
#             "Revised_or_Anticipated_Cost_Crore": revised_cost,
#             "Cumulative_Expenditure_Crore": expenditure,
#             "Milestones_Achieved": None, "Milestones_Total": None, "Milestone_Percent": None,
#             "Time_Overrun_Months": overrun, "Cost_Overrun_Percent": cost_overrun,
#             "Delay_Months": None, "Delay_Reason": None,
#             "Has_Fixed_DoC": "Yes" if original_doc else "No", "Has_Milestones": "No",
#             "Completed_In_Snapshot": "No", "Completion_Month": None,
#             "Physical_Progress_Percent": progress,
#         })
#         previous_y = code_y + 1
#     return records, current_sector


# def record_issues(row):
#     issues = []
#     if not row["Project_ID"] or not ID_RE.fullmatch(str(row["Project_ID"])):
#         issues.append("invalid_project_id")
#     if not row["Project_Name"]:
#         issues.append("missing_project_name")
#     if row["Date_of_Approval"] is None:
#         issues.append("missing_or_invalid_approval_date")
#     if row["Original_Cost_Crore"] is None:
#         issues.append("missing_or_invalid_original_cost")
#     if row["Cumulative_Expenditure_Crore"] is None:
#         issues.append("missing_or_invalid_cumulative_expenditure")
#     if row["Physical_Progress_Percent"] is not None and not (0 <= row["Physical_Progress_Percent"] <= 100):
#         issues.append("physical_progress_out_of_range")
#     if row["Original_Cost_Crore"] is not None and row["Original_Cost_Crore"] < 0:
#         issues.append("negative_original_cost")
#     return issues


# def table_pages(document):
#     """Identify only the full current-snapshot project table, never summary tables."""
#     first = None
#     snapshot_display = snapshot_iso = None
#     texts = []
#     for number, page in enumerate(document, start=1):
#         text = page.get_text("text")
#         texts.append(text)
#         display, iso = snapshot_from_text(text)
#         if display and "Project Code" in text and first is None:
#             first, snapshot_display, snapshot_iso = number, display, iso
#     if first is None:
#         return [], None, None
#     pages = []
#     for number in range(first, len(document) + 1):
#         text = texts[number - 1]
#         if number > first and re.search(r"Table\s*[:-]?\s*[89]\b", text, re.I):
#             break
#         # The table's continuation pages contain project codes in the code column.
#         words = document[number - 1].get_text("words")
#         if code_anchors(words, document[number - 1].rect.height):
#             pages.append(number)
#         elif pages:
#             # A single no-code page at the end may be a totals page; stop so another
#             # catalogue table cannot be interpreted as project records.
#             break
#     return pages, snapshot_display, snapshot_iso


# def read_sample_schema(path: Path):
#     # The supplied sample uses Windows-1252 punctuation; schema is read only.
#     for encoding in ("utf-8", "cp1252", "latin1"):
#         try:
#             with path.open("r", encoding=encoding, newline="") as handle:
#                 return next(csv.reader(handle))
#         except UnicodeDecodeError:
#             continue
#     raise ValueError("Could not read sample CSV header")


# def process_pdf(pdf_path: Path):
#     document = pymupdf.open(pdf_path)
#     document_page_count = len(document)
#     pages, snapshot_display, snapshot_iso = table_pages(document)
#     source_audit = []
#     extracted = []
#     if not pages:
#         source_audit.append({
#             "Source_PDF": pdf_path.name, "Source_Page": None, "Project_ID": None,
#             "Snapshot_Date": None, "Extraction_Method": "layout_detection",
#             "Confidence": 0.0, "Disposition": "review", "Validation_Issues": "no_full_ongoing_project_table_detected",
#             "Raw_Excerpt": "The supplied part/list-of-tables report does not expose a full project-level snapshot table with project code and all required source fields.",
#         })
#         document.close()
#         return extracted, source_audit, {"pages_scanned": document_page_count, "pages_selected": 0, "fallback_pages": 0}
#     sector = None
#     layout = None
#     for number in pages:
#         page = document[number - 1]
#         words = page.get_text("words")
#         layout = page_layout(words) or layout
#         if layout is None:
#             source_audit.append({
#                 "Source_PDF": pdf_path.name, "Source_Page": number, "Project_ID": None,
#                 "Snapshot_Date": snapshot_display, "Extraction_Method": "layout_detection",
#                 "Confidence": 0.0, "Disposition": "review", "Validation_Issues": "missing_table_column_geometry",
#                 "Raw_Excerpt": None,
#             })
#             continue
#         page_records, sector = extract_page_records(words, page.rect.height, snapshot_display, snapshot_iso, sector, layout)
#         for row in page_records:
#             issues = record_issues(row)
#             confidence = round(max(0.0, 1.0 - 0.13 * len(issues) - (0.08 if not row["Sector"] else 0)), 2)
#             disposition = "accepted" if not issues else "accepted_with_warning"
#             source_audit.append({
#                 "Source_PDF": pdf_path.name, "Source_Page": number, "Project_ID": row["Project_ID"],
#                 "Snapshot_Date": snapshot_display, "Extraction_Method": "pymupdf_coordinate_reconstruction",
#                 "Confidence": confidence, "Disposition": disposition,
#                 "Validation_Issues": ";".join(issues) if issues else None,
#                 "Raw_Excerpt": None,
#             })
#             extracted.append((row, source_audit[-1]))
#     document.close()
#     return extracted, source_audit, {"pages_scanned": document_page_count, "pages_selected": len(pages), "fallback_pages": 0}


# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--input-dir", required=True, type=Path)
#     parser.add_argument("--sample", required=True, type=Path)
#     parser.add_argument("--output-dir", required=True, type=Path)
#     args = parser.parse_args()
#     args.output_dir.mkdir(parents=True, exist_ok=True)
#     sample_schema = read_sample_schema(args.sample)
#     if sample_schema != SCHEMA:
#         raise ValueError("The hard-coded target schema does not exactly match the supplied sample CSV")

#     all_rows, audits, report_stats = [], [], []
#     for pdf_path in sorted(args.input_dir.glob("*.pdf")):
#         records, source_audit, stats = process_pdf(pdf_path)
#         audits.extend(source_audit)
#         all_rows.extend(records)
#         report_stats.append({"PDF": pdf_path.name, **stats, "candidate_records": len(records)})

#     # Duplicates are never silently overwritten. Keep first source order as accepted and
#     # send every repeated observation to review with exact source-page provenance.
#     seen = set()
#     accepted_rows = []
#     for row, audit in all_rows:
#         key = (row["Project_ID"], row["Snapshot_Date"])
#         if key in seen:
#             audit["Disposition"] = "review"
#             audit["Validation_Issues"] = ";".join(filter(None, [audit["Validation_Issues"], "duplicate_project_id_snapshot"]))
#         else:
#             seen.add(key)
#             accepted_rows.append(row)

#     final = pd.DataFrame(accepted_rows, columns=SCHEMA)
#     if not final.empty:
#         final["Project_ID"] = final["Project_ID"].astype("string")
#         final["_sort_date"] = pd.to_datetime(final["Snapshot_Date"], format="%m/%d/%Y", errors="coerce")
#         final = final.sort_values(["Project_ID", "_sort_date"], kind="stable").drop(columns="_sort_date")
#     final = final.reindex(columns=SCHEMA)
#     final.to_csv(args.output_dir / "PAIMANA_TimeSeries_Final.csv", index=False, encoding="utf-8")
#     final.to_parquet(args.output_dir / "PAIMANA_TimeSeries_Final.parquet", index=False)

#     audit_df = pd.DataFrame(audits, columns=[
#         "Source_PDF", "Source_Page", "Project_ID", "Snapshot_Date", "Extraction_Method",
#         "Confidence", "Disposition", "Validation_Issues", "Raw_Excerpt",
#     ])
#     audit_df.to_csv(args.output_dir / "extraction_audit.csv", index=False, encoding="utf-8")
#     audit_df.loc[audit_df["Disposition"].eq("review")].to_csv(args.output_dir / "review_queue.csv", index=False, encoding="utf-8")
#     pd.DataFrame(report_stats).to_csv(args.output_dir / "processing_summary.csv", index=False, encoding="utf-8")

#     summary = {
#         "pdfs_processed": len(report_stats),
#         "pages_scanned": sum(x["pages_scanned"] for x in report_stats),
#         "project_rows_extracted": len(final),
#         "unique_project_ids": final["Project_ID"].nunique() if not final.empty else 0,
#         "duplicate_monthly_records": int((audit_df["Validation_Issues"].fillna("").str.contains("duplicate_project_id_snapshot")).sum()),
#         "milestone_records_found": int(final["Has_Milestones"].eq("Yes").sum()) if not final.empty else 0,
#         "delay_reasons_found": int(final["Delay_Reason"].notna().sum()) if not final.empty else 0,
#         "rows_requiring_review": int(audit_df["Disposition"].eq("review").sum()),
#         "pages_requiring_fallback": sum(x["fallback_pages"] for x in report_stats),
#         "accepted_with_warning": int(audit_df["Disposition"].eq("accepted_with_warning").sum()),
#         "accepted": int(audit_df["Disposition"].eq("accepted").sum()),
#     }
#     pd.Series(summary).to_json(args.output_dir / "validation_summary.json", indent=2)
#     print(pd.Series(summary).to_string())


# if __name__ == "__main__":
#     main()
