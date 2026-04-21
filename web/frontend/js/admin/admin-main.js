import { requireRole, logoutAndRedirect } from "../auth-guard.js";

const logoutBtn = document.getElementById("logout-btn-admin");
const message = document.getElementById("admin-user-message");

requireRole("Administrador", (user, profile) => {
  if (message) {
    message.textContent = `Bienvenido/a, ${profile.name} ${profile.lastname}.`;
  }

  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await logoutAndRedirect();
      } catch (error) {
        console.error("Error al cerrar sesión:", error);
      }
    });
  }
});