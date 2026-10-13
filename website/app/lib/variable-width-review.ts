import { useEffect, useMemo, useSyncExternalStore } from "react";
import featured from "../data/variable-width-gallery.json";
import library from "../data/variable-width-library.json";

const key = "variable-width-review-v1";
const event = "variable-width-review-change";
const empty = '{"added":[],"removed":[],"hidden":[]}';
let fallback = empty;
const known = new Set([...featured, ...library]);
const libraryNames = new Set(library);
const marquee = ["check","calendar_clock","airplane_top","beach","boat_sail","route_waypoints","backpack","bed","maximize","cloud_sun"];
const revision = "profile-fix-20261013";
const revisedIcons = new Set(["shower","download_cloud","wallet","waterfall"]);
type Review = { added: string[]; removed: string[]; hidden: string[]; revision: string };

export function variableWidthIconPath(name: string) {
  return `/variable-width/variable-width-library/${name}.svg`;
}
function snapshot() {
  try { return localStorage.getItem(key) ?? empty; } catch { return fallback; }
}
function parse(raw: string): Review {
  try {
    const data = JSON.parse(raw);
    const names = (value: unknown) => Array.isArray(value) ? [...new Set(value.filter((name): name is string => typeof name === "string" && known.has(name)))] : [];
    return {added:names(data.added),removed:names(data.removed),hidden:names(data.hidden),revision:typeof data.revision === "string" ? data.revision : ""};
  } catch { return {added:[],removed:[],hidden:[],revision:""}; }
}
function subscribe(notify: () => void) {
  const storage = (e: StorageEvent) => { if (e.key === key || e.key === null) notify(); };
  window.addEventListener(event, notify); window.addEventListener("storage", storage);
  return () => { window.removeEventListener(event, notify); window.removeEventListener("storage", storage); };
}
function update(change: (review: Review) => Review) {
  fallback = JSON.stringify(change(parse(snapshot())));
  try { localStorage.setItem(key, fallback); } catch { /* Retain session choices if storage is unavailable. */ }
  window.dispatchEvent(new Event(event));
}
export function useVariableWidthReview() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => empty);
  useEffect(() => {
    if (parse(snapshot()).revision !== revision) {
      // Old rejection of an incomplete asset does not hide its requested fix.
      // Apply once so a fresh deletion of the repaired icon still persists.
      update(review => review.revision === revision ? review : ({...review,hidden:review.hidden.filter(name => !revisedIcons.has(name)),revision}));
    }
  }, [raw]);
  const state = useMemo(() => {
    const review = parse(raw), hidden = new Set(review.hidden), removed = new Set(review.removed);
    const visibleHome = (name: string) => libraryNames.has(name) && !hidden.has(name) && !removed.has(name);
    return {
      addedHomeIcons:review.added.filter(visibleHome),
      homeIcons:[...new Set([...featured,...review.added])].filter(visibleHome),
      marqueeIcons:[...new Set([...marquee,...review.added])].filter(visibleHome),
      libraryIcons:library.filter(name => !hidden.has(name)),
    };
  }, [raw]);
  return state;
}
