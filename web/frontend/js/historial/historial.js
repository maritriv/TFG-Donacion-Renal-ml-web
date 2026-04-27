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

const params = new URLSearchParams(window.location.search);
const scope = params.get("scope") || "medico";

function dash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function mapSexo(value) {
  if (value === "Mujer" || value === "Si" || value === "Sí") return "M";
  if (value === "Hombre" || value === "No") return "H";
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
  if (value === null || value === undefined || value === "" || value === "—") return "—";

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
  if (value === null || value === undefined || value === "" || value === "—") return "—";

  const normalized = String(value).trim();

  if (normalized === "0") return "No";
  if (normalized === "1") return "Sí";

  return value;
}

function formatIndice(value) {
  if (value === null || value === undefined || value === "") return "—";
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
    const fallbackName =
      prediction.nombre_medico ||
      auth.currentUser?.displayName ||
      "Profesional sanitario";

    const doctorName = await getDoctorNameByUid(prediction.uid_medico, fallbackName);

    generatePredictionPdfFromHistorial(
      {
        ...prediction,
        nombre_medico_pdf: doctorName
      },
      prediction.ml_prediction || null
    );
  } catch (error) {
    console.error(error);
    alert("Error generando el PDF de la predicción.");
  }
}

function renderPredictions(predictions) {
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

  const predictions = snapshot.docs.map((documentSnapshot) => {
    const basePrediction = {
      id: documentSnapshot.id,
      ...documentSnapshot.data()
    };

    return {
      ...basePrediction,
      ml_prediction: mlMap.get(documentSnapshot.id) || null
    };
  });

  predictions.sort((a, b) => {
    const dateA = a.fecha?.toMillis?.() || 0;
    const dateB = b.fecha?.toMillis?.() || 0;
    return dateB - dateA;
  });

  renderPredictions(predictions);
}

requireRole("Médico", async () => {
  if (btnBack) {
    btnBack.addEventListener("click", () => {
      window.location.href = "../../html/medico.html";
    });
  }

  await loadPredictions();
});