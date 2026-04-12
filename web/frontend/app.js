import { auth, db } from "./firebase-config.js";

import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

import {
  doc,
  setDoc,
  getDoc,
  serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// VISTAS
const loginView = document.getElementById("login-view");
const registerView = document.getElementById("register-view");
const dashboardView = document.getElementById("dashboard-view");

// BOTONES Y FORMULARIOS
const goRegisterBtn = document.getElementById("go-register");
const goLoginBtn = document.getElementById("go-login");
const forgotPasswordBtn = document.getElementById("forgot-password-btn");
const logoutBtn = document.getElementById("logout-btn");

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

// FECHA
const calendarIcon = document.getElementById("calendar-icon");
const birthdateInput = document.getElementById("register-birthdate");

// MENSAJES
const loginMessage = document.getElementById("login-message");
const registerMessage = document.getElementById("register-message");
const dashboardMessage = document.getElementById("dashboard-message");

// CAMBIAR VISTA
function showView(view) {
  loginView.classList.remove("active");
  registerView.classList.remove("active");
  dashboardView.classList.remove("active");

  if (view === "login") loginView.classList.add("active");
  if (view === "register") registerView.classList.add("active");
  if (view === "dashboard") dashboardView.classList.add("active");
}

function setMessage(element, text, type = "") {
  if (!element) return;
  element.textContent = text;
  element.style.color =
    type === "error" ? "#e56f66" :
    type === "success" ? "#7cc873" :
    "#042939";
}

function clearMessages() {
  setMessage(loginMessage, "");
  setMessage(registerMessage, "");
}

// NAVEGACIÓN ENTRE VISTAS
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

// ABRIR CALENDARIO DESDE ICONO IZQUIERDO
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

// RECUPERAR CONTRASEÑA
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

// REGISTRO
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

      await setDoc(doc(db, "usuarios", user.uid), {
        uid: user.uid,
        nombre: name,
        apellidos: lastname,
        fechaNacimiento: birthdate,
        email: email,
        rol: role,
        creadoEn: serverTimestamp()
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

// LOGIN
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

// LOGOUT
if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    try {
      await signOut(auth);
      showView("login");
    } catch (error) {
      console.error("Error al cerrar sesión:", error);
    }
  });
}

// SESIÓN ACTIVA
onAuthStateChanged(auth, async (user) => {
  if (user) {
    try {
      const userRef = doc(db, "usuarios", user.uid);
      const userSnap = await getDoc(userRef);

      if (userSnap.exists()) {
        const data = userSnap.data();
        if (dashboardMessage) {
          dashboardMessage.textContent = `Bienvenido/a, ${data.nombre} ${data.apellidos}.`;
        }
      } else {
        if (dashboardMessage) {
          dashboardMessage.textContent = `Bienvenido/a, ${user.email}.`;
        }
      }
    } catch (error) {
      console.error("Error leyendo usuario:", error);
      if (dashboardMessage) {
        dashboardMessage.textContent = `Bienvenido/a, ${user.email}.`;
      }
    }

    showView("dashboard");
  } else {
    showView("login");
  }
});

// TRADUCCIÓN DE ERRORES
function translateFirebaseError(code) {
  switch (code) {
    case "auth/email-already-in-use":
      return "Ese correo ya está registrado.";
    case "auth/invalid-email":
      return "El correo electrónico no es válido.";
    case "auth/user-not-found":
      return "No existe ningún usuario con ese correo.";
    case "auth/wrong-password":
    case "auth/invalid-credential":
      return "Credenciales incorrectas.";
    case "auth/weak-password":
      return "La contraseña es demasiado débil.";
    case "auth/missing-password":
      return "Introduce una contraseña.";
    case "auth/too-many-requests":
      return "Demasiados intentos. Inténtalo de nuevo más tarde.";
    default:
      return "Ha ocurrido un error. Revisa la configuración de Firebase.";
  }
}

// DEBUG GLOBAL
window.onerror = function (msg, url, lineNo, columnNo, error) {
  console.error("ERROR JS:", msg, "en", lineNo, columnNo, error);
};