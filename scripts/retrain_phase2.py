import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path("d:/SIH project")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.phase2 import train_phase2

def check_regression(old_metrics, new_metrics):
    for model in ["cost_model", "schedule_model"]:
        old_auc = old_metrics[model]["summary_mean_std"]["roc_auc"][0]
        new_auc = new_metrics[model]["summary_mean_std"]["roc_auc"][0]
        
        # We consider a regression to be a drop in AUC of more than 0.02
        if new_auc < old_auc - 0.02:
            return True, f"{model} AUC regressed from {old_auc:.3f} to {new_auc:.3f}"
    return False, "No regression detected"

def main():
    model_dir = ROOT / "models" / "paimana_phase2"
    old_metrics_path = model_dir / "model_metrics.json"
    
    if old_metrics_path.exists():
        with open(old_metrics_path) as f:
            old_metrics = json.load(f)
    else:
        old_metrics = None

    with TemporaryDirectory() as tempdir:
        temp_path = Path(tempdir)
        print(f"Running training pipeline in temporary directory: {temp_path}")
        
        try:
            result = train_phase2(
                completed_path=ROOT / "data" / "processed" / "completed_cleaned.csv",
                ongoing_path=ROOT / "data" / "processed" / "ongoing_cleaned.csv",
                artifact_dir=temp_path,
                output_path=temp_path / "ongoing_risk_predictions.csv"
            )
        except Exception as e:
            print(f"Training failed: {e}")
            return
            
        if old_metrics:
            regressed, reason = check_regression(old_metrics, result["model_metrics"])
            if regressed:
                print(f"Model promotion rejected: {reason}")
                return
            print("Model comparison passed. Promoting new models.")
        else:
            print("No existing models found. Promoting new models.")
            
        # Promote artifacts
        model_dir.mkdir(parents=True, exist_ok=True)
        for p in temp_path.glob("*"):
            if p.suffix in {".pkl", ".json"}:
                shutil.copy2(p, model_dir / p.name)
        print("Models successfully updated.")

if __name__ == "__main__":
    main()
