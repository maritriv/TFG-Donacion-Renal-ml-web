import { requireRole } from "../auth-guard.js";
import { auth, db } from "../../firebase-config.js";
import {
  doc,
  serverTimestamp,
  setDoc
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const API_URL = "http://127.0.0.1:8001/predict";

const form = document.getElementById("prediction-form");
const btnBack = document.getElementById("btn-back");
const formTitle = document.getElementById("form-title");

const params = new URLSearchParams(window.location.search);
const mode = params.get("mode") || "transfer";
const isMid = mode === "mid";

// ===================== COEFICIENTES REGLAS CLÍNICAS =====================

const COEFS_MITAD = {
  intercepto: 7.5,
  capnometria: 0.03701583,
  edad: -0.0510799,
  sexoFemenino: -0.82780951,
  causaCardiaca: -0.50187099,
  cardioManual: -2.0621372,
  recuperacion: 1.29618296,
  corte: 5.6071538
};

const COEFS_AFTER = {
  intercepto: 7.5,
  edad: -0.0959,
  sexoFemenino: -1.1558,
  capnometria: 0.0807,
  causaCardiaca: -0.5245,
  cardioManual: -2.6349,
  recuperacion: 2.8971,
  tiempoLlegadaInicioPcrMin: -0.0003,
  corte: 4.625
};

// ===================== HELPERS =====================

function generatePredictionId() {
  return `pred_v5_${Date.now()}_${crypto.randomUUID()}`;
}

function getNumber(id) {
  const value = document.getElementById(id).value;
  return Number(value);
}

function getStringFromSelect(id) {
  const select = document.getElementById(id);
  return select.options[select.selectedIndex].text;
}

function getFormValues() {
  const edad = getNumber("edad");
  const sexo = getNumber("sexo");
  const imc = getNumber("imc");
  const grupoSanguineo = getNumber("grupo-sanguineo");
  const capnometria = getNumber("capnometria");
  const adrenalina = getNumber("adrenalina");
  const colesterol = getNumber("colesterol");
  const causaCardiaca = getNumber("causa-cardiaca");
  const cardioManual = getNumber("cardio-manual");
  const recuperacion = getNumber("recuperacion");

  return {
    edad,
    sexo,
    imc,
    grupoSanguineo,
    capnometria,
    adrenalina,
    colesterol,
    causaCardiaca,
    cardioManual,
    recuperacion,

    sexoLabel: getStringFromSelect("sexo"),
    grupoSanguineoLabel: getStringFromSelect("grupo-sanguineo"),
    colesterolLabel: getStringFromSelect("colesterol"),
    causaCardiacaLabel: getStringFromSelect("causa-cardiaca"),
    cardioManualLabel: getStringFromSelect("cardio-manual"),
    recuperacionLabel: getStringFromSelect("recuperacion")
  };
}

function validateValues(values) {
  if (!Number.isFinite(values.edad)) {
    throw new Error("Edad obligatoria.");
  }

  if (!Number.isFinite(values.capnometria)) {
    throw new Error("Capnometría obligatoria.");
  }

  if (!Number.isFinite(values.imc)) {
    throw new Error("IMC obligatorio para el modelo de aprendizaje automático.");
  }

  if (!Number.isFinite(values.adrenalina)) {
    throw new Error("Número de dosis de adrenalina obligatorio para el modelo de aprendizaje automático.");
  }
}

// ===================== FEATURES PARA ML =====================

function buildMLFeatures(values) {
  if (isMid) {
    return {
      EDAD: values.edad,
      SEXO: values.sexo,
      IMC: values.imc,
      GRUPO_SANGUINEO: values.grupoSanguineo,
      CAUSA_FALLECIMIENTO_DANC: values.causaCardiaca,
      CARDIOCOMPRESION_EXTRAHOSPITALARIA: values.cardioManual,
      RECUPERACION_ALGUN_MOMENTO: values.recuperacion,
      ADRENALINA_N: values.adrenalina,
      COLESTEROL: values.colesterol,
      CAPNOMETRIA_MEDIO: values.capnometria,
      CAPNOMETRIA_MEDIO_MISSING: 0,
      ADRENALINA_N_MISSING: 0
    };
  }

  return {
    EDAD: values.edad,
    SEXO: values.sexo,
    IMC: values.imc,
    GRUPO_SANGUINEO: values.grupoSanguineo,
    CAUSA_FALLECIMIENTO_DANC: values.causaCardiaca,
    CARDIOCOMPRESION_EXTRAHOSPITALARIA: values.cardioManual,
    RECUPERACION_ALGUN_MOMENTO: values.recuperacion,
    ADRENALINA_N: values.adrenalina,
    COLESTEROL: values.colesterol,
    CAPNOMETRIA_TRANSFERENCIA: values.capnometria,
    CAPNOMETRIA_TRANSFERENCIA_MISSING: 0,
    ADRENALINA_N_MISSING: 0
  };
}

// ===================== MODELO BASADO EN REGLAS =====================

function calculateRulesPrediction(values) {
  let indice;
  let corte;

  if (isMid) {
    const c = COEFS_MITAD;

    indice =
      c.intercepto +
      values.capnometria * c.capnometria +
      values.edad * c.edad +
      values.sexo * c.sexoFemenino +
      values.causaCardiaca * c.causaCardiaca +
      values.cardioManual * c.cardioManual +
      values.recuperacion * c.recuperacion;

    corte = c.corte;
  } else {
    const c = COEFS_AFTER;
    const tiempoMin = 0;

    indice =
      c.intercepto +
      values.edad * c.edad +
      values.sexo * c.sexoFemenino +
      values.capnometria * c.capnometria +
      values.causaCardiaca * c.causaCardiaca +
      values.cardioManual * c.cardioManual +
      values.recuperacion * c.recuperacion +
      tiempoMin * c.tiempoLlegadaInicioPcrMin;

    corte = c.corte;
  }

  return {
    esValido: indice >= corte,
    indice,
    corte
  };
}

// ===================== BACKEND ML =====================

async function callMLBackend(features) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      mode,
      features
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Error llamando al backend de ML.");
  }

  return response.json();
}

// ===================== FIREBASE =====================

async function savePredictionToFirebase(predictionId, values, rulesResult, mlResult, mlFeatures) {
  const user = auth.currentUser;

  const predictionMode = isMid ? "MID_RCP" : "AFTER_RCP";
  const momentoLegible = isMid
    ? "Mitad del procedimiento de RCP (20 min)"
    : "Después del procedimiento de RCP";

  const commonPrediction = {
    id: predictionId,
    source: "web",

    uid_medico: user?.uid || null,
    nombre_medico: user?.displayName || null,

    prediction_mode: predictionMode,
    momento_prediccion_legible: momentoLegible,

    edad: String(values.edad),
    femenino: values.sexoLabel,
    capnometria: String(values.capnometria),
    causa_cardiaca: values.causaCardiacaLabel,
    cardio_manual: values.cardioManualLabel,
    rec_pulso: values.recuperacionLabel,

    indice: Number(rulesResult.indice.toFixed(4)),
    valido: rulesResult.esValido ? "Si" : "No",

    fecha: serverTimestamp()
  };

  const extendedPrediction = {
    ...commonPrediction,

    has_ml_prediction: true,

    input_rules: {
      edad: values.edad,
      femenino: values.sexo,
      capnometria: values.capnometria,
      causa_cardiaca: values.causaCardiaca,
      cardio_manual: values.cardioManual,
      rec_pulso: values.recuperacion
    },

    input_ml: mlFeatures,

    ml_result: {
      prediction: mlResult.prediction,
      label: mlResult.prediction_label,
      label_legible: mlResult.prediction === 1 ? "Si" : "No",
      probability: mlResult.probability
    },

    model_info: {
      dataset: mode,
      model: "logistic_regression",
      version_modelo: isMid
        ? "v1_mid_logistic_regression_real_seed_999"
        : "v1_transfer_logistic_regression_real_plus_synthetic_seed_999",
      experiment: isMid ? "real" : "real_plus_synthetic",
      seed: 999
    }
  };

  await setDoc(doc(db, "predicciones", predictionId), commonPrediction);
  await setDoc(doc(db, "predicciones_ml", predictionId), extendedPrediction);
}

// ===================== SESSION RESULT =====================

function saveResultInSession(predictionId, values, rulesResult, mlResult, mlFeatures) {
  sessionStorage.setItem(
    "lastPredictionResult",
    JSON.stringify({
      prediction_id: predictionId,
      mode,
      input_values: values,
      ml_features: mlFeatures,
      rules_result: {
        es_valido: rulesResult.esValido,
        indice: rulesResult.indice,
        corte: rulesResult.corte
      },
      ml_result: {
        prediction: mlResult.prediction,
        label: mlResult.prediction_label,
        probability: mlResult.probability
      }
    })
  );
}

// ===================== INIT =====================

requireRole("Médico", async () => {
  formTitle.textContent = isMid
    ? "Formulario · Punto medio"
    : "Formulario · Transferencia";

  const capInput = document.getElementById("capnometria");
  if (capInput) {
    capInput.placeholder = isMid
      ? "Capnometría (mejor valor a los 20 min)"
      : "Capnometría (transferencia)";
  }

  if (btnBack) {
    btnBack.addEventListener("click", () => {
      window.location.href = "../../html/prediction-mode.html";
    });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
      const values = getFormValues();
      validateValues(values);

      const mlFeatures = buildMLFeatures(values);
      const rulesResult = calculateRulesPrediction(values);
      const mlResult = await callMLBackend(mlFeatures);

      const predictionId = generatePredictionId();

      await savePredictionToFirebase(
        predictionId,
        values,
        rulesResult,
        mlResult,
        mlFeatures
      );

      saveResultInSession(
        predictionId,
        values,
        rulesResult,
        mlResult,
        mlFeatures
      );

      window.location.href = "../../html/prediction-result.html";
    } catch (error) {
      console.error(error);
      alert(error.message);
    }
  });
});