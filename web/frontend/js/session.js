import { auth, db } from "../firebase-config.js";

import {
  signOut,
  onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

import {
  doc,
  getDoc
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

import {
  logoutBtn,
  dashboardMessage
} from "./dom.js";

import { showView } from "./ui.js";

export function initSession() {
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

  onAuthStateChanged(auth, async (user) => {
    if (user) {
      try {
        const userRef = doc(db, "users", user.uid);
        const userSnap = await getDoc(userRef);

        if (userSnap.exists()) {
          const data = userSnap.data();
          if (dashboardMessage) {
            dashboardMessage.textContent = `Bienvenido/a, ${data.name} ${data.lastname}.`;
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
}