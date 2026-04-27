import { requireRole, logoutAndRedirect } from "../auth-guard.js";
import { db } from "../../firebase-config.js";

import {
  collection,
  getDocs,
  query,
  where
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const logoutBtn = document.getElementById("logout-btn-admin");
const message = document.getElementById("admin-user-message");

const totalPrediccionesEl = document.getElementById("admin-total-predicciones");
const validasTextEl = document.getElementById("admin-validas-text");
const noValidasTextEl = document.getElementById("admin-no-validas-text");
const donutChartEl = document.querySelector(".donut-chart");

const menuToggleBtn = document.getElementById("menu-toggle-btn");
const drawerCloseBtn = document.getElementById("drawer-close-btn");
const drawerOverlay = document.getElementById("drawer-overlay");
const sideDrawer = document.getElementById("side-drawer");
const drawerLogoutBtn = document.getElementById("drawer-logout-btn");
const drawerEditProfileBtn = document.getElementById("drawer-edit-profile-btn");

const btnViewUsers = document.getElementById("btn-view-users");
const btnViewPredictions = document.getElementById("btn-view-predictions");

function calcularPorcentaje(parte, total) {
  if (!total || total <= 0) return 0;
  return Math.round((parte / total) * 100);
}

function esPrediccionValida(rawVal) {
  if (typeof rawVal === "boolean") return rawVal;
  if (typeof rawVal === "number") return rawVal !== 0;

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

  totalPrediccionesEl.textContent = total;
  validasTextEl.textContent = `${porcentajeValidas}% Válidas`;
  noValidasTextEl.textContent = `${porcentajeNoValidas}% No válidas`;

  if (total === 0) {
    donutChartEl.style.background = "conic-gradient(#d9d9d9 0% 100%)";
    return;
  }

  donutChartEl.style.background = `conic-gradient(
    #7cc873 0% ${porcentajeValidas}%,
    #e56f66 ${porcentajeValidas}% 100%
  )`;
}

async function cargarEstadisticasGlobales(mode = "all") {
  try {
    let prediccionesQuery;

    if (!mode || mode === "all") {
      prediccionesQuery = query(collection(db, "predicciones"));
    } else {
      prediccionesQuery = query(
        collection(db, "predicciones"),
        where("prediction_mode", "==", mode)
      );
    }

    const snapshot = await getDocs(prediccionesQuery);

    let validas = 0;
    let noValidas = 0;

    snapshot.forEach((docSnap) => {
      const data = docSnap.data();

      if (esPrediccionValida(data.valido)) {
        validas++;
      } else {
        noValidas++;
      }
    });

    renderDonut(validas, noValidas);
  } catch (error) {
    console.error("Error cargando estadísticas globales:", error);
    renderDonut(0, 0);
  }
}

function openDrawer() {
  sideDrawer.classList.add("open");
  sideDrawer.setAttribute("aria-hidden", "false");
  drawerOverlay.classList.add("show");
  document.body.classList.add("drawer-open");
}

function closeDrawer() {
  sideDrawer.classList.remove("open");
  sideDrawer.setAttribute("aria-hidden", "true");
  drawerOverlay.classList.remove("show");
  document.body.classList.remove("drawer-open");
}

function initDrawerEvents() {
  menuToggleBtn.addEventListener("click", openDrawer);
  drawerCloseBtn.addEventListener("click", closeDrawer);
  drawerOverlay.addEventListener("click", closeDrawer);

  drawerEditProfileBtn.addEventListener("click", () => {
    closeDrawer();
    window.location.href = "../../html/editar-perfil.html";
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDrawer();
  });
}

function initPredictionFilter() {
  const container = document.getElementById("prediction-filter");
  const trigger = document.getElementById("prediction-filter-trigger");
  const label = document.getElementById("prediction-filter-label");
  const options = document.querySelectorAll(".chart-select-option");

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

      await cargarEstadisticasGlobales(option.dataset.value);
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

logoutBtn.addEventListener("click", handleLogout);
drawerLogoutBtn.addEventListener("click", handleLogout);

btnViewUsers.addEventListener("click", () => {
  window.location.href = "../../html/admin-users.html";
});

btnViewPredictions.addEventListener("click", () => {
  window.location.href = "../../html/historial.html?scope=admin";
});

requireRole("Administrador", async (user, profile) => {
  const nombre = profile?.name || "";
  const apellido = profile?.lastname || "";
  const nombreCompleto = `${nombre} ${apellido}`.trim();

  message.textContent = `Bienvenido/a, ${nombreCompleto || user.email}.`;

  await cargarEstadisticasGlobales("all");
});