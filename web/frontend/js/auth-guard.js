import { auth, db } from "../firebase-config.js";
import {
  onAuthStateChanged,
  signOut
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import {
  doc,
  getDoc
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

export function redirectByRole(role) {
  if (role === "Médico") {
    window.location.href = "./medico.html";
    return;
  }

  if (role === "Administrador") {
    window.location.href = "./admin.html";
    return;
  }

  window.location.href = "./index.html";
}

export async function getUserProfile(uid) {
  const ref = doc(db, "users", uid);
  const snap = await getDoc(ref);

  if (!snap.exists()) return null;

  return snap.data();
}

export function redirectIfAuthenticated() {
  onAuthStateChanged(auth, async (user) => {
    if (!user) return;

    try {
      const profile = await getUserProfile(user.uid);
      if (!profile) return;

      redirectByRole(profile.role);
    } catch (error) {
      console.error("Error comprobando sesión:", error);
    }
  });
}

export function requireRole(expectedRole, onReady) {
  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      window.location.href = "./index.html";
      return;
    }

    try {
      const profile = await getUserProfile(user.uid);

      if (!profile) {
        window.location.href = "./index.html";
        return;
      }

      if (profile.role !== expectedRole) {
        redirectByRole(profile.role);
        return;
      }

      onReady(user, profile);
    } catch (error) {
      console.error("Error validando acceso:", error);
      window.location.href = "./index.html";
    }
  });
}

export function requireAuthenticatedProfile(onReady) {
  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      window.location.href = "./index.html";
      return;
    }

    try {
      const profile = await getUserProfile(user.uid);

      if (!profile) {
        window.location.href = "./index.html";
        return;
      }

      onReady(user, profile);
    } catch (error) {
      console.error("Error cargando perfil:", error);
      window.location.href = "./index.html";
    }
  });
}

export async function logoutAndRedirect() {
  await signOut(auth);
  window.location.href = "./index.html";
}