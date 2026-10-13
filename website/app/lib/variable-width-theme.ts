import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";
const key = "variable-width-theme";
const event = "variable-width-theme-change";
let fallback: Theme | undefined;
function snapshot(): Theme {
  let saved: string | null = null;
  try { saved = window.localStorage.getItem(key); } catch { /* Use the session preference. */ }
  return saved === "light" || saved === "dark" ? saved : fallback ?? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function subscribe(notify: () => void) {
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onStorage = (e: StorageEvent) => { if (e.key === key || e.key === null) notify(); };
  media.addEventListener("change", notify);
  window.addEventListener(event, notify);
  window.addEventListener("storage", onStorage);
  return () => {
    media.removeEventListener("change", notify);
    window.removeEventListener(event, notify);
    window.removeEventListener("storage", onStorage);
  };
}
export function useVariableWidthTheme() {
  const theme = useSyncExternalStore(subscribe, snapshot, () => "light" as Theme);
  const setTheme = (value: Theme) => {
    fallback = value;
    try { window.localStorage.setItem(key, value); } catch { /* Keep the selection for this session. */ }
    window.dispatchEvent(new Event(event));
  };
  return { theme, setTheme };
}

// Apply the stored/system preference before styles paint. Only this independent project opts in.
export const variableWidthThemeScript = `(()=>{if(!/^\\/lab\\/variable-width(?:\\/|$)/.test(location.pathname))return;let t;try{t=localStorage.getItem("${key}")}catch{}document.documentElement.dataset.mode=t==="light"||t==="dark"?t:matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"})()`;
