# @weihuasongguo/variable-width-svg

Experimental Node API and CLI for converting stroked SVG paths into filled,
variable-width outlines. Supply an explicit width recipe for each path you want
to convert. The engine does not infer design intent from arbitrary icons.

## Requirements

- Node.js 20 or later.
- Python 3.10 or later, available as `python3`. Set the `PYTHON` environment
  variable to an alternative Python executable if needed.

The Python engine and default settings are bundled. No pip dependencies are
required. Conversion runs in a subprocess on your computer or server; it does
not run inside a browser.

## Install

```sh
npm install @weihuasongguo/variable-width-svg
```

## Convert an SVG

```js
import { convertSvg } from '@weihuasongguo/variable-width-svg';

const source = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M4 12 H20" fill="none" stroke="black" stroke-width="1.5"
    stroke-linecap="round" stroke-linejoin="round" />
</svg>`;

const result = await convertSvg(source, {
  specs: {
    '0': {
      axis: 'length',
      interpolation: 'smoothstep',
      stops: [[0, 1.2], [1, 0.8]]
    }
  },
  compensateBounds: true
});

console.log(result.svg);
console.log(result.measurements);
```

`specs` keys are zero-based path indexes after basic shape normalization. Each
stop pairs a position along the path (0–1) with a target stroke width in SVG units. Paths without
a recipe remain unchanged. `amount` defaults to 1. `geometryGuard` defaults to
true; `compensateBounds` defaults to false. The bundled engine settings are used
when `settings` is omitted. Passing `settings` replaces the complete settings
object; it is not a partial override.

Boundary compensation aligns each path's visible bounds with its source.
It may change local widths and does not guarantee correct joins between paths.
The returned `measurements` describes converted paths; an empty list means no
paths were converted. Conversion errors reject the promise.

## CLI

The included example is a complete input file:

```sh
variable-width-svg node_modules/@weihuasongguo/variable-width-svg/examples/line.json > output.json
```

The command reads a JSON file with `source` and the same options as the API.
It writes JSON containing `svg` and `measurements` to standard output. Save the
`svg` field as an `.svg` file to use the generated outline.

## Supported scope

This is a 0.1 experimental engine designed around 24 × 24 icon geometry. It
supports selected absolute path commands (`M`, `L`, `H`, `V`, `C`, `Z`) and
normalizes supported basic shapes such as circles, ellipses and rounded
rectangles. Unsupported path commands, transforms and complex geometry may
fail. Review every result, especially tight corners, overlaps and small details.
It is not a general-purpose SVG renderer or sanitizer.

## Licenses

Algorithm code: Apache-2.0, included in `LICENSE`. Documentation: CC BY 4.0,
see `LICENSE-DOCS`. No third-party icon collection is included. You are
responsible for the rights to source icons you convert.
