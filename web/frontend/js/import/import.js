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

function to01(value) {
  const v = normalize(value);

  if (["1", "si", "sí", "true"].includes(v)) return 1;
  if (["0", "no", "false"].includes(v)) return 0;

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
  const header = parseCsvLine(lines[0], separator).map((h) => h.trim());

  const columnAliases = {
    edad: ["Edad"],
    sexo: ["Sexo", "Femenino"],
    capnometria: ["Capnometria", "Capnometría"],
    causa: ["Causa_cardiaca", "Causa cardíaca", "Causa_cardiaca"],
    cardio: ["Cardiocompresion", "Cardiocompresión", "Cardio_manual"],
    rec: ["Recuperacion_pulso", "Rec. del pulso", "Recuperación_pulso"],
    mode: ["Prediction_mode"]
  };

  function indexOfAny(names) {
    return header.findIndex((h) =>
      names.some((name) => normalize(h) === normalize(name))
    );
  }

  const idxEdad = indexOfAny(columnAliases.edad);
  const idxFem = indexOfAny(columnAliases.sexo);
  const idxCap = indexOfAny(columnAliases.capnometria);
  const idxCausa = indexOfAny(columnAliases.causa);
  const idxCardio = indexOfAny(columnAliases.cardio);
  const idxRec = indexOfAny(columnAliases.rec);
  const idxMode = indexOfAny(columnAliases.mode);

  const missing = [];

  if (idxEdad === -1) missing.push("Edad");
  if (idxFem === -1) missing.push("Sexo/Femenino");
  if (idxCap === -1) missing.push("Capnometria");
  if (idxCausa === -1) missing.push("Causa_cardiaca");
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

    const edad = Number(cols[idxEdad]);
    const capno = Number(cols[idxCap]);
    const fem = femeninoTo01(cols[idxFem]);
    const cardio = cardioTo01(cols[idxCardio]);
    const rec = to01(cols[idxRec]);
    const causa = to01(cols[idxCausa]);
    const mode = parseMode(cols[idxMode]);

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
      edad,
      capno,
      fem,
      cardio,
      rec,
      causa,
      mode
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

  snapshot.docs.forEach((documentSnapshot) => {
    const data = documentSnapshot.data();

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
    if (uniqueByCsv.has(item.dupKey)) {
      duplicatesInCsv++;
    } else {
      uniqueByCsv.set(item.dupKey, item);
    }
  });

  const uniqueRows = [...uniqueByCsv.values()];
  const toImport = [];
  let duplicatesInFirestore = 0;

  uniqueRows.forEach((item) => {
    if (existingKeys.has(item.dupKey)) {
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

      indice: Number(item.rulesResult.indice.toFixed(4)),
      valido: item.validoTxt,

      fecha: serverTimestamp(),

      has_ml_prediction: false,
      importado_csv: true
    };

    const ref = doc(db, "predicciones", predictionId);

    await runTransaction(db, async (tx) => {
      const snap = await tx.get(ref);

      if (!snap.exists()) {
        tx.set(ref, prediction);
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