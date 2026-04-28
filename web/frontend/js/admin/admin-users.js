import { requireRole } from "../auth-guard.js";
import { db } from "../../firebase-config.js";
import {
  collection,
  getDocs,
  query,
  where
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const btnBack = document.getElementById("btn-back");
const btnMedicos = document.getElementById("btn-medicos");
const btnAdmins = document.getElementById("btn-admins");
const usersTitle = document.getElementById("users-title");
const searchInput = document.getElementById("search-input");
const usersList = document.getElementById("users-list");
const usersEmpty = document.getElementById("users-empty");

let currentRole = "Médico";
let currentUsers = [];

function normalize(value) {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function getFullName(user) {
  const name = user.name || "";
  const lastname = user.lastname || "";
  const fullName = `${name} ${lastname}`.trim();

  return fullName || user.email || "Usuario sin nombre";
}

function isActiveUser(user) {
  return user.active !== false;
}

function renderUsers() {
  const search = normalize(searchInput.value);

  const filteredUsers = currentUsers.filter((user) => {
    const fullName = normalize(getFullName(user));
    const email = normalize(user.email);

    return fullName.includes(search) || email.includes(search);
  });

  usersList.innerHTML = "";

  if (filteredUsers.length === 0) {
    usersEmpty.hidden = false;
    return;
  }

  usersEmpty.hidden = true;

  filteredUsers.forEach((user) => {
    const card = document.createElement("article");
    card.className = "user-card";

    const active = isActiveUser(user);

    card.innerHTML = `
      <div class="user-icon">
        <svg viewBox="0 0 24 24">
          <path
            d="M12,12c2.21,0 4,-1.79 4,-4s-1.79,-4 -4,-4 -4,1.79 -4,4 1.79,4 4,4zM12,14c-2.67,0 -8,1.34 -8,4v2h16v-2c0,-2.66 -5.33,-4 -8,-4z"
            fill="#042939"
          ></path>
        </svg>
      </div>

      <div>
        <div class="user-name">${getFullName(user)}</div>
        <div class="user-email">${user.email || "Sin email"}</div>
      </div>

      <div class="user-status ${active ? "" : "inactive"}">
        ${active ? "Activo" : "Inactivo"}
      </div>
    `;

    card.addEventListener("click", () => {
      if (user.role === "Médico") {
        window.location.href = `../../html/medical-profile.html?userId=${user.id}`;
      } else {
        window.location.href = `../../html/admin-profile.html?userId=${user.id}`;
      }
    });

    usersList.appendChild(card);
  });
}

async function loadUsersByRole(role) {
  const usersQuery = query(
    collection(db, "users"),
    where("role", "==", role)
  );

  const snapshot = await getDocs(usersQuery);

  currentUsers = snapshot.docs.map((docSnap) => ({
    id: docSnap.id,
    ...docSnap.data()
  }));

  currentUsers.sort((a, b) =>
    getFullName(a).localeCompare(getFullName(b), "es")
  );

  renderUsers();
}

async function setRole(role) {
  currentRole = role;

  const isMedico = role === "Médico";

  btnMedicos.classList.toggle("active", isMedico);
  btnAdmins.classList.toggle("active", !isMedico);

  usersTitle.textContent = isMedico ? "MÉDICOS" : "ADMINISTRADORES";
  searchInput.value = "";

  await loadUsersByRole(role);
}

requireRole("Administrador", async () => {
  if (btnBack) {
    btnBack.addEventListener("click", () => {
      window.location.href = "../../html/admin.html";
    });
  }

  btnMedicos.addEventListener("click", async () => {
    if (currentRole !== "Médico") {
      await setRole("Médico");
    }
  });

  btnAdmins.addEventListener("click", async () => {
    if (currentRole !== "Administrador") {
      await setRole("Administrador");
    }
  });

  searchInput.addEventListener("input", renderUsers);

  await setRole("Médico");
});