# Variable Width SVG

This is an independent public project. Do not import the author's main website, articles, private datasets or machine-specific configuration.

- `website/` is the production React Router/Kumo site. Use existing Kumo components and semantic tokens; project icons are pre-generated SVG assets.
- Public routes and all assets live under `/variable-width`. The original website is a separate Cloudflare Pages project: never replace its deployment.
- Home featured icons and marquee icons must exist in the full library. The featured gallery contains at most six rows at each responsive column count and uses the same SVGs as the library.
- `packages/converter/` contains the self-contained npm package, including its Python engine. Version 0.1.0 is already published; do not republish or increment it without a release request.
- Before publishing website changes: run `npm ci`, `npm run build`, then run `npm run preview` and `npm run verify` in another terminal. Use Node 24.19.0 or a compatible version.
- Converter checks: `npm run test:package`, with Python 3.10+ (3.12 tested).
- Public source must not contain credentials, internal npm registry URLs, local absolute paths or unrelated project files. Use the committed public npm registry configuration and lockfile.
- Follow third-party font and icon notices. The code license does not supersede asset licenses.
