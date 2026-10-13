import {Links,Meta,Outlet,Scripts,ScrollRestoration} from 'react-router';
import type {ReactNode} from 'react';
import {MotionConfig} from 'motion/react';
import {useVariableWidthTheme,variableWidthThemeScript} from './lib/variable-width-theme';
import {useVariableWidthLanguage} from './lib/variable-width-language';
import '@cloudflare/kumo/styles/standalone';
import './styles/global.css';
export function Layout({children}:{children:ReactNode}){const {language}=useVariableWidthLanguage();const {theme}=useVariableWidthTheme();return <html lang={language==='en'?'en':'zh-CN'} data-mode={theme} suppressHydrationWarning><head><meta charSet="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><link rel="icon" type="image/svg+xml" href="/variable-width/variable-width-library/motorcycle.svg"/><script dangerouslySetInnerHTML={{__html:variableWidthThemeScript}}/><Meta/><Links/></head><body data-project-theme="monochrome"><a className="skip-link" href="#main">{language==='en'?'Skip to content':'跳至内容'}</a>{children}<ScrollRestoration/><Scripts/></body></html>}
export default function App(){return <MotionConfig reducedMotion="user"><div className="site-root workspace-shell"><Outlet/></div></MotionConfig>}
export function ErrorBoundary(){return <main id="main" className="standalone-error"><h1>Unable to load this page</h1><a href="/variable-width">Variable Width</a></main>}
