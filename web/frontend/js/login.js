import { auth } from "../firebase-config.js";
import { sendPasswordResetEmail, signInWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

import {
  forgotPasswordBtn,
  loginForm,
  loginMessage
} from "./dom.js";

import { clearMessages, setMessage } from "./ui.js";
import { translateFirebaseError } from "./errors.js";

export function initLogin() {
  if (forgotPasswordBtn) {
    forgotPasswordBtn.addEventListener("click", async () => {
      const email = document.getElementById("login-email").value.trim();

      if (!email) {
        setMessage(loginMessage, "Introduce tu email para recuperar la contraseña.", "error");
        return;
      }

      try {
        await sendPasswordResetEmail(auth, email);
        setMessage(loginMessage, "Te hemos enviado un correo para restablecer la contraseña.", "success");
      } catch (error) {
        setMessage(loginMessage, translateFirebaseError(error.code), "error");
        console.error("Error al enviar recuperación:", error);
      }
    });
  }

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearMessages();

      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;

      if (!email || !password) {
        setMessage(loginMessage, "Introduce email y contraseña.", "error");
        return;
      }

      try {
        await signInWithEmailAndPassword(auth, email, password);
        setMessage(loginMessage, "Inicio de sesión correcto.", "success");
      } catch (error) {
        setMessage(loginMessage, translateFirebaseError(error.code), "error");
        console.error("Error en login:", error);
      }
    });
  }
}