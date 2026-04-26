import { requireRole } from "../auth-guard.js";
import { auth, db } from "../../firebase-config.js";
import {
  doc,
  getDoc
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const comparisonMessage = document.getElementById("comparison-message");

const rulesIcon = document.getElementById("rules-icon");
const rulesLabel = document.getElementById("rules-label");
const rulesIndex = document.getElementById("rules-index");

const mlIcon = document.getElementById("ml-icon");
const mlLabel = document.getElementById("ml-label");
const mlProbability = document.getElementById("ml-probability");

const btnBackMain = document.getElementById("btn-back-main");
const btnDownloadPdf = document.getElementById("btn-download-pdf");

function resultText(isValid) {
  return isValid ? "DONANTE VÁLIDO" : "DONANTE NO VÁLIDO";
}

function getResultIcon(isValid) {
  if (isValid) {
    return `
      <svg viewBox="0 0 24 24" class="result-svg-icon">
        <path
          d="M5,13 L10,18 L19,7"
          fill="none"
          stroke="#042939"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    `;
  }

  return `
    <svg viewBox="0 0 24 24" class="result-svg-icon">
      <path
        d="M19,6.41L17.59,5 12,10.59 6.41,5 5,6.41 10.59,12 5,17.59 6.41,19 12,13.41 17.59,19 19,17.59 13.41,12z"
        fill="#042939"
      />
    </svg>
  `;
}

function paintResult(iconElement, isValid) {
  iconElement.innerHTML = getResultIcon(isValid);
}

function formatProbability(probability) {
  if (probability === null || probability === undefined) {
    return "Probabilidad no disponible";
  }

  return `Probabilidad de válido: ${(probability * 100).toFixed(2)}%`;
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

function formatDateDisplay() {
  return new Date().toLocaleString("es-ES");
}

function getMomentLabel(mode) {
  return mode === "mid"
    ? "Mitad del procedimiento de RCP (20 min)"
    : "Después del procedimiento de RCP";
}

function getSexLabel(value) {
  return value === "Mujer" ? "Femenino" : "Masculino";
}

function getMLModelInfo(data) {
  const isMid = data.mode === "mid";

  return {
    dataset: isMid ? "mid" : "transfer",
    model: "logistic_regression",
    experiment: isMid ? "real" : "real_plus_synthetic",
    seed: 999,
    version: isMid
      ? "v1_mid_logistic_regression_real_seed_999"
      : "v1_transfer_logistic_regression_real_plus_synthetic_seed_999"
  };
}

async function getDoctorName() {
  const user = auth.currentUser;

  if (!user) {
    return "Profesional sanitario";
  }

  try {
    const userRef = doc(db, "users", user.uid);
    const userSnap = await getDoc(userRef);

    if (!userSnap.exists()) {
      return user.displayName || "Profesional sanitario";
    }

    const userData = userSnap.data();

    const name = userData.name || "";
    const lastname = userData.lastname || "";
    const fullName = `${name} ${lastname}`.trim();

    return fullName || user.displayName || "Profesional sanitario";
  } catch (error) {
    console.error("Error cargando nombre del médico:", error);
    return user.displayName || "Profesional sanitario";
  }
}

function generatePredictionPdf(data) {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();

  const values = data.input_values;
  const rules = data.rules_result;
  const ml = data.ml_result;
  const modelInfo = getMLModelInfo(data);

  const doctorName = data.doctor_name || "Profesional sanitario";

  const rulesValid = Boolean(rules.es_valido);
  const mlValid = Number(ml.prediction) === 1;

  const fileDate = formatDateForFile();
  const displayDate = formatDateDisplay();
  const fileName = `Reporte_${fileDate}_${cleanFileName(doctorName)}.pdf`;

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
    checkNewPage(20);
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
    pdf.text(`${label}: ${value ?? "—"}`, 20, y);
    y += 7;
  }

  function addWrappedLine(label, value) {
    checkNewPage(18);
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(11);

    const text = `${label}: ${value ?? "—"}`;
    const lines = pdf.splitTextToSize(text, 170);

    pdf.text(lines, 20, y);
    y += lines.length * 7;
  }

  addTitle("RESULTADOS DE LA PREDICCIÓN DE DONANTE DE RIÑÓN");

  addSectionTitle("DATOS DEL PROFESIONAL SANITARIO RESPONSABLE");
  addLine("Nombre del profesional sanitario responsable", doctorName);
  addLine("Fecha y hora de la predicción", displayDate);

  addSectionTitle("DATOS DEL POSIBLE DONANTE");
  addLine("Momento de la predicción", getMomentLabel(data.mode));
  addLine("Edad", `${values.edad} años`);
  addLine("Sexo", getSexLabel(values.sexoLabel));
  addLine(
    data.mode === "mid"
      ? "Capnometría (mejor valor a los 20 min)"
      : "Capnometría (transferencia)",
    values.capnometria
  );
  addLine("IMC", values.imc);
  addLine("Grupo sanguíneo", values.grupoSanguineoLabel);
  addLine("Número de dosis de adrenalina", values.adrenalina);
  addLine("Colesterol", values.colesterolLabel);
  addLine("Causa principal del evento", values.causaCardiacaLabel === "Sí" ? "Cardíaca" : "No cardíaca");
  addLine("Cardiocompresión extrahospitalaria", values.cardioManualLabel);
  addLine("Recuperación de la circulación", values.recuperacionLabel);

  addSectionTitle("RESULTADO DEL MODELO BASADO EN REGLAS CLÍNICAS");
  addLine("Resultado", rulesValid ? "DONANTE VÁLIDO" : "DONANTE NO VÁLIDO");
  addLine("Índice calculado", Number(rules.indice).toFixed(4));
  addLine("Umbral de decisión", Number(rules.corte).toFixed(4));

  addSectionTitle("RESULTADO DEL MODELO DE APRENDIZAJE AUTOMÁTICO");
  addLine("Resultado", mlValid ? "DONANTE VÁLIDO" : "DONANTE NO VÁLIDO");
  addLine(
    "Probabilidad de donante válido",
    ml.probability !== null && ml.probability !== undefined
      ? `${(ml.probability * 100).toFixed(2)}%`
      : "No disponible"
  );

  addSectionTitle("INFORMACIÓN DEL MODELO DE APRENDIZAJE AUTOMÁTICO");
  addLine("Dataset", modelInfo.dataset);
  addLine("Modelo", modelInfo.model);
  addLine("Experimento", modelInfo.experiment);
  addLine("Semilla", modelInfo.seed);
  addWrappedLine("Versión del modelo", modelInfo.version);

  checkNewPage(35);
  addSectionTitle("COMPARACIÓN ENTRE MODELOS");
  addLine(
    "Coincidencia",
    rulesValid === mlValid
      ? "Ambos modelos coinciden en la predicción"
      : "Los modelos no coinciden en la predicción"
  );

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

requireRole("Médico", async () => {
  const rawData = sessionStorage.getItem("lastPredictionResult");

  if (!rawData) {
    alert("No se han encontrado resultados de predicción.");
    window.location.href = "../../html/medico.html";
    return;
  }

  const data = JSON.parse(rawData);

  const rulesIsValid = Boolean(data.rules_result.es_valido);
  const mlIsValid = Number(data.ml_result.prediction) === 1;

  paintResult(rulesIcon, rulesIsValid);
  paintResult(mlIcon, mlIsValid);

  rulesLabel.textContent = resultText(rulesIsValid);
  rulesIndex.textContent = `Índice: ${Number(data.rules_result.indice).toFixed(4)}`;

  mlLabel.textContent = resultText(mlIsValid);
  mlProbability.textContent = formatProbability(data.ml_result.probability);

  if (rulesIsValid === mlIsValid) {
    comparisonMessage.textContent = "Ambos modelos coinciden en la predicción.";
    comparisonMessage.classList.add("match");
  } else {
    comparisonMessage.textContent = "Los modelos no coinciden en la predicción.";
    comparisonMessage.classList.add("mismatch");
  }

  btnBackMain.addEventListener("click", () => {
    window.location.href = "../../html/medico.html";
  });

  btnDownloadPdf.addEventListener("click", async () => {
    const doctorName = await getDoctorName();

    generatePredictionPdf({
      ...data,
      doctor_name: doctorName
    });
  });
});