# 0.1.0 local release preparation

Verified on 2026-10-13. Published to npm and public installation verified.

- `prepack` copies the current algorithm modules, default settings and licenses
  from the study into the package. The study remains the source of truth.
- Runtime imports only bundled engine files. Default settings support the README
  boundary-compensation example without a checkout of this repository.
- Explicit file allowlist includes 13 files (~25 kB compressed), excluding icon
  collections, local paths, reports and Python bytecode caches.
- `npm run test:package` packs, installs into a fresh temporary project with
  install scripts disabled, and checks the installed API and CLI. It covers
  conversion with/without compensation, invalid input and missing Python.
- Final package verification: Node 24.19.0, Python 3.12.14, macOS. Algorithm
  regression suite: 58 passed. Node 20, Python 3.10 and other operating systems
  were not independently exercised in this check.
- README includes complete API/CLI examples, runtime requirements and limits.
- Published with account `weihuasongguo` after browser authentication. Public
  registry now returns version `0.1.0` and the expected CLI entry.
- Installed `@weihuasongguo/variable-width-svg@0.1.0` from the public npm registry
  into a fresh temporary project with install scripts disabled. API conversion
  and the installed CLI both passed using Node 24 and Python 3.12.
- Package URL: https://www.npmjs.com/package/@weihuasongguo/variable-width-svg


To repeat local verification from this directory:

```sh
npm run test:package
```

This produces the tarball and prints the isolated install directory. It does
not publish. The prepack step must run from the source checkout; installed users
can use the already-bundled engine without running it.
