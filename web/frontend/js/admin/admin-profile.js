import { requireRole } from "../auth-guard.js";
import { db } from "../../firebase-config.js";
import {
  deleteDoc,
  doc,
  getDoc,
  updateDoc
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const page = document.querySelector(".admin-profile-page");

const btnBack = document.getElementById("btn-back");
const btnEdit = document.getElementById("btn-edit");
const btnCancelEdit = document.getElementById("btn-cancel-edit");
const btnSave = document.getElementById("btn-save");
const btnDelete = document.getElementById("btn-delete");

const statusBtn = document.getElementById("profile-status");
const roleText = document.getElementById("profile-role-text");
const roleSelect = document.getElementById("profile-role");

const inputName = document.getElementById("profile-name");
const inputLastname = document.getElementById("profile-lastname");
const inputEmail = document.getElementById("profile-email");
const inputBirthdate = document.getElementById("profile-birthdate");

const modal = document.getElementById("confirm-modal");
const confirmTitle = document.getElementById("confirm-title");
const confirmMessage = document.getElementById("confirm-message");
const confirmCancel = document.getElementById("confirm-cancel");
const confirmAccept = document.getElementById("confirm-accept");

const params = new URLSearchParams(window.location.search);
const userId = params.get("userId");

let originalUser = null;
let currentActive = true;
let confirmCallback = null;

function setStatus(active) {
  currentActive = active;
  statusBtn.textContent = active ? "Activo" : "Inactivo";
  statusBtn.classList.toggle("active", active);
  statusBtn.classList.toggle("inactive", !active);
}

function setEditMode(enabled) {
  page.classList.toggle("editing", enabled);

  [inputName, inputLastname, inputEmail, inputBirthdate].forEach((input) => {
    input.disabled = !enabled;
    input.classList.toggle("editing", enabled);
  });

  roleSelect.disabled = !enabled;
  roleSelect.classList.toggle("editing", enabled);
}

function fillUser(user) {
  originalUser = { ...user };

  inputName.value = user.name || "";
  inputLastname.value = user.lastname || "";
  inputEmail.value = user.email || "";
  inputBirthdate.value = user.birthdate || "";

  roleText.textContent = user.role || "Administrador";
  roleSelect.value = user.role || "Administrador";

  setStatus(user.active !== false);
}

function getCurrentData() {
  return {
    name: inputName.value.trim(),
    lastname: inputLastname.value.trim(),
    email: inputEmail.value.trim(),
    birthdate: inputBirthdate.value.trim(),
    role: roleSelect.value,
    active: currentActive
  };
}

function hasChanges() {
  if (!originalUser) return false;

  const current = getCurrentData();

  return (
    current.name !== (originalUser.name || "") ||
    current.lastname !== (originalUser.lastname || "") ||
    current.email !== (originalUser.email || "") ||
    current.birthdate !== (originalUser.birthdate || "") ||
    current.role !== (originalUser.role || "Administrador") ||
    current.active !== (originalUser.active !== false)
  );
}

function openConfirm(title, message, onAccept, acceptText = "Aceptar") {
  confirmTitle.textContent = title;
  confirmMessage.textContent = message;
  confirmAccept.textContent = acceptText;
  confirmCallback = onAccept;
  modal.hidden = false;
}

function closeConfirm() {
  modal.hidden = true;
  confirmCallback = null;
}

async function loadUser() {
  if (!userId) {
    alert("Usuario no válido.");
    window.location.href = "../../html/admin-users.html";
    return;
  }

  const snap = await getDoc(doc(db, "users", userId));

  if (!snap.exists()) {
    alert("Usuario no encontrado.");
    window.location.href = "../../html/admin-users.html";
    return;
  }

  fillUser(snap.data());
}

async function saveChanges() {
  const data = getCurrentData();

  await updateDoc(doc(db, "users", userId), data);

  roleText.textContent = data.role;
  originalUser = { ...data };

  setEditMode(false);
  alert("Cambios guardados.");
}

async function deleteUser() {
  await deleteDoc(doc(db, "users", userId));
  alert("Usuario eliminado.");
  window.location.href = "../../html/admin-users.html";
}

btnBack.addEventListener("click", () => {
  window.location.href = "../../html/admin-users.html";
});

btnEdit.addEventListener("click", () => {
  setEditMode(true);
});

btnCancelEdit.addEventListener("click", () => {
  if (hasChanges()) {
    openConfirm(
      "Descartar cambios",
      "¿Estás seguro de que quieres descartar los cambios realizados?",
      () => {
        fillUser(originalUser);
        setEditMode(false);
        closeConfirm();
      },
      "Descartar"
    );
    return;
  }

  fillUser(originalUser);
  setEditMode(false);
});

statusBtn.addEventListener("click", () => {
  if (!page.classList.contains("editing")) return;
  setStatus(!currentActive);
});

btnSave.addEventListener("click", async () => {
  try {
    await saveChanges();
  } catch (error) {
    console.error(error);
    alert("Error al guardar cambios.");
  }
});

btnDelete.addEventListener("click", () => {
  openConfirm(
    "Eliminar usuario",
    "¿Estás seguro de que quieres eliminar a este usuario?",
    async () => {
      closeConfirm();

      try {
        await deleteUser();
      } catch (error) {
        console.error(error);
        alert("Error al eliminar usuario.");
      }
    },
    "Eliminar"
  );
});

confirmCancel.addEventListener("click", closeConfirm);

confirmAccept.addEventListener("click", () => {
  if (confirmCallback) confirmCallback();
});

requireRole("Administrador", async () => {
  setEditMode(false);
  await loadUser();
});