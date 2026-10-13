"""Reproduce reviewed icon fixes using the committed converter engine."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from normalize_strokes import canonical

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/converter/python/engine'))
import generate

THEME = '<style data-variable-width-theme="true">:root{color:#171717}@media(prefers-color-scheme:dark){:root{color:#c6c6c6}}</style>'
settings = json.loads((ROOT / 'packages/converter/python/engine/engine-v2.json').read_text())
records = json.loads((ROOT / 'tools/icon-refinements.json').read_text())
for record in records:
    source = canonical(record['source'])
    svg, measurements = generate.derive(source, record['specs'], 1, settings, compensate_bounds=True)
    assert len(measurements) == len(record['specs']), record['name']
    result = ET.fromstring(svg)
    assert result.get('stroke', 'none') == 'none', 'Filled outlines must not inherit a second stroke'
    svg = svg.replace('>', '>' + THEME, 1)
    (ROOT / 'website/public/variable-width/variable-width-library' / (record['name'] + '.svg')).write_text(svg)
print(f'Generated {len(records)} reviewed icons')
