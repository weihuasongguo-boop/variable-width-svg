"""Generate the navigation mark with the same width range as the GitHub icon."""
import json
from pathlib import Path
import sys
from normalize_strokes import canonical
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/converter/python/engine'))
import generate
source = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
<path d="M9 17V7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
<path d="M9 7H13C14.656854 7 16 8.343146 16 10C16 11.656854 14.656854 13 13 13H9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''
specs = {
 '0': {'axis':'length','interpolation':'pchip','stops':[[0,.825],[.5,1.875],[1,.825]]},
 '1': {'axis':'length','interpolation':'pchip','stops':[[0,.825],[1,1.5]]},
 '2': {'axis':'length','interpolation':'pchip','stops':[[0,1.5],[.5,1.875],[1,1.5]]},
}
settings=json.loads((ROOT/'packages/converter/python/engine/engine-v2.json').read_text())
svg,measurements=generate.derive(canonical(source),specs,1,settings,compensate_bounds=True)
assert len(measurements)==3
assert all(m['maxWidth']>m['minWidth'] for m in measurements)
theme='<style data-variable-width-theme="true">:root{color:#171717}@media(prefers-color-scheme:dark){:root{color:#c6c6c6}}</style>'
(ROOT/'website/public/variable-width/variable-width-navigation/product-hunt.svg').write_text(svg.replace('>','>'+theme,1))
print('Converted all 3 paths into variable-width outlines')
