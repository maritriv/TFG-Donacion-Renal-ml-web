import { requireRole } from "../auth-guard.js";
import { db } from "../../firebase-config.js";
import {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  query,
  updateDoc,
  where
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

import { downloadPredictionPdf } from "../shared/pdf-utils.js";

const page = document.querySelector(".admin-profile-page");

const btnBack = document.getElementById("btn-back");
const btnEdit = document.getElementById("btn-edit");
const btnCancelEdit = document.getElementById("btn-cancel-edit");
const btnSave = document.getElementById("btn-save");
const btnDelete = document.getElementById("btn-delete");

const statusBtn = document.getElementById("profile-status");
const roleText = document.getElementById("profile-role-text");
const roleSelect = document.getElementById("profile-role");

const inputName = document.getElementById("profile-name");
const inputLastname = document.getElementById("profile-lastname");
const inputEmail = document.getElementById("profile-email");
const inputBirthdate = document.getElementById("profile-birthdate");

const tableBody = document.getElementById("historial-table-body");
const historialCount = document.getElementById("historial-count");
const historialEmpty = document.getElementById("historial-empty");

const btnSort = document.getElementById("btn-sort");
const btnFilter = document.getElementById("btn-filter");
const btnExport = document.getElementById("btn-export");

const sortModalOverlay = document.getElementById("sort-modal-overlay");
const sortSelect = document.getElementById("sort-select");
const btnSortCancel = document.getElementById("btn-sort-cancel");
const btnSortApply = document.getElementById("btn-sort-apply");

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
let currentPredictions = [];
let displayedPredictions = [];

const modal = document.getElementById("confirm-modal");
const confirmTitle = document.getElementById("confirm-title");
const confirmMessage = document.getElementById("confirm-message");
const confirmCancel = document.getElementById("confirm-cancel");
const confirmAccept = document.getElementById("confirm-accept");

const params = new URLSearchParams(window.location.search);
const userId = params.get("userId");

let originalUser = null;
let currentActive = true;
let confirmCallback = null;

// ===================== HELPERS =====================

function dash(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function mapSexo(value) {
  if (value === "Mujer" || value === "Si" || value === "Sí") return "M";
  if (value === "Hombre" || value === "No") return "H";
  return dash(value);
}

function mapResultado(value) {
  return value === "Si" || value === "Sí" ? "Válido" : "No válido";
}

function formatIndice(value) {
  if (value === null || value === undefined || value === "") return "—";
  return Number(value).toFixed(3);
}

function modeToLabel(mode, fallback) {
  if (mode === "MID_RCP") return "Mitad del procedimiento de RCP (20 min)";
  if (mode === "AFTER_RCP") return "Transferencia hospitalaria";
  return fallback || "—";
}

function isDash(value) {
  return value === null || value === undefined || value === "" || value === "—";
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

function getExtraValue(prediction, keyInputValues, keyInputMl) {
  const ml = prediction.ml_prediction;

  if (!ml) return "—";

  const inputValues = ml.input_values || {};
  const inputMl = ml.input_ml || {};

  return dash(inputValues[keyInputValues] ?? inputMl[keyInputMl]);
}

// ===================== SORT =====================

function getSortValue(prediction, sortBy) {
  if (sortBy === "edad") return dash(prediction.edad);
  if (sortBy === "capnometria") return dash(prediction.capnometria);
  if (sortBy === "momento") {
    return modeToLabel(
      prediction.prediction_mode,
      prediction.momento_prediccion_legible
    );
  }
  if (sortBy === "indice") return dash(prediction.indice);
  if (sortBy === "imc") return getExtraValue(prediction, "imc", "IMC");
  if (sortBy === "adrenalina") return getExtraValue(prediction, "adrenalina", "ADRENALINA_N");

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
  sortModalOverlay.hidden = false;
}

function closeSortModal() {
  sortModalOverlay.hidden = true;
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
  const grupo = mapGrupoSanguineo(getExtraValue(prediction, "grupoSanguineoLabel", "GRUPO_SANGUINEO"));
  const adrenalina = getExtraValue(prediction, "adrenalina", "ADRENALINA_N");
  const colesterol = mapColesterol(getExtraValue(prediction, "colesterolLabel", "COLESTEROL"));

  if ((imcMin !== null || imcMax !== null) && !matchesRange(imc, imcMin, imcMax)) return false;
  if (filterGrupo.value && grupo !== filterGrupo.value) return false;
  if ((adrenalinaMin !== null || adrenalinaMax !== null) && !matchesRange(adrenalina, adrenalinaMin, adrenalinaMax)) return false;
  if (filterColesterol.value && colesterol !== filterColesterol.value) return false;

  if ((edadMin !== null || edadMax !== null) && !matchesRange(prediction.edad, edadMin, edadMax)) return false;
  if (filterSexo.value && mapSexo(prediction.femenino) !== filterSexo.value) return false;
  if ((capnoMin !== null || capnoMax !== null) && !matchesRange(prediction.capnometria, capnoMin, capnoMax)) return false;
  if (filterCausa.value && normalizeSiNo(prediction.causa_cardiaca) !== filterCausa.value) return false;
  if (filterCardio.value && prediction.cardio_manual !== filterCardio.value) return false;
  if (filterRec.value && normalizeSiNo(prediction.rec_pulso) !== filterRec.value) return false;
  if (filterResultado.value && normalizeSiNo(prediction.valido) !== filterResultado.value) return false;

  return true;
}

function applyFilters() {
  const filtered = allPredictions.filter(predictionMatchesFilters);
  currentPredictions = filtered;
  renderPredictions(filtered);
  closeFilterModal();
}

function clearFilters() {
  document.querySelectorAll("#filter-modal-overlay input, #filter-modal-overlay select")
    .forEach(el => el.value = "");

  currentPredictions = allPredictions;
  renderPredictions(allPredictions);
  closeFilterModal();
}

function openFilterModal() {
  filterModalOverlay.hidden = false;
}

function closeFilterModal() {
  filterModalOverlay.hidden = true;
}

function exportPredictionsCsv(predictions) {
  if (!predictions.length) {
    alert("No hay predicciones para exportar.");
    return;
  }

  const headers = ["Edad","Sexo","Capnometria","Resultado"];

  const rows = predictions.map(p => [
    p.edad,
    mapSexo(p.femenino),
    p.capnometria,
    mapResultado(p.valido)
  ].join(","));

  const csvContent = [headers.join(","), ...rows].join("\n");

  const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = "predicciones.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

// ===================== PERFIL =====================

function setStatus(active) {
  currentActive = active;
  statusBtn.textContent = active ? "Activo" : "Inactivo";
  statusBtn.classList.toggle("active", active);
  statusBtn.classList.toggle("inactive", !active);
}

function setEditMode(enabled) {
  page.classList.toggle("editing", enabled);

  [inputName, inputLastname, inputEmail, inputBirthdate].forEach((input) => {
    input.disabled = !enabled;
    input.classList.toggle("editing", enabled);
  });

  roleSelect.disabled = !enabled;
  roleSelect.classList.toggle("editing", enabled);
}

function fillUser(user) {
  originalUser = { ...user };

  inputName.value = user.name || "";
  inputLastname.value = user.lastname || "";
  inputEmail.value = user.email || "";
  inputBirthdate.value = user.birthdate || "";

  roleText.textContent = user.role || "Médico";
  roleSelect.value = user.role || "Médico";

  setStatus(user.active !== false);
}

function getCurrentData() {
  return {
    name: inputName.value.trim(),
    lastname: inputLastname.value.trim(),
    email: inputEmail.value.trim(),
    birthdate: inputBirthdate.value.trim(),
    role: roleSelect.value,
    active: currentActive
  };
}

function hasChanges() {
  if (!originalUser) return false;

  const current = getCurrentData();

  return (
    current.name !== (originalUser.name || "") ||
    current.lastname !== (originalUser.lastname || "") ||
    current.email !== (originalUser.email || "") ||
    current.birthdate !== (originalUser.birthdate || "") ||
    current.role !== (originalUser.role || "Médico") ||
    current.active !== (originalUser.active !== false)
  );
}

async function loadUser() {
  if (!userId) {
    alert("Usuario no válido.");
    window.location.href = "../../html/admin-users.html";
    return;
  }

  const snap = await getDoc(doc(db, "users", userId));

  if (!snap.exists()) {
    alert("Usuario no encontrado.");
    window.location.href = "../../html/admin-users.html";
    return;
  }

  fillUser(snap.data());
}

async function saveChanges() {
  const data = getCurrentData();

  await updateDoc(doc(db, "users", userId), data);

  roleText.textContent = data.role;
  originalUser = { ...data };

  setEditMode(false);
  alert("Cambios guardados.");
}

async function deleteUser() {
  await deleteDoc(doc(db, "users", userId));
  alert("Usuario eliminado.");
  window.location.href = "../../html/admin-users.html";
}

// ===================== PREDICCIONES =====================

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

async function loadDoctorPredictions() {
  if (!tableBody || !historialCount || !historialEmpty) return;

  const predictionsQuery = query(
    collection(db, "predicciones"),
    where("uid_medico", "==", userId)
  );

  const [snapshot, mlMap] = await Promise.all([
    getDocs(predictionsQuery),
    loadMlPredictionsById()
  ]);

  const doctorName = `${inputName.value} ${inputLastname.value}`.trim();

  const predictions = snapshot.docs.map((docSnap) => ({
    id: docSnap.id,
    ...docSnap.data(),
    nombre_medico_pdf: doctorName || "Profesional sanitario",
    nombre_medico: doctorName || "Profesional sanitario",
    ml_prediction: mlMap.get(docSnap.id) || null
  }));

  predictions.sort((a, b) => {
    const dateA = a.fecha?.toMillis?.() || 0;
    const dateB = b.fecha?.toMillis?.() || 0;
    return dateB - dateA;
  });

  allPredictions = predictions;
  currentPredictions = predictions;
  renderPredictions(predictions);
}

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

// ===================== MODAL =====================

function openConfirm(title, message, onAccept, acceptText = "Aceptar") {
  confirmTitle.textContent = title;
  confirmMessage.textContent = message;
  confirmAccept.textContent = acceptText;
  confirmCallback = onAccept;
  modal.hidden = false;
}

function closeConfirm() {
  modal.hidden = true;
  confirmCallback = null;
}

// ===================== EVENTS =====================

btnBack.addEventListener("click", () => {
  window.location.href = "../../html/admin-users.html";
});

btnEdit.addEventListener("click", () => {
  setEditMode(true);
});

btnCancelEdit.addEventListener("click", () => {
  if (hasChanges()) {
    openConfirm(
      "Descartar cambios",
      "¿Estás seguro de que quieres descartar los cambios realizados?",
      () => {
        fillUser(originalUser);
        setEditMode(false);
        closeConfirm();
      },
      "Descartar"
    );
    return;
  }

  fillUser(originalUser);
  setEditMode(false);
});

statusBtn.addEventListener("click", () => {
  if (!page.classList.contains("editing")) return;
  setStatus(!currentActive);
});

btnSave.addEventListener("click", async () => {
  try {
    await saveChanges();
  } catch (error) {
    console.error(error);
    alert("Error al guardar cambios.");
  }
});

btnDelete.addEventListener("click", () => {
  openConfirm(
    "Eliminar usuario",
    "¿Estás seguro de que quieres eliminar a este usuario?",
    async () => {
      closeConfirm();

      try {
        await deleteUser();
      } catch (error) {
        console.error(error);
        alert("Error al eliminar usuario.");
      }
    },
    "Eliminar"
  );
});

confirmCancel.addEventListener("click", closeConfirm);

confirmAccept.addEventListener("click", () => {
  if (confirmCallback) confirmCallback();
});

// ===================== INIT =====================

requireRole("Administrador", async () => {
  setEditMode(false);

  // ===================== BOTONES HISTORIAL =====================

  if (btnSort) {
    btnSort.addEventListener("click", openSortModal);
  }

  if (btnSortCancel) {
    btnSortCancel.addEventListener("click", closeSortModal);
  }

  if (btnSortApply) {
    btnSortApply.addEventListener("click", () => {
      const sorted = sortPredictions(currentPredictions, sortSelect.value);
      currentPredictions = sorted;
      renderPredictions(sorted);
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

  // ===================== CARGA DATOS =====================

  await loadUser();
  await loadDoctorPredictions();
});