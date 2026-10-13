import { VariableWidthPage } from "./variable-width";
import { pageMeta } from "../lib/meta";
export const meta = () => pageMeta("Docs · Variable Width SVG", "Controlled width variation for SVG icon strokes.", "/variable-width/docs");
export default function Page() { return <VariableWidthPage view="docs" />; }
