import { requireRole } from "../auth-guard.js";
import { auth, db } from "../../firebase-config.js";
import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const btnBack = document.getElementById("btn-back");
const historialTitle = document.getElementById("historial-title");
const historialCount = document.getElementById("historial-count");
const historialEmpty = document.getElementById("historial-empty");
const tableBody = document.getElementById("historial-table-body");

const btnSort = document.getElementById("btn-sort");
const sortModalOverlay = document.getElementById("sort-modal-overlay");
const sortSelect = document.getElementById("sort-select");
const btnSortCancel = document.getElementById("btn-sort-cancel");
const btnSortApply = document.getElementById("btn-sort-apply");

let currentPredictions = [];

const btnFilter = document.getElementById("btn-filter");
const filterModalOverlay = document.getElementById("filter-modal-overlay");

const filterEdadMin = document.getElementById("filter-edad-min");
const filterEdadMax = document.getElementById("filter-edad-max");
const filterSexo = document.getElementById("filter-sexo");
const filterCapnoMin = document.getElementById("filter-capno-min");
const filterCapnoMax = document.getElementById("filter-capno-max");
const filterCausa = document.getElementById("filter-causa");
const filterCardio = document.getElementById("filter-cardio");
const filterRec = document.getElementById("filter-rec");
const filterResultado = document.getElementById("filter-resultado");
const filterImcMin = document.getElementById("filter-imc-min");
const filterImcMax = document.getElementById("filter-imc-max");
const filterGrupo = document.getElementById("filter-grupo");
const filterAdrenalinaMin = document.getElementById("filter-adrenalina-min");
const filterAdrenalinaMax = document.getElementById("filter-adrenalina-max");
const filterColesterol = document.getElementById("filter-colesterol");

const btnFilterClear = document.getElementById("btn-filter-clear");
const btnFilterCancel = document.getElementById("btn-filter-cancel");
const btnFilterApply = document.getElementById("btn-filter-apply");

let allPredictions = [];

const btnExport = document.getElementById("btn-export");

let displayedPredictions = [];

const params = new URLSearchParams(window.location.search);
const scope = params.get("scope") || "medico";

// ===================== HELPERS =====================

function dash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function isDash(value) {
  return value === null || value === undefined || value === "" || value === "—";
}

function mapSexo(value) {
  if (value === "Mujer" || value === "Si" || value === "Sí") return "Mujer";
  if (value === "Hombre" || value === "No") return "Hombre";
  return dash(value);
}

function mapSexoPdf(value) {
  if (value === "Mujer" || value === "Si" || value === "Sí") return "Femenino";
  if (value === "Hombre" || value === "No") return "Masculino";
  return dash(value);
}

function mapResultado(value) {
  return value === "Si" || value === "Sí" ? "Válido" : "No válido";
}

function mapGrupoSanguineo(value) {
  if (isDash(value)) return "—";

  const normalized = String(value).trim().toUpperCase();

  if (["A", "B", "AB", "O"].includes(normalized)) {
    return normalized;
  }

  const map = {
    "0": "A",
    "1": "B",
    "2": "AB",
    "3": "O"
  };

  return map[normalized] ?? "—";
}

function mapColesterol(value) {
  if (isDash(value)) return "—";

  const normalized = String(value).trim();

  if (normalized === "0") return "No";
  if (normalized === "1") return "Sí";

  return value;
}

function formatIndice(value) {
  if (isDash(value)) return "—";
  return Number(value).toFixed(3);
}

function modeToLabel(mode, fallback) {
  if (mode === "MID_RCP") return "Mitad del procedimiento de RCP (20 min)";
  if (mode === "AFTER_RCP") return "Después del procedimiento de RCP";
  return fallback || "—";
}

function getExtraValue(prediction, keyInputValues, keyInputMl) {
  const ml = prediction.ml_prediction;

  if (!ml) return "—";

  const inputValues = ml.input_values || {};
  const inputMl = ml.input_ml || {};

  return dash(inputValues[keyInputValues] ?? inputMl[keyInputMl]);
}

function cleanFileName(value) {
  return String(value || "Medico")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9_ ]/g, "")
    .trim()
    .replace(/\s+/g, "_") || "Medico";
}

function formatDateForFile() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");

  return `${pad(now.getDate())}-${pad(now.getMonth() + 1)}-${now.getFullYear()}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
}

function formatDateDisplay(timestamp) {
  if (timestamp?.toDate) return timestamp.toDate().toLocaleString("es-ES");
  return new Date().toLocaleString("es-ES");
}

function safePercent(probability) {
  if (probability === null || probability === undefined || Number.isNaN(Number(probability))) {
    return "No disponible";
  }

  return `${(Number(probability) * 100).toFixed(2)}%`;
}

// ===================== SORT =====================

function getSortValue(prediction, sortBy) {
  if (sortBy === "edad") {
    return dash(prediction.edad);
  }

  if (sortBy === "capnometria") {
    return dash(prediction.capnometria);
  }

  if (sortBy === "momento") {
    return modeToLabel(
      prediction.prediction_mode,
      prediction.momento_prediccion_legible
    );
  }

  if (sortBy === "indice") {
    return dash(prediction.indice);
  }

  if (sortBy === "imc") {
    return getExtraValue(prediction, "imc", "IMC");
  }

  if (sortBy === "adrenalina") {
    return getExtraValue(prediction, "adrenalina", "ADRENALINA_N");
  }

  return "—";
}

function normalizeValue(value) {
  if (isDash(value)) return null;

  const number = Number(value);
  if (Number.isFinite(number)) return number;

  return String(value).toLowerCase();
}

function sortPredictions(predictions, sortBy) {
  return [...predictions].sort((a, b) => {
    const rawA = getSortValue(a, sortBy);
    const rawB = getSortValue(b, sortBy);

    const dashA = isDash(rawA);
    const dashB = isDash(rawB);

    if (dashA && !dashB) return 1;
    if (!dashA && dashB) return -1;
    if (dashA && dashB) return 0;

    const valueA = normalizeValue(rawA);
    const valueB = normalizeValue(rawB);

    if (typeof valueA === "number" && typeof valueB === "number") {
      return valueA - valueB;
    }

    return String(valueA).localeCompare(String(valueB), "es");
  });
}

function openSortModal() {
  if (sortModalOverlay) {
    sortModalOverlay.hidden = false;
  }
}

function closeSortModal() {
  if (sortModalOverlay) {
    sortModalOverlay.hidden = true;
  }
}

// ===================== DOCTOR NAME =====================

async function getDoctorNameByUid(uid, fallback = "Profesional sanitario") {
  if (!uid) return fallback;

  try {
    const userRef = doc(db, "users", uid);
    const userSnap = await getDoc(userRef);

    if (!userSnap.exists()) return fallback;

    const userData = userSnap.data();
    const name = userData.name || "";
    const lastname = userData.lastname || "";
    const fullName = `${name} ${lastname}`.trim();

    return fullName || fallback;
  } catch (error) {
    console.error("Error cargando nombre del médico:", error);
    return fallback;
  }
}

// ===================== PDF =====================

function generatePredictionPdfFromHistorial(basePrediction, mlPrediction = null) {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();

  const doctorName =
    basePrediction.nombre_medico_pdf ||
    basePrediction.nombre_medico ||
    "Profesional sanitario";

  const fileName = `Reporte_${formatDateForFile()}_${cleanFileName(doctorName)}.pdf`;

  let y = 20;

  function checkNewPage(extraSpace = 20) {
    if (y + extraSpace > 280) {
      pdf.addPage();
      y = 20;
    }
  }

  function addTitle(text) {
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(16);
    pdf.text(text, 105, y, { align: "center" });
    y += 12;
  }

  function addSectionTitle(text) {
    checkNewPage(18);
    y += 5;
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(12);
    pdf.text(text, 20, y);
    y += 8;
  }

  function addLine(label, value) {
    checkNewPage(10);
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(11);
    pdf.text(`${label}: ${dash(value)}`, 20, y);
    y += 7;
  }

  function addWrappedLine(label, value) {
    checkNewPage(18);
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(11);

    const text = `${label}: ${dash(value)}`;
    const lines = pdf.splitTextToSize(text, 170);

    pdf.text(lines, 20, y);
    y += lines.length * 7;
  }

  const momento = modeToLabel(
    basePrediction.prediction_mode,
    basePrediction.momento_prediccion_legible
  );

  const isValidRules = basePrediction.valido === "Si" || basePrediction.valido === "Sí";

  addTitle("RESULTADOS DE LA PREDICCIÓN DE DONANTE DE RIÑÓN");

  addSectionTitle("DATOS DEL PROFESIONAL SANITARIO RESPONSABLE");
  addLine("Nombre del profesional sanitario responsable", doctorName);
  addLine("Fecha y hora de la predicción", formatDateDisplay(basePrediction.fecha));

  addSectionTitle("DATOS DEL POSIBLE DONANTE");
  addLine("Momento de la predicción", momento);
  addLine("Edad", `${dash(basePrediction.edad)} años`);
  addLine("Sexo", mapSexoPdf(basePrediction.femenino));

  const capLabel =
    basePrediction.prediction_mode === "MID_RCP"
      ? "Capnometría (mejor valor a los 20 min)"
      : "Capnometría (transferencia)";

  addLine(capLabel, basePrediction.capnometria);
  addLine("Causa principal del evento", basePrediction.causa_cardiaca);
  addLine("Cardiocompresión extrahospitalaria", basePrediction.cardio_manual);
  addLine("Recuperación de la circulación", basePrediction.rec_pulso);

  if (mlPrediction?.input_values || mlPrediction?.input_ml) {
    const input = mlPrediction.input_values || {};
    const inputML = mlPrediction.input_ml || {};

    addLine("IMC", input.imc ?? inputML.IMC);
    addLine(
      "Grupo sanguíneo",
      mapGrupoSanguineo(input.grupoSanguineoLabel ?? inputML.GRUPO_SANGUINEO)
    );
    addLine("Número de dosis de adrenalina", input.adrenalina ?? inputML.ADRENALINA_N);
    addLine("Colesterol", mapColesterol(input.colesterolLabel ?? inputML.COLESTEROL));
  }

  addSectionTitle("RESULTADO DEL MODELO BASADO EN REGLAS CLÍNICAS");
  addLine("Resultado", isValidRules ? "DONANTE VÁLIDO" : "DONANTE NO VÁLIDO");
  addLine("Índice calculado", formatIndice(basePrediction.indice));

  if (mlPrediction) {
    const mlResult = mlPrediction.ml_result || {};
    const modelInfo = mlPrediction.model_info || {};
    const mlValid = Number(mlResult.prediction) === 1 || mlResult.label_legible === "Si";

    addSectionTitle("RESULTADO DEL MODELO DE APRENDIZAJE AUTOMÁTICO");
    addLine("Resultado", mlValid ? "DONANTE VÁLIDO" : "DONANTE NO VÁLIDO");
    addLine("Probabilidad de donante válido", safePercent(mlResult.probability));

    addSectionTitle("INFORMACIÓN DEL MODELO DE APRENDIZAJE AUTOMÁTICO");
    addLine("Dataset", modelInfo.dataset);
    addLine("Modelo", modelInfo.model);
    addLine("Experimento", modelInfo.experiment);
    addLine("Semilla", modelInfo.seed);
    addWrappedLine("Versión del modelo", modelInfo.version_modelo);

    addSectionTitle("COMPARACIÓN ENTRE MODELOS");
    addLine(
      "Coincidencia",
      isValidRules === mlValid
        ? "Ambos modelos coinciden en la predicción"
        : "Los modelos no coinciden en la predicción"
    );
  } else {
    addSectionTitle("MODELO DE APRENDIZAJE AUTOMÁTICO");
    addWrappedLine(
      "Información",
      "Esta predicción fue generada desde la aplicación móvil o desde una versión anterior, por lo que no dispone de resultado del modelo de aprendizaje automático."
    );
  }

  y += 8;
  checkNewPage(25);
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(11);
  pdf.text(
    "Nota: los resultados tienen finalidad académica y de apoyo a la decisión, y no sustituyen la valoración médica.",
    20,
    y,
    { maxWidth: 170 }
  );

  pdf.save(fileName);
}

async function downloadPredictionPdf(prediction) {
  try {
    generatePredictionPdfFromHistorial(
      prediction,
      prediction.ml_prediction || null
    );
  } catch (error) {
    console.error(error);
    alert("Error generando el PDF de la predicción.");
  }
}

// ===================== TABLE =====================

function renderPredictions(predictions) {
  displayedPredictions = predictions;

  tableBody.innerHTML = "";
  historialCount.textContent = `Mostrando ${predictions.length} filas`;

  if (predictions.length === 0) {
    historialEmpty.hidden = false;
    return;
  }

  historialEmpty.hidden = true;

  predictions.forEach((prediction, index) => {
    const row = document.createElement("tr");

    const momento = modeToLabel(
      prediction.prediction_mode,
      prediction.momento_prediccion_legible
    );

    const imc = getExtraValue(prediction, "imc", "IMC");
    const grupo = mapGrupoSanguineo(
      getExtraValue(prediction, "grupoSanguineoLabel", "GRUPO_SANGUINEO")
    );
    const adrenalina = getExtraValue(prediction, "adrenalina", "ADRENALINA_N");
    const colesterol = mapColesterol(
      getExtraValue(prediction, "colesterolLabel", "COLESTEROL")
    );

    row.innerHTML = `
      <td>${index + 1}</td>
      <td>${dash(prediction.edad)}</td>
      <td>${mapSexo(prediction.femenino)}</td>
      <td>${dash(prediction.capnometria)}</td>
      <td>${dash(prediction.causa_cardiaca)}</td>
      <td>${dash(prediction.cardio_manual)}</td>
      <td>${dash(prediction.rec_pulso)}</td>
      <td>${momento}</td>
      <td>${imc}</td>
      <td>${grupo}</td>
      <td>${adrenalina}</td>
      <td>${colesterol}</td>
      <td>${mapResultado(prediction.valido)}</td>
      <td>${formatIndice(prediction.indice)}</td>
      <td>
        <button type="button" class="historial-pdf-btn" data-index="${index}">
          PDF
        </button>
      </td>
    `;

    tableBody.appendChild(row);
  });

  document.querySelectorAll(".historial-pdf-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const prediction = predictions[Number(button.dataset.index)];
      await downloadPredictionPdf(prediction);
    });
  });
}

// ===================== FIREBASE =====================

async function loadMlPredictionsById() {
  const snapshot = await getDocs(collection(db, "predicciones_ml"));
  const map = new Map();

  snapshot.docs.forEach((documentSnapshot) => {
    map.set(documentSnapshot.id, {
      id: documentSnapshot.id,
      ...documentSnapshot.data()
    });
  });

  return map;
}

async function loadPredictions() {
  const user = auth.currentUser;

  if (!user) {
    alert("Usuario no autenticado.");
    window.location.href = "../../html/index.html";
    return;
  }

  let predictionsQuery;

  if (scope === "admin") {
    historialTitle.textContent = "HISTORIAL GLOBAL DE PREDICCIONES";
    predictionsQuery = query(collection(db, "predicciones"));
  } else {
    historialTitle.textContent = "HISTORIAL PREDICCIONES";
    predictionsQuery = query(
      collection(db, "predicciones"),
      where("uid_medico", "==", user.uid)
    );
  }

  const [snapshot, mlMap] = await Promise.all([
    getDocs(predictionsQuery),
    loadMlPredictionsById()
  ]);

  const predictions = await Promise.all(
    snapshot.docs.map(async (documentSnapshot) => {
        const basePrediction = {
            id: documentSnapshot.id,
            ...documentSnapshot.data()
        };

        const fallbackName =
            basePrediction.nombre_medico ||
            auth.currentUser?.displayName ||
            "Profesional sanitario";

        const doctorName = await getDoctorNameByUid(
            basePrediction.uid_medico,
            fallbackName
            );

        return {
            ...basePrediction,
            nombre_medico_pdf: doctorName,
            ml_prediction: mlMap.get(documentSnapshot.id) || null
        };
    })
  );

  predictions.sort((a, b) => {
    const dateA = a.fecha?.toMillis?.() || 0;
    const dateB = b.fecha?.toMillis?.() || 0;
    return dateB - dateA;
  });

  allPredictions = predictions;
  currentPredictions = predictions;
  renderPredictions(predictions);
}

// ===================== INIT =====================

const requiredRole = scope === "admin" ? "Administrador" : "Médico";

requireRole(requiredRole, async () => {
  if (btnBack) {
    btnBack.addEventListener("click", () => {
        window.location.href = "../../html/medico.html";
    });
  }

  if (btnSort) {
    btnSort.addEventListener("click", openSortModal);
  }

  if (btnSortCancel) {
    btnSortCancel.addEventListener("click", closeSortModal);
  }

  if (btnSortApply) {
    btnSortApply.addEventListener("click", () => {
      const sortedPredictions = sortPredictions(currentPredictions, sortSelect.value);
      currentPredictions = sortedPredictions;
      renderPredictions(sortedPredictions);
      closeSortModal();
    });
  }

  if (btnFilter) {
    btnFilter.addEventListener("click", openFilterModal);
  }

  if (btnFilterCancel) {
    btnFilterCancel.addEventListener("click", closeFilterModal);
  }

  if (btnFilterApply) {
    btnFilterApply.addEventListener("click", applyFilters);
  }

  if (btnFilterClear) {
    btnFilterClear.addEventListener("click", clearFilters);
  }

  if (btnExport) {
    btnExport.addEventListener("click", () => {
        exportPredictionsCsv(displayedPredictions);
    });
  }

  await loadPredictions();
});

function openFilterModal() {
  filterModalOverlay.hidden = false;
}

function closeFilterModal() {
  filterModalOverlay.hidden = true;
}

function toNumberOrNull(value) {
  if (value === null || value === undefined || value === "") return null;

  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalizeSiNo(value) {
  if (value === "Sí") return "Si";
  return value || "";
}

function matchesRange(value, min, max) {
  const numericValue = toNumberOrNull(value);

  if (numericValue === null) return false;
  if (min !== null && numericValue < min) return false;
  if (max !== null && numericValue > max) return false;

  return true;
}

function predictionMatchesFilters(prediction) {
  const edadMin = toNumberOrNull(filterEdadMin.value);
  const edadMax = toNumberOrNull(filterEdadMax.value);
  const capnoMin = toNumberOrNull(filterCapnoMin.value);
  const capnoMax = toNumberOrNull(filterCapnoMax.value);
  const imcMin = toNumberOrNull(filterImcMin.value);
  const imcMax = toNumberOrNull(filterImcMax.value);
  const adrenalinaMin = toNumberOrNull(filterAdrenalinaMin.value);
  const adrenalinaMax = toNumberOrNull(filterAdrenalinaMax.value);

  const imc = getExtraValue(prediction, "imc", "IMC");
  const grupo = mapGrupoSanguineo(
    getExtraValue(prediction, "grupoSanguineoLabel", "GRUPO_SANGUINEO")
  );
  const adrenalina = getExtraValue(prediction, "adrenalina", "ADRENALINA_N");
  const colesterol = mapColesterol(
    getExtraValue(prediction, "colesterolLabel", "COLESTEROL")
  );

if ((imcMin !== null || imcMax !== null) && !matchesRange(imc, imcMin, imcMax)) {
  return false;
}

if (filterGrupo.value && grupo !== filterGrupo.value) {
  return false;
}

if ((adrenalinaMin !== null || adrenalinaMax !== null) && !matchesRange(adrenalina, adrenalinaMin, adrenalinaMax)) {
  return false;
}

if (filterColesterol.value && colesterol !== filterColesterol.value) {
  return false;
}

  if ((edadMin !== null || edadMax !== null) && !matchesRange(prediction.edad, edadMin, edadMax)) {
    return false;
  }

  if (filterSexo.value && mapSexo(prediction.femenino) !== filterSexo.value) {
    return false;
  }

  if ((capnoMin !== null || capnoMax !== null) && !matchesRange(prediction.capnometria, capnoMin, capnoMax)) {
    return false;
  }

  if (filterCausa.value && normalizeSiNo(prediction.causa_cardiaca) !== filterCausa.value) {
    return false;
  }

  if (filterCardio.value && prediction.cardio_manual !== filterCardio.value) {
    return false;
  }

  if (filterRec.value && normalizeSiNo(prediction.rec_pulso) !== filterRec.value) {
    return false;
  }

  if (filterResultado.value && normalizeSiNo(prediction.valido) !== filterResultado.value) {
    return false;
  }

  return true;
}

function applyFilters() {
  const filteredPredictions = allPredictions.filter(predictionMatchesFilters);

  currentPredictions = filteredPredictions;
  renderPredictions(filteredPredictions);
  closeFilterModal();
}

function clearFilters() {
  filterEdadMin.value = "";
  filterEdadMax.value = "";
  filterSexo.value = "";
  filterCapnoMin.value = "";
  filterCapnoMax.value = "";
  filterCausa.value = "";
  filterCardio.value = "";
  filterRec.value = "";
  filterResultado.value = "";
  filterImcMin.value = "";
  filterImcMax.value = "";
  filterGrupo.value = "";
  filterAdrenalinaMin.value = "";
  filterAdrenalinaMax.value = "";
  filterColesterol.value = "";

  currentPredictions = allPredictions;
  renderPredictions(allPredictions);
  closeFilterModal();
}

function stripAccents(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function csvValue(value) {
  const raw = stripAccents(value)
    .replace(/\r/g, " ")
    .replace(/\n/g, " ")
    .trim();

  if (raw.includes(",") || raw.includes('"')) {
    return `"${raw.replace(/"/g, '""')}"`;
  }

  return raw;
}

function formatCsvDate(timestamp) {
  if (timestamp?.toDate) {
    return timestamp.toDate().toLocaleString("es-ES");
  }

  return "";
}

function getMlPredictionLabel(mlPrediction) {
  if (!mlPrediction?.ml_result) return "—";

  const mlResult = mlPrediction.ml_result;
  const isValid = Number(mlResult.prediction) === 1 || mlResult.label_legible === "Si";

  return isValid ? "Valido" : "No valido";
}

function exportPredictionsCsv(predictions) {
  if (!predictions.length) {
    alert("No hay predicciones para exportar.");
    return;
  }

  const headers = [
    "ID",
    "Edad",
    "Femenino",
    "Capnometria",
    "Causa_cardiaca",
    "Cardio_manual",
    "Recuperacion_pulso",
    "Prediction_mode",
    "Momento",
    "IMC",
    "Grupo_sanguineo",
    "Adrenalina",
    "Colesterol",
    "Resultado_reglas",
    "Indice",
    "Resultado_ML",
    "Probabilidad_ML",
    "ML_dataset",
    "ML_modelo",
    "ML_experimento",
    "ML_seed",
    "ML_version",
    "UID_medico",
    "Nombre_medico",
    "Fecha"
  ];

  const rows = predictions.map((prediction) => {
    const mlPrediction = prediction.ml_prediction || null;
    const inputValues = mlPrediction?.input_values || {};
    const inputMl = mlPrediction?.input_ml || {};
    const mlResult = mlPrediction?.ml_result || {};
    const modelInfo = mlPrediction?.model_info || {};

    const momento = modeToLabel(
      prediction.prediction_mode,
      prediction.momento_prediccion_legible
    );

    const imc = inputValues.imc ?? inputMl.IMC ?? "";
    const grupo = mapGrupoSanguineo(
      inputValues.grupoSanguineoLabel ?? inputMl.GRUPO_SANGUINEO
    );
    const adrenalina = inputValues.adrenalina ?? inputMl.ADRENALINA_N ?? "";
    const colesterol = mapColesterol(
      inputValues.colesterolLabel ?? inputMl.COLESTEROL
    );

    const probability =
      mlResult.probability !== null && mlResult.probability !== undefined
        ? Number(mlResult.probability).toFixed(4)
        : "";

    return [
      prediction.id,
      prediction.edad,
      prediction.femenino,
      prediction.capnometria,
      prediction.causa_cardiaca,
      prediction.cardio_manual,
      prediction.rec_pulso,
      prediction.prediction_mode,
      momento,
      imc,
      grupo,
      adrenalina,
      colesterol,
      mapResultado(prediction.valido),
      formatIndice(prediction.indice),
      getMlPredictionLabel(mlPrediction),
      probability,
      modelInfo.dataset,
      modelInfo.model,
      modelInfo.experiment,
      modelInfo.seed,
      modelInfo.version_modelo,
      prediction.uid_medico,
      prediction.nombre_medico_pdf || prediction.nombre_medico,
      formatCsvDate(prediction.fecha)
    ].map(csvValue).join(",");
  });

  const csvContent = [headers.join(","), ...rows].join("\n");

  const blob = new Blob(["\uFEFF" + csvContent], {
    type: "text/csv;charset=utf-8;"
  });

  const url = URL.createObjectURL(blob);

  const now = new Date();
  let fileName;

  if (scope === "admin") {
    fileName = `predicciones_globales_${formatDateForFile()}.csv`;
  } else {
    const doctorName =
        predictions[0]?.nombre_medico_pdf ||
        predictions[0]?.nombre_medico ||
        "medico";

    fileName = `predicciones_${cleanFileName(doctorName)}_${formatDateForFile()}.csv`;
  }

  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

