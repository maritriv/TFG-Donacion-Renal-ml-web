from pathlib import Path
import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MID_MODEL_PATH = PROJECT_ROOT / "outputs" / "final_model_export" / "mid" / "final_model.joblib"
TRANSFER_MODEL_PATH = PROJECT_ROOT / "outputs" / "final_model_export" / "transfer" / "final_model.joblib"

mid_model = joblib.load(MID_MODEL_PATH)
transfer_model = joblib.load(TRANSFER_MODEL_PATH)