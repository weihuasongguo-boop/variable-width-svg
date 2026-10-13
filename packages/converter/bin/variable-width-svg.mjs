#!/usr/bin/env node
import fs from 'node:fs/promises';
import { convertSvg } from '../src/index.mjs';

const inputPath = process.argv[2];
if (!inputPath) {
  console.error('Usage: variable-width-svg input.json');
  process.exit(1);
}
const input = JSON.parse(await fs.readFile(inputPath, 'utf8'));
const output = await convertSvg(input.source, input);
process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
