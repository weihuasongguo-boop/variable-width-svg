import {rename,rm,writeFile} from 'node:fs/promises';
const out=new URL('../build/client/',import.meta.url);
for(const route of ['variable-width','variable-width/icons','variable-width/docs'])await rename(new URL(route+'/index.html',out),new URL(route+'.html',out));
for(const file of ['index.html','__spa-fallback.html'])await rm(new URL(file,out),{force:true});
await writeFile(new URL('404.html',out),'<!doctype html><html lang="en"><meta charset="utf-8"><title>Page not found · Variable Width</title><h1>Page not found</h1><a href="/variable-width">Variable Width</a></html>');
await writeFile(new URL('variable-width/sitemap.xml',out),'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+['','/icons','/docs'].map(p=>'<url><loc>https://weihuasongguo.com/variable-width'+p+'</loc></url>').join('')+'</urlset>');
await writeFile(new URL('_headers',out),'/variable-width/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n');
