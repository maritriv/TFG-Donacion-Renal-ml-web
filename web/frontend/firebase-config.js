import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import {
  getFirestore
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyBwMvA_tinL4L7DEaxFCxJqCTuL866kHoo",
  authDomain: "tfg-prediccion-70e66.firebaseapp.com",
  projectId: "tfg-prediccion-70e66",
  storageBucket: "tfg-prediccion-70e66.firebasestorage.app",
  messagingSenderId: "12835915973",
  appId: "1:12835915973:web:0d254509c8a0b85dd248ac",
  measurementId: "G-JJ2XEH8C16"
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const db = getFirestore(app);