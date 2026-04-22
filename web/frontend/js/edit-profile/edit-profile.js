import { auth, db } from "../../firebase-config.js";
import { redirectByRole } from "../auth-guard.js";

import {
  onAuthStateChanged,
  EmailAuthProvider,
  reauthenticateWithCredential,
  updatePassword,
  updateEmail
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

import {
  doc,
  getDoc,
  updateDoc,
  collection,
  query,
  where,
  getDocs
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const backBtn = document.getElementById("back-btn");
const form = document.getElementById("edit-profile-form");
const messageEl = document.getElementById("edit-message");

const nameInput = document.getElementById("edit-name");
const lastnameInput = document.getElementById("edit-lastname");
const birthdateInput = document.getElementById("edit-birthdate");
const emailInput = document.getElementById("edit-email");

const passwordInput = document.getElementById("edit-password");
const newPasswordInput = document.getElementById("edit-new-password");
const confirmPasswordInput = document.getElementById("edit-confirm-password");

const calendarIcon = document.getElementById("edit-calendar-icon");

const discardModal = document.getElementById("discard-modal");
const cancelDiscardBtn = document.getElementById("cancel-discard");
const confirmDiscardBtn = document.getElementById("confirm-discard");

let currentUser = null;
let currentProfile = null;
let eventsInitialized = false;

let originalData = {
  name: "",
  lastname: "",
  birthdate: "",
  email: ""
};

function setMessage(text, type = "") {
  if (!messageEl) return;

  messageEl.textContent = text;
  messageEl.style.color =
    type === "error"
      ? "#e56f66"
      : type === "success"
      ? "#7cc873"
      : "#042939";
}

function normalizeDateValue(value) {
  if (!value) return "";

  const trimmed = String(value).trim();

  // Ya viene como yyyy-mm-dd
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return trimmed;
  }

  // Si viene como dd/mm/yyyy lo convertimos a yyyy-mm-dd
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(trimmed)) {
    const [day, month, year] = trimmed.split("/");
    return `${year}-${month}-${day}`;
  }

  return "";
}

function getFormData() {
  return {
    name: nameInput.value.trim(),
    lastname: lastnameInput.value.trim(),
    birthdate: normalizeDateValue(birthdateInput.value),
    email: emailInput.value.trim()
  };
}

function clearPasswordFields() {
  passwordInput.value = "";
  newPasswordInput.value = "";
  confirmPasswordInput.value = "";
}

function openDiscardModal() {
  if (!discardModal) return;
  discardModal.classList.add("show");
  document.body.classList.add("drawer-open");
}

function closeDiscardModal() {
  if (!discardModal) return;
  discardModal.classList.remove("show");
  document.body.classList.remove("drawer-open");
}

function hasChanges() {
  const currentData = getFormData();

  const profileChanged =
    currentData.name !== originalData.name ||
    currentData.lastname !== originalData.lastname ||
    currentData.birthdate !== originalData.birthdate ||
    currentData.email !== originalData.email;

  const passwordChanged =
    passwordInput.value.trim() !== "" ||
    newPasswordInput.value.trim() !== "" ||
    confirmPasswordInput.value.trim() !== "";

  return profileChanged || passwordChanged;
}

function goBackByRole() {
  if (!currentProfile?.role) {
    window.location.href = "../../html/index.html";
    return;
  }

  redirectByRole(currentProfile.role);
}

function handleBack() {
  if (hasChanges()) {
    openDiscardModal();
    return;
  }

  goBackByRole();
}

async function loadProfile(user) {
  const userRef = doc(db, "users", user.uid);
  const userSnap = await getDoc(userRef);

  if (!userSnap.exists()) {
    window.location.href = "../../html/index.html";
    return;
  }

  const profile = userSnap.data();
  currentProfile = profile;

  const normalizedBirthdate = normalizeDateValue(profile.birthdate);

  nameInput.value = profile.name || "";
  lastnameInput.value = profile.lastname || "";
  birthdateInput.value = normalizedBirthdate;
  emailInput.value = profile.email || user.email || "";

  originalData = {
    name: (profile.name || "").trim(),
    lastname: (profile.lastname || "").trim(),
    birthdate: normalizedBirthdate,
    email: (profile.email || user.email || "").trim()
  };

  clearPasswordFields();
  setMessage("");
}

async function isEmailAvailable(email, uid) {
  if (!email) return false;
  if (email === originalData.email) return true;

  const usersRef = collection(db, "users");
  const q = query(usersRef, where("email", "==", email));
  const querySnapshot = await getDocs(q);

  let emailInUseByOtherUser = false;

  querySnapshot.forEach((docSnap) => {
    if (docSnap.id !== uid) {
      emailInUseByOtherUser = true;
    }
  });

  return !emailInUseByOtherUser;
}

async function updateProfileData(user, profile) {
  const { name, lastname, birthdate, email } = getFormData();

  const currentPassword = passwordInput.value;
  const newPassword = newPasswordInput.value;
  const confirmPassword = confirmPasswordInput.value;

  if (!name || !lastname || !birthdate || !email) {
    setMessage("Nombre, apellidos, fecha y email son obligatorios.", "error");
    return;
  }

  const emailAvailable = await isEmailAvailable(email, user.uid);
  if (!emailAvailable) {
    setMessage("Ese correo ya está en uso por otro usuario.", "error");
    return;
  }

  const wantsPasswordChange =
    currentPassword.trim() !== "" ||
    newPassword.trim() !== "" ||
    confirmPassword.trim() !== "";

  if (wantsPasswordChange) {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setMessage("Si quieres cambiar la contraseña, rellena los tres campos.", "error");
      return;
    }

    if (newPassword !== confirmPassword) {
      setMessage("La nueva contraseña y su confirmación no coinciden.", "error");
      return;
    }

    if (newPassword.length < 6) {
      setMessage("La nueva contraseña debe tener al menos 6 caracteres.", "error");
      return;
    }

    const credential = EmailAuthProvider.credential(user.email, currentPassword);

    try {
      await reauthenticateWithCredential(user, credential);
      await updatePassword(user, newPassword);
    } catch (error) {
      console.error("Error cambiando contraseña:", error);
      setMessage("La contraseña actual es incorrecta.", "error");
      return;
    }
  }

  try {
    const userRef = doc(db, "users", user.uid);

    await updateDoc(userRef, {
      name,
      lastname,
      birthdate,
      email
    });

    if (user.email !== email) {
      try {
        await updateEmail(user, email);
      } catch (error) {
        console.error("No se pudo actualizar el email en Auth:", error);
      }
    }

    originalData = { name, lastname, birthdate, email };
    clearPasswordFields();
    setMessage("Cambios guardados correctamente.", "success");

    setTimeout(() => {
      redirectByRole(profile.role);
    }, 700);
  } catch (error) {
    console.error("Error actualizando perfil:", error);
    setMessage("Error al actualizar los datos. Inténtalo de nuevo.", "error");
  }
}

function initCalendar() {
  if (!calendarIcon || !birthdateInput) return;

  calendarIcon.addEventListener("click", () => {
    if (typeof birthdateInput.showPicker === "function") {
      birthdateInput.showPicker();
    } else {
      birthdateInput.focus();
      birthdateInput.click();
    }
  });
}

function initEvents() {
  if (eventsInitialized) return;
  eventsInitialized = true;

  if (backBtn) {
    backBtn.addEventListener("click", handleBack);
  }

  if (cancelDiscardBtn) {
    cancelDiscardBtn.addEventListener("click", closeDiscardModal);
  }

  if (confirmDiscardBtn) {
    confirmDiscardBtn.addEventListener("click", () => {
      closeDiscardModal();
      goBackByRole();
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && discardModal?.classList.contains("show")) {
      closeDiscardModal();
    }
  });

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      if (!currentUser || !currentProfile) return;

      setMessage("");
      await updateProfileData(currentUser, currentProfile);
    });
  }
}

onAuthStateChanged(auth, async (user) => {
  if (!user) {
    window.location.href = "../../html/index.html";
    return;
  }

  currentUser = user;

  try {
    initCalendar();
    initEvents();
    await loadProfile(user);
  } catch (error) {
    console.error("Error cargando perfil:", error);
    window.location.href = "../../html/index.html";
  }
});