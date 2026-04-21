import { requireRole, logoutAndRedirect } from "../auth-guard.js";

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

function calcularPorcentaje(parte, total) {
  if (!total || total <= 0) return 0;
  return Math.round((parte / total) * 100);
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
    donutChartEl.style.background = `conic-gradient(
      #7cc873 0% ${porcentajeValidas}%,
      #e56f66 ${porcentajeValidas}% 100%
    )`;
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
      console.log("Editar perfil pulsado");
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDrawer();
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

/* IMPORTANTE: el menú se inicializa siempre al cargar */
initDrawerEvents();

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

  const validas = Number(profile?.predicciones_validas || 0);
  const noValidas = Number(profile?.predicciones_no_validas || 0);

  renderDonut(validas, noValidas);
});