# Variable Width SVG

Add controlled weight variation to SVG strokes while preserving their structure.

- Website: https://weihuasongguo.com/variable-width
- npm: https://www.npmjs.com/package/@weihuasongguo/variable-width-svg
- Published converter: **0.1.0**, an experimental Node API and CLI requiring Node 20+ and Python 3.10+.

## Repository

- `website/`: React Router + Cloudflare Kumo website, with pre-generated icon examples.
- `packages/converter/`: standalone converter source, Python engine, examples and package tests.

The website's comparisons use pre-generated SVGs. Conversion does not run in the browser.

## Website development

Use Node 24 (tested with 24.19.0) and npm 11.

```sh
cd website
npm ci
npm run dev
```

Open `http://127.0.0.1:4200/variable-width`.

```sh
npm run build
npm run preview
# In a second terminal:
npm run verify
```

The production build contains only the three project pages and their assets. It does not include the author's main website or articles.

## Deployment

The project uses an independent Cloudflare Worker with static assets. Only `weihuasongguo.com/variable-width` and `weihuasongguo.com/variable-width/*` are routed to it. The existing main website remains on its original Cloudflare Pages project. There is no cross-site navigation or automated article notification.

```sh
cd website
npx wrangler login
npm run build
npm run deploy
```

`wrangler.jsonc` contains the route and asset configuration; it contains no credentials. The deploying account must have access to the domain's Cloudflare zone. Remove this Worker's two routes to detach the project without changing the main website. Do not deploy this artifact over the existing Pages project.

## Converter

```sh
cd packages/converter
npm run smoke
npm run test:package
```

Set `PYTHON` to a Python 3.10+ executable if `python3` points to an older version. The engine source is committed under `python/engine`; no external checkout is required. See the package README for API usage and supported SVG inputs. Repository metadata changes do not republish the existing npm version.

## Licenses

Code: Apache-2.0 (`LICENSE`). Documentation: CC BY 4.0 (`LICENSE-DOCS`). Fonts and icon resources retain their respective rights; see `THIRD_PARTY_NOTICES.md`. The code license does not automatically license every source icon or brand mark.
