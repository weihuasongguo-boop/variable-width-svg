import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import styles from "./VariableWidthCursorTrail.module.css";

type Point = { x: number; y: number; time: number };
const SEGMENTS = 24;

export function VariableWidthCursorTrail() {
  const [mounted, setMounted] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  useEffect(() => { setMounted(true); }, []);
  useEffect(() => {
    const svg = svgRef.current;
    if (!mounted || !svg) return;
    const paths = Array.from(svg.querySelectorAll("path"));
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    const mouse = matchMedia("(any-pointer: fine)");
    let points: Point[] = [];
    let frame = 0;
    let hero = false;
    const clear = () => {
      cancelAnimationFrame(frame); frame = 0; points = [];
      paths.forEach(path => path.setAttribute("d", ""));
    };
    const draw = () => {
      frame = 0;
      const now = performance.now();
      points = points.filter(point => now - point.time < 150);
      paths.forEach(path => path.setAttribute("d", ""));
      if (points.length < 2) return;
      const end = points.length - 1;
      for (let i = 1; i <= end; i++) {
        const previous = points[i - 1], point = points[i];
        const next = points[Math.min(end, i + 1)];
        const start = i === 1 ? previous : {x:(previous.x + point.x)/2,y:(previous.y + point.y)/2};
        const finish = i === end ? point : {x:(point.x + next.x)/2,y:(point.y + next.y)/2};
        const path = paths[i - 1];
        path.setAttribute("d", `M${start.x},${start.y} Q${point.x},${point.y} ${finish.x},${finish.y}`);
        path.setAttribute("stroke-width", String(0.3 + (hero ? 2.4 : 1.8) * (i / end) ** 1.3));
        path.setAttribute("opacity", String(0.45 * Math.max(0, 1 - (now - point.time) / 150)));
      }
      frame = requestAnimationFrame(draw);
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType !== "mouse" || reduced.matches || !mouse.matches) { clear(); return; }
      if (event.target instanceof Element && event.target.closest("#variable-title")) { clear(); return; }
      hero = event.target instanceof Element && !!event.target.closest('[aria-labelledby="variable-title"]');
      const point = {x:event.clientX,y:event.clientY,time:performance.now()};
      const previous = points.at(-1);
      if (previous && Math.hypot(point.x-previous.x,point.y-previous.y) < 1) return;
      points.push(point);
      // Bound both sample count and visible length, even during a fast sweep.
      if (points.length > SEGMENTS + 1) points.shift();
      let length = 0;
      for (let i = points.length - 1; i > 0; i--) {
        const a = points[i], b = points[i-1];
        const segment = Math.hypot(a.x-b.x,a.y-b.y);
        if (length + segment > 44) {
          const ratio = (44-length)/segment;
          points = [{x:a.x+(b.x-a.x)*ratio,y:a.y+(b.y-a.y)*ratio,time:b.time},...points.slice(i)];
          break;
        }
        length += segment;
      }
      if (!frame) frame = requestAnimationFrame(draw);
    };
    const visibility = () => { if (document.hidden) clear(); };
    document.addEventListener("pointermove", move, {passive:true});
    document.documentElement.addEventListener("pointerleave", clear);
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("blur", clear);
    window.addEventListener("scroll", clear, {passive:true});
    reduced.addEventListener("change", clear);
    return () => {
      clear(); document.removeEventListener("pointermove", move);
      document.documentElement.removeEventListener("pointerleave", clear);
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("blur", clear); window.removeEventListener("scroll", clear);
      reduced.removeEventListener("change", clear);
    };
  }, [mounted]);
  return mounted ? createPortal(<svg ref={svgRef} className={styles.trail} aria-hidden="true" focusable="false" data-cursor-trail="">
    {Array.from({length:SEGMENTS},(_,index)=><path key={index} fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" />)}
  </svg>, document.body) : null;
}
