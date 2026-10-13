import { useVariableWidthTheme } from "../lib/variable-width-theme";
import { Tabs } from "@cloudflare/kumo/components/tabs";
import { useVariableWidthLanguage } from "../lib/variable-width-language";
import { useEffect, useRef, useState } from "react";
import { VariableWidthCursorTrail } from "../components/VariableWidthCursorTrail";
import { VariableWidthHeroTitle } from "../components/VariableWidthHeroTitle";
import { AlgorithmDemo } from "../components/AlgorithmDemo";
import { VariableWidthDocs } from "../components/VariableWidthDocs";
import { Button, LinkButton } from "@cloudflare/kumo/components/button";
import { Text } from "@cloudflare/kumo/components/text";
import { SiteLink as Link } from "../components/ui/SiteLink";
import { pageMeta } from "../lib/meta";
import { useVariableWidthReview, variableWidthIconPath } from "../lib/variable-width-review";
import { VariableWidthGallery } from "../components/VariableWidthGallery";
import styles from "../styles/variable-width.module.css";

export const meta = () => pageMeta("Variable Width SVG", "Controlled width variation for SVG icon strokes.", "/variable-width");

function InstallCommand() {
  const { t } = useVariableWidthLanguage();
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const command = "npm install @weihuasongguo/variable-width-svg";
  return <div className={`${styles.installCommand} rounded-md bg-kumo-recessed ring ring-kumo-hairline/70`}><code>{command}</code><Button variant="secondary" size="sm" shape="square" className="size-5" aria-label={t(failed ? "复制失败" : copied ? "已复制" : "复制命令")} title={t(failed ? "复制失败" : copied ? "已复制" : "复制命令")} aria-live="polite" onClick={async () => {
    try { await navigator.clipboard.writeText(command); setCopied(true); setFailed(false); }
    catch { setFailed(true); }
  }}><img src={`/variable-width/variable-width-library/${copied ? "check" : "copy"}.svg`} width={14} height={14} alt="" /></Button></div>;
}

function MarqueeRow() {
  const { marqueeIcons } = useVariableWidthReview();
  const rowRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const row = rowRef.current;
    const viewport = row?.parentElement;
    if (!row || !viewport) return;
    const icons = Array.from(row.querySelectorAll<HTMLImageElement>("img"));
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let frame = 0;
    let visible = false;
    let offsets: number[] = [];
    let center = 0;
    let radius = 1;
    let previousLeft = NaN;
    const measure = () => {
      const bounds = viewport.getBoundingClientRect();
      const left = row.getBoundingClientRect().left;
      center = bounds.left + bounds.width / 2;
      radius = bounds.width / 2;
      offsets = icons.map(icon => {
        const cell = icon.parentElement!.getBoundingClientRect();
        return cell.left - left + cell.width / 2;
      });
      previousLeft = NaN;
    };
    const draw = () => {
      const left = row.getBoundingClientRect().left;
      if (left === previousLeft) return;
      previousLeft = left;
      icons.forEach((icon, index) => {
        const distance = Math.min(1, Math.abs(left + offsets[index] - center) / radius);
        const scale = 0.85 + 0.25 * Math.cos(distance * Math.PI / 2) ** 2;
        icon.style.transform = `scale(${scale})`;
      });
    };
    const tick = () => { draw(); frame = requestAnimationFrame(tick); };
    const sync = () => {
      cancelAnimationFrame(frame);
      if (visible && !document.hidden) {
        measure(); draw();
        if (!motion.matches) frame = requestAnimationFrame(tick);
      }
    };
    const resize = new ResizeObserver(sync);
    resize.observe(viewport);
    const intersection = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); });
    intersection.observe(viewport);
    document.addEventListener("visibilitychange", sync);
    motion.addEventListener("change", sync);
    return () => {
      cancelAnimationFrame(frame);
      resize.disconnect(); intersection.disconnect();
      document.removeEventListener("visibilitychange", sync);
      motion.removeEventListener("change", sync);
    };
  }, [marqueeIcons]);
  return <div ref={rowRef} className={styles.marqueeRow} style={{animationDuration:`${Math.max(1,marqueeIcons.length)*7}s`}}>{[0, 1].map(copy => <div className={styles.marqueeGroup} key={copy}>{marqueeIcons.map(name => <span className={styles.marqueeIcon} key={name}><img src={variableWidthIconPath(name)} alt="" width="72" height="72" /></span>)}</div>)}</div>;
}

export function VariableWidthPage({ view = "home" }: { view?: "home" | "icons" | "docs" }) {
  const { language, setLanguage, t } = useVariableWidthLanguage();
  const { theme, setTheme } = useVariableWidthTheme();
  const headerRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const header = headerRef.current;
    if (!header) return;
    const measure = () => header.parentElement?.style.setProperty("--project-header-height", `${header.getBoundingClientRect().height}px`);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(header);
    return () => observer.disconnect();
  }, []);
  return <main lang={language === "zh" ? "zh-CN" : "en"} id="main" className={styles.page}>
    <VariableWidthCursorTrail />
    <header ref={headerRef} className={styles.projectHeader}><span aria-hidden="true" className={styles.headerRails} /><Link className={styles.projectBrand} to="/variable-width" aria-label="variable-width"><img src="/variable-width/variable-width-library/motorcycle.svg" width={28} height={28} alt="" /></Link>
    <div className={styles.headerActions}><nav className={styles.projectNav} aria-label={t("项目导航")}><Link to="/variable-width/icons">{t("图标")}</Link><Link to="/variable-width/docs">{t("文档")}</Link></nav><div className={styles.languageToggle}><div className={styles.navIcons}><Link href="https://www.producthunt.com/products/variable-width-svg?launch=variable-width-svg" aria-label="Product Hunt" title="Product Hunt"><img src="/variable-width/variable-width-navigation/product-hunt.svg" width={20} height={20} alt="" /></Link><Link href="https://github.com/weihuasongguo-boop/variable-width-svg" aria-label="GitHub" title="GitHub"><img src="/variable-width/variable-width-navigation/github.svg" width={20} height={20} alt="" /></Link><Button variant="ghost" size="sm" aria-label={theme === "dark" ? t("切换到浅色模式") : t("切换到深色模式")} title={theme === "dark" ? t("切换到浅色模式") : t("切换到深色模式")} onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? <img src="/variable-width/variable-width-navigation/sun.svg" width={20} height={20} alt="" /> : <img src="/variable-width/variable-width-navigation/moon.svg" width={20} height={20} alt="" />}</Button></div><Tabs size="sm" variant="segmented" value={language} onValueChange={value=>{setLanguage(value === "zh" ? "zh" : "en");}} tabs={[{value:"en",label:"EN"},{value:"zh",label:"中文"}]} aria-label={t("语言")} /></div></div></header>
    {view === "home" && <><section className={styles.hero} aria-labelledby="variable-title">

      <VariableWidthHeroTitle language={language} />
      <p className={styles.heroCopy}>{t("从描边路径到可变线宽轮廓。")}<br />{t("平滑过渡，保留图形的比例与对称。")}</p>
      <InstallCommand />
    </section>
    <section className={styles.marquee} aria-label={t("可变线宽图标展示")}><MarqueeRow /></section></>}
    {view === "home" && <><section className={styles.notes} id="algorithm" aria-label={t("算法说明")}><div className={styles.algorithmContent}><section className={styles.algorithmRow}><AlgorithmDemo mode="width" /><div><h3>{t("从中心线定义宽度")}</h3><p>{t("保留原图中心线，用宽度配方控制粗细。圆、椭圆和圆角矩形先转成路径，再生成轮廓；变化由配方明确指定。")}</p></div></section><section className={styles.algorithmRow}><AlgorithmDemo mode="interpolation" /><div><h3>{t("按弧长平滑过渡")}</h3><p>{t("按路径实际长度分配宽度，用无过冲的 PCHIP 插值平滑连接。端点缓动限制在笔画尺度内，减少细颈和鼓包。")}</p></div></section><section className={styles.algorithmRow}><AlgorithmDemo mode="bend" /><div><h3>{t("根据笔画结构选择变化")}</h3><p>{t("对勾、折角箭头和 L 形指针在拐点最粗，两端收细。短线简化变化，极短线保留等粗；组合笔画协调连接处的宽度。")}</p></div></section><section className={styles.algorithmRow}><AlgorithmDemo mode="endpoint" /><div><h3>{t("处理转角与连接端点")}</h3><p>{t("沿中心线两侧偏移生成轮廓，清理内角重叠、小回环和局部突变。连接端点向内回退一小段，保留圆头与粗细变化，减少出头。")}</p></div></section><section className={styles.algorithmRow}><AlgorithmDemo mode="symmetry" /><div><h3>{t("保持对称与共用形状")}</h3><p>{t("约束对称中心线，并检查轮廓的镜像关系。日历等同族图标复用基础形状，保留原有开口、比例和路径方向。")}</p></div></section><section className={styles.algorithmRow}><AlgorithmDemo mode="bounds" /><div><h3>{t("用曲线表达，补偿可见边界")}</h3><p>{t("用三次 Bézier 曲线拟合轮廓，在误差范围内合并节点，复杂转角保留更多锚点。再按曲线极值补偿可见宽高与基线；补偿可能改变局部线宽。")}</p></div></section><section className={styles.algorithmRow}><AlgorithmDemo mode="fitting" /><div><h3>{t("可调整的部分与当前边界")}</h3><p>{t("宽度、方向、端点缓动、平顺和拟合容差均可调整。更强的平顺可能改变局部形状，更小的容差会增加节点；复杂自交、回环和变换仍需检查。")}</p></div></section></div></section>

    </>}
    {(view === "home" || view === "icons") && <>{view === "icons" && <header className={styles.subpageHeading}><h1>{t("图标")}</h1><p>{t("这里是一小批用算法生成的图标示例。你也可以选择成熟图标库中的描边图标，按需生成自己的可变线宽版本，不必局限于这些案例。")}</p></header>}<section className={styles.figures} id="figures" aria-label={t("图标预览")}>
      {view === "home" && <header className={styles.galleryHeading}>
        <Text as="h2" variant="heading" size="lg">{t("精选")}</Text>
        <LinkButton href="/variable-width/icons" variant="secondary" size="sm">{t("更多图标")}</LinkButton>
      </header>}
      <VariableWidthGallery full={view === "icons"} />
    </section>
    </>}
    {view === "docs" && <VariableWidthDocs />}
    <footer className={styles.projectFooter} aria-label={t("项目页脚")}><span>variable-width</span><span>weihua</span></footer>

  </main>;
}

export default function VariableWidth() { return <VariableWidthPage />; }
