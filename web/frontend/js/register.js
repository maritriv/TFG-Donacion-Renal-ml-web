import { auth, db } from "../firebase-config.js";

import { createUserWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { doc, setDoc } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

import {
  registerForm,
  registerMessage,
  calendarIcon,
  birthdateInput
} from "./dom.js";

import { clearMessages, setMessage, showView } from "./ui.js";
import { translateFirebaseError } from "./errors.js";

export function initRegister() {
  if (calendarIcon && birthdateInput) {
    calendarIcon.addEventListener("click", () => {
      if (typeof birthdateInput.showPicker === "function") {
        birthdateInput.showPicker();
      } else {
        birthdateInput.focus();
        birthdateInput.click();
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearMessages();

      const name = document.getElementById("register-name").value.trim();
      const lastname = document.getElementById("register-lastname").value.trim();
      const birthdate = document.getElementById("register-birthdate").value;
      const email = document.getElementById("register-email").value.trim();
      const password = document.getElementById("register-password").value;
      const confirmPassword = document.getElementById("register-confirm-password").value;
      const role = document.getElementById("register-role").value;

      if (!name || !lastname || !birthdate || !email || !password || !confirmPassword || !role) {
        setMessage(registerMessage, "Completa todos los campos.", "error");
        return;
      }

      if (password !== confirmPassword) {
        setMessage(registerMessage, "Las contraseñas no coinciden.", "error");
        return;
      }

      if (password.length < 6) {
        setMessage(registerMessage, "La contraseña debe tener al menos 6 caracteres.", "error");
        return;
      }

      try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;

        await setDoc(doc(db, "users", user.uid), {
          uid: user.uid,
          name: name,
          lastname: lastname,
          birthdate: birthdate,
          email: email,
          role: role,
          active: true,
          numeroPredicciones: 0,
          predicciones_validas: 0,
          predicciones_no_validas: 0
        });

        setMessage(registerMessage, "Usuario registrado correctamente.", "success");
        registerForm.reset();
        showView("dashboard");
      } catch (error) {
        setMessage(registerMessage, translateFirebaseError(error.code), "error");
        console.error("Error en registro:", error);
      }
    });
  }
}