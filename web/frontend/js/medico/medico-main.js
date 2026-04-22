import { db } from "../../firebase-config.js";
import { requireRole, logoutAndRedirect } from "../auth-guard.js";

import {
  collection,
  getDocs,
  query,
  where
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const logoutBtn = document.getElementById("logout-btn-medico");
const message = document.getElementById("medico-user-message");

const totalPrediccionesEl = document.getElementById("medico-total-predicciones");
const validasTextEl = document.getElementById("medico-validas-text");
const noValidasTextEl = document.getElementById("medico-no-validas-text");
const donutChartEl = document.querySelector(".donut-chart");

const menuToggleBtn = document.getElementById("menu-toggle-btn");
const drawerCloseBtn = document.getElementById("drawer-close-btn");
const drawerOverlay = document.getElementById("drawer-overlay");
const sideDrawer = document.getElementById("side-drawer");
const drawerLogoutBtn = document.getElementById("drawer-logout-btn");
const drawerEditProfileBtn = document.getElementById("drawer-edit-profile-btn");

const MODE_MID = "MID_RCP";
const MODE_AFTER = "AFTER_RCP";

let allPredicciones = [];
let filtroActual = "all";

function calcularPorcentaje(parte, total) {
  if (!total || total <= 0) return 0;
  return Math.round((parte / total) * 100);
}

function normalizarTexto(valor) {
  return String(valor || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function esPrediccionValida(rawVal) {
  if (typeof rawVal === "boolean") return rawVal;

  if (typeof rawVal === "string") {
    const valor = normalizarTexto(rawVal);
    return (
      valor === "si" ||
      valor === "sí" ||
      valor === "true" ||
      valor === "1"
    );
  }

  if (typeof rawVal === "number") {
    return rawVal !== 0;
  }

  return false;
}

function obtenerModoPrediccion(data) {
  const predictionMode = String(data?.prediction_mode || "").trim();
  const momentoLegible = normalizarTexto(data?.modelos?.momento_prediccion_legible);

  if (predictionMode === MODE_MID || predictionMode === MODE_AFTER) {
    return predictionMode;
  }

  if (
    momentoLegible.includes("mitad del procedimiento") ||
    momentoLegible.includes("20 min") ||
    momentoLegible.includes("mitad")
  ) {
    return MODE_MID;
  }

  if (
    momentoLegible.includes("despues del procedimiento") ||
    momentoLegible.includes("después del procedimiento") ||
    momentoLegible.includes("despues")
  ) {
    return MODE_AFTER;
  }

  return null;
}

function renderDonut(validas, noValidas) {
  const total = validas + noValidas;
  const porcentajeValidas = calcularPorcentaje(validas, total);
  const porcentajeNoValidas = total > 0 ? 100 - porcentajeValidas : 0;

  if (totalPrediccionesEl) {
    totalPrediccionesEl.textContent = total;
  }

  if (validasTextEl) {
    validasTextEl.textContent = `${porcentajeValidas}% Válidas`;
  }

  if (noValidasTextEl) {
    noValidasTextEl.textContent = `${porcentajeNoValidas}% No válidas`;
  }

  if (donutChartEl) {
    if (total === 0) {
      donutChartEl.style.background = "conic-gradient(#d9d9d9 0% 100%)";
      return;
    }

    donutChartEl.style.background = `conic-gradient(
      #7cc873 0% ${porcentajeValidas}%,
      #e56f66 ${porcentajeValidas}% 100%
    )`;
  }
}

function aplicarFiltroYRender() {
  let prediccionesFiltradas = allPredicciones;

  if (filtroActual !== "all") {
    prediccionesFiltradas = allPredicciones.filter(
      (pred) => pred.modo === filtroActual
    );
  }

  let validas = 0;
  let noValidas = 0;

  prediccionesFiltradas.forEach((pred) => {
    if (pred.valida) {
      validas += 1;
    } else {
      noValidas += 1;
    }
  });

  renderDonut(validas, noValidas);
}

async function cargarPrediccionesMedico(uidMedico) {
  const prediccionesRef = collection(db, "predicciones");
  const q = query(prediccionesRef, where("uid_medico", "==", uidMedico));
  const snapshot = await getDocs(q);

  allPredicciones = snapshot.docs.map((docSnap) => {
    const data = docSnap.data();

    return {
      id: docSnap.id,
      valida: esPrediccionValida(data?.valido),
      modo: obtenerModoPrediccion(data),
      raw: data
    };
  });

  console.log(
    "Predicciones cargadas:",
    allPredicciones.map((p) => ({
      id: p.id,
      modo: p.modo,
      valida: p.valida,
      prediction_mode: p.raw?.prediction_mode,
      momento_legible: p.raw?.modelos?.momento_prediccion_legible
    }))
  );

  aplicarFiltroYRender();
}

function openDrawer() {
  if (sideDrawer) {
    sideDrawer.classList.add("open");
    sideDrawer.setAttribute("aria-hidden", "false");
  }

  if (drawerOverlay) {
    drawerOverlay.classList.add("show");
  }

  document.body.classList.add("drawer-open");
}

function closeDrawer() {
  if (sideDrawer) {
    sideDrawer.classList.remove("open");
    sideDrawer.setAttribute("aria-hidden", "true");
  }

  if (drawerOverlay) {
    drawerOverlay.classList.remove("show");
  }

  document.body.classList.remove("drawer-open");
}

function initDrawerEvents() {
  if (menuToggleBtn) {
    menuToggleBtn.addEventListener("click", openDrawer);
  }

  if (drawerCloseBtn) {
    drawerCloseBtn.addEventListener("click", closeDrawer);
  }

  if (drawerOverlay) {
    drawerOverlay.addEventListener("click", closeDrawer);
  }

  if (drawerEditProfileBtn) {
    drawerEditProfileBtn.addEventListener("click", () => {
      closeDrawer();
      window.location.href = "./editar-perfil.html";
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDrawer();
    }
  });
}

function initPredictionFilter() {
  const container = document.getElementById("prediction-filter");
  const trigger = document.getElementById("prediction-filter-trigger");
  const label = document.getElementById("prediction-filter-label");
  const options = document.querySelectorAll(".chart-select-option");

  if (!container || !trigger || !label || !options.length) return;

  trigger.addEventListener("click", (event) => {
    event.stopPropagation();
    const abierto = container.classList.toggle("open");
    trigger.setAttribute("aria-expanded", abierto ? "true" : "false");
  });

  options.forEach((option) => {
    option.addEventListener("click", () => {
      options.forEach((opt) => opt.classList.remove("active"));
      option.classList.add("active");

      label.textContent = option.textContent.trim();
      filtroActual = option.dataset.value || "all";

      container.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");

      aplicarFiltroYRender();
    });
  });

  document.addEventListener("click", (event) => {
    if (!container.contains(event.target)) {
      container.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
    }
  });
}

async function handleLogout() {
  try {
    await logoutAndRedirect();
  } catch (error) {
    console.error("Error al cerrar sesión:", error);
  }
}

initDrawerEvents();
initPredictionFilter();

if (logoutBtn) {
  logoutBtn.addEventListener("click", handleLogout);
}

if (drawerLogoutBtn) {
  drawerLogoutBtn.addEventListener("click", handleLogout);
}

requireRole("Médico", async (user, profile) => {
  if (message) {
    const nombre = profile?.name || "";
    const apellido = profile?.lastname || "";
    const nombreCompleto = `${nombre} ${apellido}`.trim();
    message.textContent = `Bienvenido/a, ${nombreCompleto || user.email}.`;
  }

  try {
    await cargarPrediccionesMedico(user.uid);
  } catch (error) {
    console.error("Error cargando predicciones del médico:", error);
    renderDonut(0, 0);
  }
});