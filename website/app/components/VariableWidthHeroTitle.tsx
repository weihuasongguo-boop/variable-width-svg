import { useEffect, useRef } from "react";
import styles from "../styles/variable-width.module.css";

function Characters({ text }: { text: string }) {
  return <>{Array.from(text).map((character, index) => <span data-weight-char="" key={index}>{character}</span>)}</>;
}

export function VariableWidthHeroTitle({ language }: { language: "en" | "zh" }) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const frameRef = useRef(0);
  const enterTimerRef = useRef<number | undefined>(undefined);
  const centersRef = useRef<{element:HTMLElement;x:number;y:number}[]>([]);
  useEffect(() => {
    const title = titleRef.current;
    if (!title) return;
    let active = true;
    const measure = () => {
      const origin = title.getBoundingClientRect();
      centersRef.current = Array.from(title.querySelectorAll<HTMLElement>("[data-weight-char]")).map(element => {
        const bounds = element.getBoundingClientRect();
        return {element,x:bounds.left-origin.left+bounds.width/2,y:bounds.top-origin.top+bounds.height/2};
      });
    };
    measure();
    const resize = new ResizeObserver(measure); resize.observe(title);
    void document.fonts.ready.then(() => { if (active) measure(); });
    return () => { active = false; resize.disconnect(); cancelAnimationFrame(frameRef.current); window.clearTimeout(enterTimerRef.current); delete title.dataset.weightEntering; };
  }, [language]);
  const reset = () => {
    cancelAnimationFrame(frameRef.current);
    window.clearTimeout(enterTimerRef.current);
    if (titleRef.current) delete titleRef.current.dataset.weightEntering;
    centersRef.current.forEach(({element}) => element.style.removeProperty("--hover-weight"));
  };
  return <h1 id="variable-title" ref={titleRef} className={styles.hoverTitle}
    onPointerEnter={event => {
      if (event.pointerType !== "mouse" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      window.clearTimeout(enterTimerRef.current);
      event.currentTarget.dataset.weightEntering = "";
      enterTimerRef.current = window.setTimeout(() => {
        if (titleRef.current) delete titleRef.current.dataset.weightEntering;
      }, 140);
    }}
    onPointerMove={event => {
      if (event.pointerType !== "mouse" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const {clientX,clientY} = event;
      cancelAnimationFrame(frameRef.current);
      frameRef.current = requestAnimationFrame(() => {
        const origin = titleRef.current?.getBoundingClientRect();
        if (!origin) return;
        centersRef.current.forEach(({element,x,y}) => {
          const distance = Math.hypot(clientX-origin.left-x,clientY-origin.top-y);
          const influence = Math.max(0,1-distance/90);
          element.style.setProperty("--hover-weight", `${(300+influence**1.5*(language === "en" ? 700 : 400)).toFixed(1)}`);
        });
      });
    }} onPointerLeave={reset} onPointerCancel={reset}>
    {language === "zh" ? <><Characters text="为图标，" /><br /><Characters text="添一点" /><Characters text="粗细变化" /><Characters text="。" /></> : <><Characters text="A little " /><Characters text="variation" /><Characters text="." /><br /><Characters text="For your SVG icons." /></>}
  </h1>;
}
