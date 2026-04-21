import { redirectIfAuthenticated } from "./auth-guard.js";

export function initSession() {
  redirectIfAuthenticated();
}