import { useVariableWidthLanguage } from "../lib/variable-width-language";
import { useState } from "react";
import { Tabs } from "@cloudflare/kumo/components/tabs";
import { Switch } from "@cloudflare/kumo/components/switch";
import demoAssets from "../data/variable-width-demos.json";
import styles from "./AlgorithmDemo.module.css";

export type DemoMode = keyof typeof demoAssets;
type Asset = { src: string; nodes?: number; nodesSrc?: string };
const assets: Record<DemoMode, { icon: string; variants: Record<string, Asset> }> = demoAssets;
const config: Record<DemoMode, { title: string; initial: string; label: string; options?: Record<string, string> }> = {
  width: {title:"沿路径的粗细过渡", initial:"variable", label:"线宽", options:{original:"原始等粗",variable:"粗细变化"}},
  interpolation: {title:"弧长位置与平滑过渡", initial:"smooth", label:"过渡方式", options:{linear:"匀速",smooth:"平滑"}},
  bend: {title:"拐点处的宽度峰值", initial:"corner", label:"最粗的位置", options:{middle:"路径中点",corner:"真实拐点"}},
  endpoint: {title:"连接端点沿中心线内收", initial:"on", label:"端点内收"},
  symmetry: {title:"镜像约束与对称轮廓", initial:"on", label:"镜像约束"},
  bounds: {title:"恢复原图可见边界", initial:"on", label:"边界补偿"},
  fitting: {title:"曲线分段与控制手柄", initial:"optimized", label:"节点优化", options:{dense:"优化前",optimized:"优化后"}},
};

export function AlgorithmDemo({mode}: {mode: DemoMode}) {
  const { t } = useVariableWidthLanguage();
  const item = config[mode];
  const [variant, setVariant] = useState(item.initial);
  const asset = assets[mode].variants[variant];
  const src = asset.nodesSrc ?? asset.src;
  return <figure className={styles.demo} aria-label={t(item.title)}>
    <div className={styles.iconStage}>
      <img src={src} alt={`${t(item.title)} · ${assets[mode].icon}`} width="240" height="240" loading="lazy" />
    </div>
    <div className={styles.controls}>
      {item.options
        ? <div className={styles.optionGroup} role="group" aria-label={t(item.label)}><span>{t(item.label)}</span><Tabs className={styles.optionTabs} listClassName={styles.optionList} size="sm" variant="segmented" value={variant} onValueChange={setVariant} tabs={Object.entries(item.options).map(([value,label])=>({value,label:t(label)}))}/></div>
        : <div className={styles.optionGroup}><span>{t(item.label)}</span><Switch variant="neutral" aria-label={t(item.label)} checked={variant==="on"} onCheckedChange={checked=>setVariant(checked?"on":"off")}/></div>}
    </div>
  </figure>;
}
