export const safeLocalStorage =
  typeof window === "undefined" ? null : window.localStorage;
