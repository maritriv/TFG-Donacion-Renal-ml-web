from pathlib import Path
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Renal Donor Prediction API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MID_MODEL_PATH = PROJECT_ROOT / "outputs" / "final_model_export" / "mid" / "final_model.joblib"
TRANSFER_MODEL_PATH = PROJECT_ROOT / "outputs" / "final_model_export" / "transfer" / "final_model.joblib"

mid_model = joblib.load(MID_MODEL_PATH)
transfer_model = joblib.load(TRANSFER_MODEL_PATH)

MID_FEATURES = [
    "EDAD",
    "SEXO",
    "IMC",
    "GRUPO_SANGUINEO",
    "CAUSA_FALLECIMIENTO_DANC",
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "ADRENALINA_N",
    "COLESTEROL",
    "CAPNOMETRIA_MEDIO",
    "CAPNOMETRIA_MEDIO_MISSING",
    "ADRENALINA_N_MISSING",
]

TRANSFER_FEATURES = [
    "EDAD",
    "SEXO",
    "IMC",
    "GRUPO_SANGUINEO",
    "CAUSA_FALLECIMIENTO_DANC",
    "CARDIOCOMPRESION_EXTRAHOSPITALARIA",
    "RECUPERACION_ALGUN_MOMENTO",
    "ADRENALINA_N",
    "COLESTEROL",
    "CAPNOMETRIA_TRANSFERENCIA",
    "CAPNOMETRIA_TRANSFERENCIA_MISSING",
    "ADRENALINA_N_MISSING",
]


class PredictionRequest(BaseModel):
    mode: str
    features: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(request: PredictionRequest):
    mode = request.mode.lower()

    if mode == "mid":
        model = mid_model
        feature_order = MID_FEATURES
    elif mode == "transfer":
        model = transfer_model
        feature_order = TRANSFER_FEATURES
    else:
        raise HTTPException(status_code=400, detail="Modo no válido. Usa 'mid' o 'transfer'.")

    try:
        row = {feature: request.features.get(feature) for feature in feature_order}
        df = pd.DataFrame([row], columns=feature_order)

        pred = int(model.predict(df)[0])

        probability = None
        if hasattr(model, "predict_proba"):
            probability = float(model.predict_proba(df)[0][1])

        return {
            "mode": mode,
            "prediction": pred,
            "prediction_label": "valido" if pred == 1 else "no_valido",
            "probability": probability,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error durante la predicción: {exc}")