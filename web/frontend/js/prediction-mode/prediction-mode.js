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
      window.location.href = "../../html/prediction.html?mode=mid";
    });
  }

  if (btnModeAfter) {
    btnModeAfter.addEventListener("click", () => {
      window.location.href = "../../html/prediction.html?mode=transfer";
    });
  }
});