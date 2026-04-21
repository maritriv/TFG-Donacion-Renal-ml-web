import {
  loginMessage,
  registerMessage
} from "./dom.js";

function safeToggleById(id, active) {
  const element = document.getElementById(id);
  if (!element) return;

  if (active) {
    element.classList.add("active");
  } else {
    element.classList.remove("active");
  }
}

export function showView(view) {
  safeToggleById("login-view", view === "login");
  safeToggleById("register-view", view === "register");
}

export function setMessage(element, text, type = "") {
  if (!element) return;

  element.textContent = text;
  element.style.color =
    type === "error"
      ? "#e56f66"
      : type === "success"
      ? "#7cc873"
      : "#042939";
}

export function clearMessages() {
  setMessage(loginMessage, "");
  setMessage(registerMessage, "");
}