import { requireRole } from "../auth-guard.js";

const btnModeMid = document.getElementById("btn-mode-mid");
const btnModeAfter = document.getElementById("btn-mode-after");
const btnBackToMain = document.getElementById("btn-back-to-main");

requireRole("Médico", async () => {
  if (btnBackToMain) {
    btnBackToMain.addEventListener("click", () => {
      window.location.href = "../../html/medico.html";
    });
  }

  if (btnModeMid) {
    btnModeMid.addEventListener("click", () => {
      console.log("Modo seleccionado: MID_RCP");
      // Después aquí conectaremos con el cuestionario real
      // window.location.href = "../../html/prediction.html?mode=MID_RCP";
    });
  }

  if (btnModeAfter) {
    btnModeAfter.addEventListener("click", () => {
      console.log("Modo seleccionado: AFTER_RCP");
      // Después aquí conectaremos con el cuestionario real
      // window.location.href = "../../html/prediction.html?mode=AFTER_RCP";
    });
  }
});