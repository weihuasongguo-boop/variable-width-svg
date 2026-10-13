import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Button } from "@cloudflare/kumo/components/button";
import { useVariableWidthLanguage } from "../lib/variable-width-language";
import { useVariableWidthReview, variableWidthIconPath } from "../lib/variable-width-review";
import styles from "../styles/variable-width.module.css";

type Anchor = { name: string; row: number; column: number };

// Reserve the clicked cell before packing its neighbours. The rightmost column
// grows leftward, preserving its top-right corner instead of moving to a new row.
function arrange(icons: readonly string[], selected: string | null, columns: number, anchor: Anchor | null, previous: Anchor | null) {
  const occupied = new Set<string>();
  const pinned = new Map<string, {row:number;column:number;span:number}>();
  const reserve = (name: string, row: number, column: number, span: number) => {
    pinned.set(name, {row,column,span});
    for (let y=row;y<row+span;y++) for(let x=column;x<column+span;x++) occupied.add(`${y}:${x}`);
  };
  if (anchor && icons.includes(anchor.name)) {
    const span = selected ? 2 : 1;
    let row = anchor.row, column = Math.min(anchor.column, columns-span);
    if (selected && previous) {
      // Prefer downward expansion; use another corner if it would cover the
      // cell of the icon that is simultaneously collapsing.
      const candidates = [[row,column],[row,anchor.column-1],[row-1,column],[row-1,anchor.column-1]];
      const free = candidates.find(([r,c]) => r>=0 && c>=0 && c+span<=columns &&
        !(previous.row>=r && previous.row<r+span && previous.column>=c && previous.column<c+span));
      if (free) [row,column]=free;
    }
    reserve(anchor.name,row,column,span);
  }
  if (selected && previous && icons.includes(previous.name) && !occupied.has(`${previous.row}:${previous.column}`)) reserve(previous.name,previous.row,previous.column,1);
  let slot=0;
  return icons.map(name => {
    let cell = pinned.get(name);
    if (!cell) {
      while(occupied.has(`${Math.floor(slot/columns)}:${slot%columns}`)) slot++;
      cell={row:Math.floor(slot/columns),column:slot%columns,span:1};
      reserve(name,cell.row,cell.column,1);
    }
    return {name,...cell,atRight:cell.column+cell.span===columns};
  });
}

export function VariableWidthGallery({ full = false }: { full?: boolean }) {
  const review = useVariableWidthReview();

  const imagePath = full ? (name: string) => `/variable-width/variable-width-library/${name}.svg` : variableWidthIconPath;
  const { t } = useVariableWidthLanguage();
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(preference.matches);
    update(); preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);
  const transition = { duration: reducedMotion ? 0 : 0.38, ease: [0.22, 1, 0.36, 1] as const };
  const [selected, setSelected] = useState<string | null>(null);
  const [columns, setColumns] = useState(6);
  const icons = useMemo(() => full ? review.libraryIcons
    : [...new Set([...review.addedHomeIcons, ...review.homeIcons])].slice(0, columns * 6),
    [full, review.libraryIcons, review.homeIcons, review.addedHomeIcons, columns]);
  const columnsRef = useRef(6);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [previous, setPrevious] = useState<Anchor | null>(null);
  const cells = useMemo(() => arrange(icons, selected, columns, anchor, previous), [icons, selected, columns, anchor, previous]);
  const [status, setStatus] = useState("");
  const sequence = useRef(0);
  const buttons = useRef(new Map<string, HTMLButtonElement>());
  const lastPositions = useRef(new Map<string, string>());
  useLayoutEffect(() => {
    const animations: Animation[] = [];
    cells.forEach(({name,row,column}) => {
      const position = `${row}:${column}`;
      const last = lastPositions.current.get(name);
      const image = buttons.current.get(name)?.querySelector("img");
      if (last && last !== position && !reducedMotion && name !== anchor?.name && name !== previous?.name && image) {
        animations.push(image.animate([{opacity:0.25},{opacity:1}], {duration:160,easing:"ease-out"}));
      }
      lastPositions.current.set(name,position);
    });
    return () => animations.forEach(animation => animation.cancel());
  }, [cells, reducedMotion, anchor, previous]);
  function select(name: string | null) {
    sequence.current++;
    setStatus("");
    if (name) {
      const cell = cells.find(cell => cell.name === name)!;
      setPrevious(selected ? anchor : null);
      setAnchor({name,row:cell.row,column:cell.column});
    } else setPrevious(null);
    setSelected(name);
  }
  useEffect(() => {
    if (selected && !icons.includes(selected)) {
      sequence.current++; setSelected(null); setAnchor(null); setPrevious(null); setStatus("");
    }
  }, [icons, selected]);
  useEffect(() => {
    const update = () => {
      const next = window.innerWidth <= 640 ? 3 : window.innerWidth <= 800 ? 2 : 6;
      if (columnsRef.current !== next) {
        columnsRef.current = next;
        setColumns(next); setSelected(null); setAnchor(null); setPrevious(null);
      }
    };
    update(); window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  useEffect(() => {
    if (!selected) return;
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") { buttons.current.get(selected)?.focus({ preventScroll: true }); select(null); } };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [selected, anchor, previous, columns]);
  async function copy(name: string) {
    const request = ++sequence.current;
    try {
      const response = await fetch(imagePath(name));
      if (!response.ok) throw new Error("SVG request failed");
      const svg = await response.text();
      await navigator.clipboard.writeText(svg);
      if (sequence.current === request) setStatus("已复制");
    } catch {
      if (sequence.current === request) setStatus("复制失败，请检查剪贴板权限。");
    }
  }
  return <div className={styles.gallerySurface}><div className={styles.grid}>
    {cells.map(({name, row, column, span, atRight}) => <article
      key={name} className={`${styles.card} ${span === 2 ? styles.expandedCard : ""}`}
      data-gallery-icon={name} data-right-edge={atRight || undefined}
      style={{gridRow:`${row + 1} / span ${span}`,gridColumn:`${column + 1} / span ${span}`}}>
      <Button variant="ghost" className={styles.figureOpen}
        ref={element => { if (element) buttons.current.set(name, element); else buttons.current.delete(name); }}
        aria-label={`${t(span === 2 ? "收起" : "放大")} ${name}`} aria-expanded={span === 2} data-cursor={span === 2 ? "shrink" : "enlarge"}
        onClick={() => select(selected === name ? null : name)}>
        <motion.img layout transition={{layout: name === anchor?.name || name === previous?.name ? transition : {duration:0}}} src={imagePath(name)} alt="" width={span === 2 ? 160 : 48} height={span === 2 ? 160 : 48} loading="lazy" />
      </Button>
      <AnimatePresence initial={false}>{span === 2 && <motion.div key="actions" className={styles.galleryActions}
        initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}
        transition={{duration:reducedMotion ? 0 : 0.14, delay:reducedMotion ? 0 : 0.08}}>
        <Button variant="secondary" size="sm" aria-live="polite" onClick={() => void copy(name)}>{t(status || "复制 SVG")}</Button>
      </motion.div>}</AnimatePresence>
    </article>)}
  </div></div>;
}
