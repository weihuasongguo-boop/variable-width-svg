import { execFileSync } from 'node:child_process';
import { mkdtemp, readFile, writeFile, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
const root = fileURLToPath(new URL('../', import.meta.url));
const target = await mkdtemp(path.join(tmpdir(), 'variable-width-package-'));
const run = (command, args, cwd = target) => execFileSync(command, args, { cwd, encoding: 'utf8', env: { ...process.env, PYTHONPATH: '', PYTHONNOUSERSITE: '1' } });
run('npm', ['pack', '--pack-destination', target], root);
const tarball = (await readdir(target)).find(file => file.endsWith('.tgz'));
await writeFile(path.join(target, 'package.json'), JSON.stringify({ private: true, type: 'module' }));
run('npm', ['install', '--ignore-scripts', '--no-audit', '--no-fund', path.join(target, tarball)]);
const installed = path.join(target, 'node_modules/@weihuasongguo/variable-width-svg');
const input = JSON.parse(await readFile(path.join(installed, 'examples/line.json'), 'utf8'));
await writeFile(path.join(target, 'input.json'), JSON.stringify(input));
await writeFile(path.join(target, 'verify.mjs'), `
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { convertSvg } from '@weihuasongguo/variable-width-svg';
const input = JSON.parse(await fs.readFile('input.json','utf8'));
for (const compensateBounds of [false, true]) {
 const result = await convertSvg(input.source, {...input, compensateBounds});
 assert.equal(result.measurements.length,1);
 assert.ok(result.svg.includes('fill-rule="evenodd"'));
}
await assert.rejects(convertSvg('invalid', {}), /SVG string/);
await assert.rejects(convertSvg(input.source, {}), /specs/);
const old = process.env.PYTHON; process.env.PYTHON = '/missing-python-for-test';
await assert.rejects(convertSvg(input.source,input), /Unable to start Python/);
if (old === undefined) delete process.env.PYTHON; else process.env.PYTHON=old;
console.log('Installed API and failure cases passed');
`);
console.log(run(process.execPath, ['verify.mjs']));
const result = JSON.parse(run(path.join(target, 'node_modules/.bin/variable-width-svg'), ['input.json']));
assert.equal(result.measurements.length, 1);
assert.ok(result.svg.includes('<svg'));
console.log(`Installed CLI passed. Tarball and isolated install: ${target}`);
