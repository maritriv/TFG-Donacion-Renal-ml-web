export function translateFirebaseError(code) {
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