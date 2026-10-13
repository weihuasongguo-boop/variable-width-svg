import { VariableWidthPage } from "./variable-width";
import { pageMeta } from "../lib/meta";
export const meta = () => pageMeta("Icons · Variable Width SVG", "Controlled width variation for SVG icon strokes.", "/variable-width/icons");
export default function Page() { return <VariableWidthPage view="icons" />; }
