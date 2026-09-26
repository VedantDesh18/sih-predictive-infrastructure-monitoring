import asyncio
import sys
from pathlib import Path
import pandas as pd

ROOT = Path("d:/SIH project")
if str(ROOT / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.db.session import async_session_factory
from app.models.project import Project
from sqlalchemy import select

async def main():
    predictions_path = ROOT / "outputs/ongoing_risk_predictions.csv"
    if not predictions_path.exists():
        print("Predictions file not found")
        return
        
    df = pd.read_csv(predictions_path)
    # Get latest prediction per project
    latest = df.sort_values(["Project_ID", "Snapshot_Date"]).groupby("Project_ID").last().reset_index()
    
    from app.models.risk_prediction import RiskPredictionHistory
    from sqlalchemy.dialects.postgresql import insert
    import datetime
    
    async with async_session_factory() as session:
        result = await session.execute(select(Project))
        projects = result.scalars().all()
        
        project_map = {p.paimana_project_id: p for p in projects}
        updated = 0
        
        for _, row in latest.iterrows():
            pid = str(row["Project_ID"])
            if pid in project_map:
                proj = project_map[pid]
                proj.ml_risk_predictions = {
                    "cost_overrun_probability": float(row["Cost_Overrun_Probability"]),
                    "schedule_overrun_probability": float(row["Schedule_Overrun_Probability"]),
                    "overall_risk_probability": float(row["Overall_Risk_Probability"]),
                    "risk_level": row["Risk_Level"]
                }
                
                import json
                thresholds_path = ROOT / "models/paimana_phase2/risk_thresholds.json"
                if thresholds_path.exists():
                    with open(thresholds_path) as f:
                        thresholds = json.load(f)["threshold_values"]
                        high_threshold = thresholds["high_max_inclusive"]
                else:
                    high_threshold = 0.647 # default fallback
                    
                ml_alerts = []
                if row["Cost_Overrun_Probability"] > high_threshold:
                    ml_alerts.append({
                        "type": "ML COST RISK WARNING",
                        "severity": row["Risk_Level"],
                        "reason": "Machine learning model predicts a critical likelihood of material cost overrun.",
                        "supporting_metric": f"Probability: {row['Cost_Overrun_Probability']:.0%}"
                    })
                if row["Schedule_Overrun_Probability"] > high_threshold:
                    ml_alerts.append({
                        "type": "ML SCHEDULE RISK WARNING",
                        "severity": row["Risk_Level"],
                        "reason": "Machine learning model predicts a critical likelihood of material schedule delay.",
                        "supporting_metric": f"Probability: {row['Schedule_Overrun_Probability']:.0%}"
                    })
                proj.ml_alerts = ml_alerts
                updated += 1

        # Now load history for all rows in the prediction file
        history_records = []
        for _, row in df.iterrows():
            snapshot_date = pd.to_datetime(row["Snapshot_Date"]).date()
            history_records.append({
                "project_id": str(row["Project_ID"]),
                "snapshot_date": snapshot_date,
                "model_version": "v1.0.0",
                "cost_probability": float(row["Cost_Overrun_Probability"]),
                "schedule_probability": float(row["Schedule_Overrun_Probability"]),
                "overall_probability": float(row["Overall_Risk_Probability"]),
                "risk_level": row["Risk_Level"]
            })
            
        if history_records:
            batch_size = 1000
            for i in range(0, len(history_records), batch_size):
                batch = history_records[i:i + batch_size]
                stmt = insert(RiskPredictionHistory).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['project_id', 'snapshot_date'],
                    set_={
                        'model_version': stmt.excluded.model_version,
                        'cost_probability': stmt.excluded.cost_probability,
                        'schedule_probability': stmt.excluded.schedule_probability,
                        'overall_probability': stmt.excluded.overall_probability,
                        'risk_level': stmt.excluded.risk_level
                    }
                )
                await session.execute(stmt)
                
        await session.commit()
        print(f"Updated {updated} projects with latest ML predictions, and loaded history for {len(history_records)} snapshots.")

if __name__ == "__main__":
    asyncio.run(main())
