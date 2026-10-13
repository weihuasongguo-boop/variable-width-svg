import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const bridge = path.join(packageRoot, 'python', 'bridge.py');

function runPython(payload) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.env.PYTHON || 'python3', [bridge], {
      cwd: packageRoot,
      stdio: ['pipe', 'pipe', 'pipe']
    });
    let output = '';
    let errors = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk) => { output += chunk; });
    child.stderr.on('data', (chunk) => { errors += chunk; });
    child.once('error', (error) => reject(new Error(`Unable to start Python 3.10+. Install python3 or set PYTHON to its executable. ${error.message}`)));
    child.stdin.on('error', reject);
    child.once('close', (code) => {
      if (code !== 0) {
        reject(new Error(errors.trim() || `variable-width-svg exited with code ${code}`));
        return;
      }
      try { resolve(JSON.parse(output)); }
      catch (error) { reject(new Error(`Invalid engine response: ${error.message}`)); }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

export async function convertSvg(source, options = {}) {
  if (typeof source !== 'string' || !source.includes('<svg')) {
    throw new TypeError('convertSvg(source, options) expects an SVG string.');
  }
  if (!options.specs || typeof options.specs !== 'object') {
    throw new TypeError('options.specs must map normalized path indexes to width recipes.');
  }
  return runPython({ ...options, source });
}

export const version = '0.1.0';
