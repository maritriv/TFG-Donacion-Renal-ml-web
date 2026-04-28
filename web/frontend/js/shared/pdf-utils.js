function dash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function isDash(value) {
  return value === null || value === undefined || value === "" || value === "—";
}

function mapSexoPdf(value) {
  if (value === "Mujer" || value === "Si" || value === "Sí") return "Femenino";
  if (value === "Hombre" || value === "No") return "Masculino";
  return dash(value);
}

function mapGrupoSanguineo(value) {
  if (isDash(value)) return "—";

  const normalized = String(value).trim().toUpperCase();

  if (["A", "B", "AB", "O"].includes(normalized)) return normalized;

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
  if (
    probability === null ||
    probability === undefined ||
    Number.isNaN(Number(probability))
  ) {
    return "No disponible";
  }

  return `${(Number(probability) * 100).toFixed(2)}%`;
}

function modeToLabel(mode, fallback) {
  if (mode === "MID_RCP") return "Mitad del procedimiento de RCP (20 min)";
  if (mode === "AFTER_RCP") return "Transferencia hospitalaria";
  return fallback || "—";
}

export function generatePredictionPdfFromHistorial(basePrediction, mlPrediction = null) {
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

  const isValidRules =
    basePrediction.valido === "Si" || basePrediction.valido === "Sí";

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
    const mlValid =
      Number(mlResult.prediction) === 1 || mlResult.label_legible === "Si";

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

export async function downloadPredictionPdf(prediction) {
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