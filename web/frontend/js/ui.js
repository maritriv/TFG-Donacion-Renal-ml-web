import {
  loginView,
  registerView,
  dashboardView,
  loginMessage,
  registerMessage
} from "./dom.js";

export function showView(view) {
  loginView.classList.remove("active");
  registerView.classList.remove("active");
  dashboardView.classList.remove("active");

  if (view === "login") loginView.classList.add("active");
  if (view === "register") registerView.classList.add("active");
  if (view === "dashboard") dashboardView.classList.add("active");
}

export function setMessage(element, text, type = "") {
  if (!element) return;

  element.textContent = text;
  element.style.color =
    type === "error" ? "#e56f66" :
    type === "success" ? "#7cc873" :
    "#042939";
}

export function clearMessages() {
  setMessage(loginMessage, "");
  setMessage(registerMessage, "");
}