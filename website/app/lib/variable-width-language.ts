import { useSyncExternalStore } from "react";
import english from "../data/variable-width-en.json";

type Language = "en" | "zh";
const key = "variable-width-language";
const event = "variable-width-language-change";
let fallback: Language = "en";
const translations: Record<string, string> = english;

function snapshot(): Language {
  try {
    const saved = window.localStorage.getItem(key);
    return saved === "zh" ? "zh" : saved === "en" ? "en" : fallback;
  } catch { return fallback; }
}
function subscribe(notify: () => void) {
  const onStorage = (e: StorageEvent) => { if (e.key === key || e.key === null) notify(); };
  window.addEventListener(event, notify);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(event, notify);
    window.removeEventListener("storage", onStorage);
  };
}
export function useVariableWidthLanguage() {
  const language = useSyncExternalStore(subscribe, snapshot, () => "en" as Language);
  const setLanguage = (value: Language) => {
    fallback = value;
    try { window.localStorage.setItem(key, value); } catch { /* Keep the selection for this session. */ }
    window.dispatchEvent(new Event(event));
  };
  const t = (source: string) => language === "en" ? translations[source] ?? source : source;
  return { language, setLanguage, t };
}
