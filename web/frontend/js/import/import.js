import { requireRole } from "../auth-guard.js";
import { auth, db } from "../../firebase-config.js";
import {
  collection,
  doc,
  getDocs,
  increment,
  query,
  runTransaction,
  serverTimestamp,
  setDoc,
  where
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const filePickerArea = document.getElementById("file-picker-area");
const csvInput = document.getElementById("csv-input");
const fileName = document.getElementById("file-name");
const btnClearFile = document.getElementById("btn-clear-file");
const btnAddPredictions = document.getElementById("btn-add-predictions");
const btnHelp = document.getElementById("btn-help");
const btnBackMain = document.getElementById("btn-back-main");

const progressWrapper = document.getElementById("import-progress-wrapper");
const progressBar = document.getElementById("import-progress-bar");

const helpOverlay = document.getElementById("csv-help-overlay");
const btnHelpOk = document.getElementById("btn-help-ok");

const duplicateOverlay = document.getElementById("duplicate-overlay");
const duplicateTitle = document.getElementById("duplicate-title");
const duplicateMessage = document.getElementById("duplicate-message");
const btnDuplicateCancel = document.getElementById("btn-duplicate-cancel");
const btnDuplicateConfirm = document.getElementById("btn-duplicate-confirm");

let rowsReady = [];
let selectedFile = null;
let pendingImportRows = [];

// ===================== COEFICIENTES =====================

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

function normalize(value) {
  return String(value ?? "")
    .replace(/^\uFEFF/, "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function toast(message) {
  alert(message);
}

function modeToLabel(mode) {
  if (mode === "MID_RCP") return "Mitad del procedimiento de RCP (20 min)";
  if (mode === "AFTER_RCP") return "Después del procedimiento de RCP";
  return "—";
}

function sexoLabel(fem01) {
  return fem01 === 1 ? "Si" : "No";
}

function cardioLabel(cardio01) {
  return cardio01 === 1 ? "Manual" : "Mecánica";
}

function yesNoLabel(value01) {
  return value01 === 1 ? "Si" : "No";
}

function yesNoLabelAccent(value01) {
  return value01 === 1 ? "Sí" : "No";
}

function to01(value) {
  const v = normalize(value);

  if (["1", "si", "sí", "true", "valido", "válido"].includes(v)) return 1;
  if (["0", "no", "false", "no valido", "no válido"].includes(v)) return 0;

  const number = Number(value);
  return Number.isInteger(number) && (number === 0 || number === 1)
    ? number
    : null;
}

function femeninoTo01(value) {
  const v = normalize(value);

  if (["si", "sí", "1", "true", "mujer", "femenino", "m"].includes(v)) return 1;
  if (["no", "0", "false", "hombre", "masculino", "h"].includes(v)) return 0;

  return null;
}

function cardioTo01(value) {
  const v = normalize(value);

  if (["manual", "1", "si", "sí", "true"].includes(v)) return 1;
  if (["mecanica", "mecánica", "0", "no", "false"].includes(v)) return 0;

  return null;
}

function parseMode(value) {
  const raw = String(value ?? "").trim().toUpperCase();

  if (raw === "MID_RCP") return "MID_RCP";
  if (raw === "AFTER_RCP") return "AFTER_RCP";

  const loose = normalize(value);

  if (loose.includes("mitad") || loose.includes("20")) return "MID_RCP";
  if (loose.includes("despues") || loose.includes("transferencia")) return "AFTER_RCP";

  return null;
}

function toNumberOrNull(value) {
  const raw = String(value ?? "").trim();

  if (!raw || raw === "—") return null;

  const number = Number(raw.replace(",", "."));
  return Number.isFinite(number) ? number : null;
}

function parseGrupoSanguineo(value) {
  const v = normalize(value).toUpperCase();

  if (v === "A" || v === "0") return { code: 0, label: "A" };
  if (v === "B" || v === "1") return { code: 1, label: "B" };
  if (v === "AB" || v === "2") return { code: 2, label: "AB" };
  if (v === "O" || v === "3") return { code: 3, label: "O" };

  return { code: null, label: "" };
}

function causaLabelFromCode(code, fallback = "") {
  const map = {
    0: "Desconocido",
    1: "TEP",
    2: "Arritmia",
    3: "Cardiopatía isquémica",
    4: "Tóxicos",
    5: "Muerte súbita",
    6: "Otras"
  };

  return map[Number(code)] || fallback || "";
}

function causaCardiacaFromCodigo(code) {
  return [2, 3, 5].includes(Number(code)) ? 1 : 0;
}

function parseCsvLine(line, separator) {
  const result = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const next = line[i + 1];

    if (char === '"' && next === '"') {
      current += '"';
      i++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === separator && !inQuotes) {
      result.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }

  result.push(current.trim());
  return result;
}

function buildDupKey({
  uidMedico,
  mode,
  edad,
  femenino,
  capnometria,
  causaCardiaca,
  cardioManual,
  recPulso,
  valido
}) {
  return [
    uidMedico,
    mode,
    edad,
    femenino,
    capnometria,
    causaCardiaca,
    cardioManual,
    recPulso,
    valido
  ].map(normalize).join("|");
}

function generateImportPredictionId(row, validoTxt) {
  const raw = [
    "import",
    row.mode,
    row.edad,
    row.capno,
    row.fem,
    row.causa,
    row.cardio,
    row.rec,
    validoTxt,
    Date.now(),
    crypto.randomUUID()
  ].join("_");

  return raw.replace(/[^A-Za-z0-9_-]/g, "_");
}

// ===================== REGLAS CLÍNICAS =====================

function calculateRulesPrediction(row) {
  let indice;
  let corte;

  if (row.mode === "MID_RCP") {
    const c = COEFS_MITAD;

    indice =
      c.intercepto +
      row.capno * c.capnometria +
      row.edad * c.edad +
      row.fem * c.sexoFemenino +
      row.causa * c.causaCardiaca +
      row.cardio * c.cardioManual +
      row.rec * c.recuperacion;

    corte = c.corte;
  } else {
    const c = COEFS_AFTER;
    const tiempoMin = 0;

    indice =
      c.intercepto +
      row.edad * c.edad +
      row.fem * c.sexoFemenino +
      row.capno * c.capnometria +
      row.causa * c.causaCardiaca +
      row.cardio * c.cardioManual +
      row.rec * c.recuperacion +
      tiempoMin * c.tiempoLlegadaInicioPcrMin;

    corte = c.corte;
  }

  return {
    esValido: indice >= corte,
    indice,
    corte
  };
}

// ===================== UI =====================

function resetUI() {
  rowsReady = [];
  selectedFile = null;
  pendingImportRows = [];

  csvInput.value = "";
  fileName.textContent = "Selecciona un archivo CSV...";
  btnClearFile.hidden = true;

  btnAddPredictions.hidden = true;
  btnAddPredictions.disabled = true;
  btnAddPredictions.textContent = "AÑADIR FILAS";

  progressWrapper.hidden = true;
  progressBar.style.width = "0%";
}

function startImportUI() {
  progressWrapper.hidden = false;
  progressBar.style.width = "0%";

  btnAddPredictions.disabled = true;
  filePickerArea.style.pointerEvents = "none";
  btnClearFile.disabled = true;
}

function finishImportUI() {
  progressWrapper.hidden = true;
  filePickerArea.style.pointerEvents = "auto";
  btnClearFile.disabled = false;
  btnAddPredictions.disabled = rowsReady.length === 0;
}

function setProgress(done, total) {
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);
  progressBar.style.width = `${percent}%`;
}

function showHelp() {
  helpOverlay.hidden = false;
}

function hideHelp() {
  helpOverlay.hidden = true;
}

function showDuplicateDialog(totalDuplicates, toImportCount) {
  duplicateTitle.textContent = "Filas duplicadas detectadas";
  duplicateMessage.textContent =
    `Hay ${totalDuplicates} filas duplicadas que NO se importarán. ` +
    `¿Deseas importar el resto (${toImportCount} filas)?`;

  duplicateOverlay.hidden = false;
}

function hideDuplicateDialog() {
  duplicateOverlay.hidden = true;
}

// ===================== CSV =====================

async function validateAndParseCsv(file) {
  rowsReady = [];

  const text = await file.text();
  const lines = text
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length === 0) {
    throw new Error("CSV inválido: archivo vacío.");
  }

  const separator = lines[0].includes(";") && !lines[0].includes(",") ? ";" : ",";
  const header = parseCsvLine(lines[0], separator).map((h) =>
    h.replace(/^\uFEFF/, "").trim()
  );

  const columnAliases = {
    id: ["ID"],
    edad: ["Edad"],
    sexo: ["Sexo", "Femenino"],
    capnometria: ["Capnometria", "Capnometría"],
    causa: ["Causa_cardiaca", "Causa cardíaca", "Causa_cardiaca_reglas"],
    causaCodigo: ["Causa_fallecimiento_codigo"],
    causaLabel: ["Causa_fallecimiento"],
    cardio: ["Cardiocompresion", "Cardiocompresión", "Cardio_manual"],
    rec: ["Recuperacion_pulso", "Rec. del pulso", "Recuperación_pulso"],
    mode: ["Prediction_mode"],
    imc: ["IMC"],
    grupo: ["Grupo_sanguineo", "Grupo sanguíneo"],
    adrenalina: ["Adrenalina"],
    hta: ["HTA"],
    diabetes: ["Diabetes"],
    tabaco: ["Tabaco"],
    colesterol: ["Colesterol"],
    alcohol: ["Alcohol"],
    resultadoMl: ["Resultado_ML"],
    probabilidadMl: ["Probabilidad_ML"],
    mlDataset: ["ML_dataset"],
    mlModelo: ["ML_modelo"],
    mlExperimento: ["ML_experimento"],
    mlSeed: ["ML_seed"],
    mlVersion: ["ML_version"]
  };

  function indexOfAny(names) {
    return header.findIndex((h) =>
      names.some((name) => normalize(h) === normalize(name))
    );
  }

  const idxId = indexOfAny(columnAliases.id);
  const idxEdad = indexOfAny(columnAliases.edad);
  const idxFem = indexOfAny(columnAliases.sexo);
  const idxCap = indexOfAny(columnAliases.capnometria);
  const idxCausa = indexOfAny(columnAliases.causa);
  const idxCausaCodigo = indexOfAny(columnAliases.causaCodigo);
  const idxCausaLabel = indexOfAny(columnAliases.causaLabel);
  const idxCardio = indexOfAny(columnAliases.cardio);
  const idxRec = indexOfAny(columnAliases.rec);
  const idxMode = indexOfAny(columnAliases.mode);

  const idxImc = indexOfAny(columnAliases.imc);
  const idxGrupo = indexOfAny(columnAliases.grupo);
  const idxAdrenalina = indexOfAny(columnAliases.adrenalina);
  const idxHta = indexOfAny(columnAliases.hta);
  const idxDiabetes = indexOfAny(columnAliases.diabetes);
  const idxTabaco = indexOfAny(columnAliases.tabaco);
  const idxColesterol = indexOfAny(columnAliases.colesterol);
  const idxAlcohol = indexOfAny(columnAliases.alcohol);
  const idxResultadoMl = indexOfAny(columnAliases.resultadoMl);
  const idxProbabilidadMl = indexOfAny(columnAliases.probabilidadMl);
  const idxMlDataset = indexOfAny(columnAliases.mlDataset);
  const idxMlModelo = indexOfAny(columnAliases.mlModelo);
  const idxMlExperimento = indexOfAny(columnAliases.mlExperimento);
  const idxMlSeed = indexOfAny(columnAliases.mlSeed);
  const idxMlVersion = indexOfAny(columnAliases.mlVersion);

  const missing = [];

  if (idxEdad === -1) missing.push("Edad");
  if (idxFem === -1) missing.push("Sexo/Femenino");
  if (idxCap === -1) missing.push("Capnometria");
  if (idxCausa === -1 && idxCausaCodigo === -1) missing.push("Causa_cardiaca_reglas o Causa_fallecimiento_codigo");
  if (idxCardio === -1) missing.push("Cardiocompresion/Cardio_manual");
  if (idxRec === -1) missing.push("Recuperacion_pulso");
  if (idxMode === -1) missing.push("Prediction_mode");

  if (missing.length > 0) {
    throw new Error(`CSV inválido: faltan columnas: ${missing.join(", ")}`);
  }

  let invalidValues = false;
  let insufficientCols = false;

  for (const line of lines.slice(1)) {
    const cols = parseCsvLine(line, separator);

    if (cols.length < header.length) {
      insufficientCols = true;
      continue;
    }

    const get = (index) => index === -1 ? "" : cols[index];

    const edad = Number(get(idxEdad));
    const capno = Number(get(idxCap));
    const fem = femeninoTo01(get(idxFem));
    const cardio = cardioTo01(get(idxCardio));
    const rec = to01(get(idxRec));
    const mode = parseMode(get(idxMode));

    let causa = idxCausa !== -1 ? to01(get(idxCausa)) : null;

    const causaCodigo = idxCausaCodigo !== -1
      ? toNumberOrNull(get(idxCausaCodigo))
      : null;

    if (causa === null && causaCodigo !== null) {
      causa = causaCardiacaFromCodigo(causaCodigo);
    }

    const grupo = parseGrupoSanguineo(get(idxGrupo));

    const imc = toNumberOrNull(get(idxImc));
    const adrenalina = toNumberOrNull(get(idxAdrenalina));
    const hta = to01(get(idxHta)) ?? 0;
    const diabetes = to01(get(idxDiabetes)) ?? 0;
    const tabaco = to01(get(idxTabaco)) ?? 0;
    const colesterol = to01(get(idxColesterol)) ?? 0;
    const alcohol = to01(get(idxAlcohol)) ?? 0;

    if (
      !Number.isFinite(edad) ||
      !Number.isFinite(capno) ||
      fem === null ||
      cardio === null ||
      rec === null ||
      causa === null ||
      mode === null
    ) {
      invalidValues = true;
      continue;
    }

    rowsReady.push({
      originalId: get(idxId),

      edad,
      capno,
      fem,
      cardio,
      rec,
      causa,
      mode,

      causaCodigo,
      causaLabel: causaLabelFromCode(causaCodigo, get(idxCausaLabel)),

      imc,
      grupoCode: grupo.code,
      grupoLabel: grupo.label,
      adrenalina,
      hta,
      diabetes,
      tabaco,
      colesterol,
      alcohol,

      resultadoMl: get(idxResultadoMl),
      probabilidadMl: toNumberOrNull(get(idxProbabilidadMl)),
      mlDataset: get(idxMlDataset),
      mlModelo: get(idxMlModelo),
      mlExperimento: get(idxMlExperimento),
      mlSeed: toNumberOrNull(get(idxMlSeed)),
      mlVersion: get(idxMlVersion)
    });
  }

  if (rowsReady.length === 0 && insufficientCols) {
    throw new Error("CSV inválido: columnas insuficientes. Revisa el formato.");
  }

  if (rowsReady.length === 0 && invalidValues) {
    throw new Error("CSV inválido: valores no válidos.");
  }

  if (rowsReady.length === 0) {
    throw new Error("CSV inválido: no hay filas válidas.");
  }

  return rowsReady;
}

// ===================== FIRESTORE IMPORT =====================

async function prepareImportRows(rows) {
  const user = auth.currentUser;

  if (!user) {
    throw new Error("Usuario no autenticado.");
  }

  const snapshot = await getDocs(
    query(
      collection(db, "predicciones"),
      where("uid_medico", "==", user.uid)
    )
  );

  const existingKeys = new Set();
  const existingOriginalIds = new Set();

  snapshot.docs.forEach((documentSnapshot) => {
    const data = documentSnapshot.data();

    if (data.id) existingOriginalIds.add(data.id);
    if (data.csv_original_id) existingOriginalIds.add(data.csv_original_id);

    existingKeys.add(
      buildDupKey({
        uidMedico: data.uid_medico,
        mode: data.prediction_mode,
        edad: data.edad,
        femenino: data.femenino,
        capnometria: data.capnometria,
        causaCardiaca: data.causa_cardiaca,
        cardioManual: data.cardio_manual,
        recPulso: data.rec_pulso,
        valido: data.valido
      })
    );
  });

  const computedRows = rows.map((row) => {
    const rulesResult = calculateRulesPrediction(row);
    const validoTxt = rulesResult.esValido ? "Si" : "No";

    const femTxt = sexoLabel(row.fem);
    const cardioTxt = cardioLabel(row.cardio);
    const causaTxt = yesNoLabel(row.causa);
    const recTxt = yesNoLabel(row.rec);

    const dupKey = buildDupKey({
      uidMedico: user.uid,
      mode: row.mode,
      edad: String(row.edad),
      femenino: femTxt,
      capnometria: String(row.capno),
      causaCardiaca: causaTxt,
      cardioManual: cardioTxt,
      recPulso: recTxt,
      valido: validoTxt
    });

    return {
      row,
      rulesResult,
      validoTxt,
      femTxt,
      cardioTxt,
      causaTxt,
      recTxt,
      dupKey
    };
  });

  const uniqueByCsv = new Map();
  let duplicatesInCsv = 0;

  computedRows.forEach((item) => {
    const originalId = item.row.originalId || "";
    const csvKey = originalId ? `id:${normalize(originalId)}` : item.dupKey;

    if (uniqueByCsv.has(csvKey)) {
      duplicatesInCsv++;
    } else {
      uniqueByCsv.set(csvKey, item);
    }
  });

  const uniqueRows = [...uniqueByCsv.values()];
  const toImport = [];
  let duplicatesInFirestore = 0;

  uniqueRows.forEach((item) => {
    const originalId = item.row.originalId || "";

    const duplicatedByOriginalId =
      originalId && existingOriginalIds.has(originalId);

    const duplicatedByClinicalData =
      existingKeys.has(item.dupKey);

    if (duplicatedByOriginalId || duplicatedByClinicalData) {
      duplicatesInFirestore++;
    } else {
      toImport.push(item);
    }
  });

  return {
    toImport,
    totalDuplicates: duplicatesInCsv + duplicatesInFirestore
  };
}

function buildMlFeatures(row) {
  const base = {
    EDAD: row.edad,
    SEXO: row.fem,
    IMC: row.imc,
    GRUPO_SANGUINEO: row.grupoCode,
    CAUSA_FALLECIMIENTO_DANC: row.causaCodigo,
    CARDIOCOMPRESION_EXTRAHOSPITALARIA: row.cardio,
    RECUPERACION_ALGUN_MOMENTO: row.rec,
    ADRENALINA_N: row.adrenalina,
    HTA: row.hta,
    DIABETES: row.diabetes,
    TABACO: row.tabaco,
    COLESTEROL: row.colesterol,
    ALCOHOL: row.alcohol,
    ADRENALINA_N_MISSING: row.adrenalina === null ? 1 : 0
  };

  if (row.mode === "MID_RCP") {
    return {
      ...base,
      CAPNOMETRIA_MEDIO: row.capno,
      CAPNOMETRIA_MEDIO_MISSING: 0
    };
  }

  return {
    ...base,
    CAPNOMETRIA_TRANSFERENCIA: row.capno,
    CAPNOMETRIA_TRANSFERENCIA_MISSING: 0
  };
}

function shouldCreateMlDocument(row) {
  return (
    row.imc !== null ||
    row.grupoCode !== null ||
    row.adrenalina !== null ||
    row.resultadoMl ||
    row.probabilidadMl !== null
  );
}

async function importRowsIntoFirestore(rowsToImport) {
  const user = auth.currentUser;

  if (!user) {
    throw new Error("Usuario no autenticado.");
  }

  startImportUI();

  let processed = 0;
  let validas = 0;
  let noValidas = 0;

  for (const item of rowsToImport) {
    const predictionId = generateImportPredictionId(item.row, item.validoTxt);
    const predictionMode = item.row.mode;

    const prediction = {
      id: predictionId,
      source: "web_import",

      uid_medico: user.uid,
      nombre_medico: user.displayName || user.email || "",

      prediction_mode: predictionMode,
      momento_prediccion_legible: modeToLabel(predictionMode),

      edad: String(item.row.edad),
      femenino: item.femTxt,
      capnometria: String(item.row.capno),
      causa_cardiaca: item.causaTxt,
      cardio_manual: item.cardioTxt,
      rec_pulso: item.recTxt,

      causa_fallecimiento_danc: item.row.causaLabel || "",
      causa_fallecimiento_danc_codigo: item.row.causaCodigo ?? "",

      hta: yesNoLabel(item.row.hta),
      diabetes: yesNoLabel(item.row.diabetes),
      tabaco: yesNoLabel(item.row.tabaco),
      colesterol: yesNoLabel(item.row.colesterol),
      alcohol: yesNoLabel(item.row.alcohol),

      indice: Number(item.rulesResult.indice.toFixed(4)),
      valido: item.validoTxt,

      fecha: serverTimestamp(),

      has_ml_prediction: shouldCreateMlDocument(item.row),
      importado_csv: true,
      csv_original_id: item.row.originalId || null
    };

    const ref = doc(db, "predicciones", predictionId);

    await runTransaction(db, async (tx) => {
      const snap = await tx.get(ref);

      if (!snap.exists()) {
        tx.set(ref, prediction);

        if (shouldCreateMlDocument(item.row)) {
          const mlPrediction = {
            ...prediction,

            input_values: {
              edad: item.row.edad,
              sexo: item.row.fem,
              imc: item.row.imc,
              grupoSanguineo: item.row.grupoCode,
              capnometria: item.row.capno,
              adrenalina: item.row.adrenalina,

              hta: item.row.hta,
              diabetes: item.row.diabetes,
              tabaco: item.row.tabaco,
              colesterol: item.row.colesterol,
              alcohol: item.row.alcohol,

              causaFallecimientoDanc: item.row.causaCodigo,
              causaCardiaca: item.row.causa,
              cardioManual: item.row.cardio,
              recuperacion: item.row.rec,

              sexoLabel: item.row.fem === 1 ? "Mujer" : "Hombre",
              grupoSanguineoLabel: item.row.grupoLabel,
              htaLabel: yesNoLabelAccent(item.row.hta),
              diabetesLabel: yesNoLabelAccent(item.row.diabetes),
              tabacoLabel: yesNoLabelAccent(item.row.tabaco),
              colesterolLabel: yesNoLabelAccent(item.row.colesterol),
              alcoholLabel: yesNoLabelAccent(item.row.alcohol),
              causaFallecimientoDancLabel: item.row.causaLabel,
              causaCardiacaLabel: yesNoLabelAccent(item.row.causa),
              cardioManualLabel: item.cardioTxt,
              recuperacionLabel: yesNoLabelAccent(item.row.rec)
            },

            input_ml: buildMlFeatures(item.row),

            ml_result: {
              prediction: to01(item.row.resultadoMl),
              label: item.row.resultadoMl || "",
              label_legible: to01(item.row.resultadoMl) === 1 ? "Si" : to01(item.row.resultadoMl) === 0 ? "No" : "",
              probability: item.row.probabilidadMl
            },

            model_info: {
              dataset: item.row.mlDataset || predictionMode,
              model: item.row.mlModelo || "",
              experiment: item.row.mlExperimento || "",
              seed: item.row.mlSeed,
              version_modelo: item.row.mlVersion || ""
            }
          };

          tx.set(doc(db, "predicciones_ml", predictionId), mlPrediction);
        }
      }
    });

    if (item.rulesResult.esValido) {
      validas++;
    } else {
      noValidas++;
    }

    processed++;
    setProgress(processed, rowsToImport.length);
  }

  const total = validas + noValidas;

  if (total > 0) {
    await setDoc(
      doc(db, "users", user.uid),
      {
        numeroPredicciones: increment(total),
        predicciones_validas: increment(validas),
        predicciones_no_validas: increment(noValidas)
      },
      { merge: true }
    );
  }

  finishImportUI();
  toast(`Importación completada: ${total} filas`);
  resetUI();
}

async function handleImport() {
  if (rowsReady.length === 0) {
    toast("No hay datos válidos. Selecciona un CSV válido.");
    return;
  }

  try {
    startImportUI();

    const { toImport, totalDuplicates } = await prepareImportRows(rowsReady);

    finishImportUI();

    if (toImport.length === 0) {
      duplicateTitle.textContent = "Importación cancelada";
      duplicateMessage.textContent =
        "No es posible importar estas filas porque son filas duplicadas.";
      btnDuplicateCancel.hidden = true;
      btnDuplicateConfirm.textContent = "Entendido";

      pendingImportRows = [];
      duplicateOverlay.hidden = false;
      return;
    }

    if (totalDuplicates > 0) {
      pendingImportRows = toImport;
      btnDuplicateCancel.hidden = false;
      btnDuplicateConfirm.textContent = "Importar resto";
      showDuplicateDialog(totalDuplicates, toImport.length);
      return;
    }

    await importRowsIntoFirestore(toImport);
  } catch (error) {
    console.error(error);
    finishImportUI();
    toast(error.message || "Error al importar predicciones.");
  }
}

// ===================== INIT =====================

requireRole("Médico", async () => {
  resetUI();

  filePickerArea.addEventListener("click", (event) => {
    if (event.target === btnClearFile) return;
    csvInput.click();
  });

  csvInput.addEventListener("change", async () => {
    const file = csvInput.files?.[0];

    if (!file) return;

    try {
      selectedFile = file;
      fileName.textContent = file.name;
      btnClearFile.hidden = false;

      const rows = await validateAndParseCsv(file);

      btnAddPredictions.hidden = false;
      btnAddPredictions.disabled = false;
      btnAddPredictions.textContent = `AÑADIR ${rows.length} FILAS`;

      toast("CSV válido");
    } catch (error) {
      console.error(error);
      toast(error.message || "CSV inválido.");
      resetUI();
    }
  });

  btnClearFile.addEventListener("click", (event) => {
    event.stopPropagation();
    resetUI();
    toast("Archivo deseleccionado");
  });

  btnAddPredictions.addEventListener("click", handleImport);

  btnHelp.addEventListener("click", showHelp);
  btnHelpOk.addEventListener("click", hideHelp);

  btnBackMain.addEventListener("click", () => {
    window.location.href = "../../html/medico.html";
  });

  btnDuplicateCancel.addEventListener("click", () => {
    pendingImportRows = [];
    hideDuplicateDialog();
  });

  btnDuplicateConfirm.addEventListener("click", async () => {
    const rows = pendingImportRows;

    hideDuplicateDialog();

    if (rows.length === 0) {
      return;
    }

    pendingImportRows = [];
    await importRowsIntoFirestore(rows);
  });
});