import {
  goRegisterBtn,
  goLoginBtn
} from "./dom.js";

import { clearMessages, showView } from "./ui.js";
import { initLogin } from "./login.js";
import { initRegister } from "./register.js";
import { initSession } from "./session.js";

function initNavigation() {
  if (goRegisterBtn) {
    goRegisterBtn.addEventListener("click", () => {
      clearMessages();
      showView("register");
    });
  }

  if (goLoginBtn) {
    goLoginBtn.addEventListener("click", () => {
      clearMessages();
      showView("login");
    });
  }
}

function initApp() {
  initNavigation();
  initLogin();
  initRegister();
  initSession();
}

initApp();

window.onerror = function (msg, url, lineNo, columnNo, error) {
  console.error("ERROR JS:", msg, "en", lineNo, columnNo, error);
};