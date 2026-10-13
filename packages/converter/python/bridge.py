#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'engine'
sys.path.insert(0, str(ROOT))

import generate  # noqa: E402


def main():
    payload = json.load(sys.stdin)
    result, measurements = generate.derive(
        payload['source'],
        payload['specs'],
        payload.get('amount', 1),
        payload.get('settings') or json.loads((ROOT / 'engine-v2.json').read_text()),
        payload.get('geometryGuard', True),
        payload.get('compensateBounds', False),
    )
    json.dump({'svg': result, 'measurements': measurements}, sys.stdout)


if __name__ == '__main__':
    main()
