import { requireRole, logoutAndRedirect } from "../auth-guard.js";
import { db } from "../../firebase-config.js";

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

const btnGoPredictionMode = document.getElementById("btn-go-prediction-mode");

const btnGoHistorial = document.getElementById("btn-go-historial-medico");

const btnGoImport = document.getElementById("btn-import");

if (btnGoHistorial) {
  btnGoHistorial.addEventListener("click", () => {
    window.location.href = "../../html/historial.html?scope=medico";
  });
}

if (btnGoImport) {
  btnGoImport.addEventListener("click", () => {
    window.location.href = "../../html/import.html";
  });
}

let currentUser = null;

function calcularPorcentaje(parte, total) {
  if (!total || total <= 0) return 0;
  return Math.round((parte / total) * 100);
}

function esPrediccionValida(rawVal) {
  if (typeof rawVal === "boolean") {
    return rawVal;
  }

  if (typeof rawVal === "number") {
    return rawVal !== 0;
  }

  if (typeof rawVal === "string") {
    const valor = rawVal.trim().toLowerCase();
    return valor === "si" || valor === "sí" || valor === "true" || valor === "1";
  }

  return false;
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

async function cargarEstadisticasPorModo(uidMedico, mode = "all") {
  try {
    let prediccionesQuery;

    if (!mode || mode === "all") {
      prediccionesQuery = query(
        collection(db, "predicciones"),
        where("uid_medico", "==", uidMedico)
      );
    } else {
      prediccionesQuery = query(
        collection(db, "predicciones"),
        where("uid_medico", "==", uidMedico),
        where("prediction_mode", "==", mode)
      );
    }

    const snapshot = await getDocs(prediccionesQuery);

    let validas = 0;
    let noValidas = 0;

    snapshot.forEach((docSnap) => {
      const data = docSnap.data();
      const rawVal = data.valido;

      if (esPrediccionValida(rawVal)) {
        validas++;
      } else {
        noValidas++;
      }
    });

    renderDonut(validas, noValidas);
  } catch (error) {
    console.error("Error cargando estadísticas:", error);
    renderDonut(0, 0);
  }
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
      window.location.href = "../../html/editar-perfil.html";
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
    container.classList.toggle("open");
    trigger.setAttribute(
      "aria-expanded",
      container.classList.contains("open") ? "true" : "false"
    );
  });

  options.forEach((option) => {
    option.addEventListener("click", async () => {
      options.forEach((opt) => opt.classList.remove("active"));
      option.classList.add("active");

      label.textContent = option.textContent.trim();
      container.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");

      const selectedMode = option.dataset.value;

      if (currentUser?.uid) {
        await cargarEstadisticasPorModo(currentUser.uid, selectedMode);
      }
    });
  });

  document.addEventListener("click", (event) => {
    if (!container.contains(event.target)) {
      container.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
    }
  });
}

function initPredictionModeButton() {
  if (btnGoPredictionMode) {
    btnGoPredictionMode.addEventListener("click", () => {
      window.location.href = "../../html/prediction-mode.html";
    });
  }
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
initPredictionModeButton();

if (logoutBtn) {
  logoutBtn.addEventListener("click", handleLogout);
}

if (drawerLogoutBtn) {
  drawerLogoutBtn.addEventListener("click", handleLogout);
}

requireRole("Médico", async (user, profile) => {
  currentUser = user;

  if (message) {
    const nombre = profile?.name || "";
    const apellido = profile?.lastname || "";
    const nombreCompleto = `${nombre} ${apellido}`.trim();
    message.textContent = `Bienvenido/a, ${nombreCompleto || user.email}.`;
  }

  await cargarEstadisticasPorModo(user.uid, "all");
});