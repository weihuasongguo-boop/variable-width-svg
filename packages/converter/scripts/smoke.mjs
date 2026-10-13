import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { convertSvg } from '../src/index.mjs';
const input = JSON.parse(await fs.readFile(new URL('../examples/line.json', import.meta.url), 'utf8'));
const result = await convertSvg(input.source, input);
assert.ok(result.svg.includes('<svg'));
assert.equal(result.measurements.length, 1);
console.log('API conversion with bundled default settings passed');
