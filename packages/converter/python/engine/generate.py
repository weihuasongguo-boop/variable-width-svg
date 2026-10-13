"""Small, dependency-free variable-width stroke experiment, not a general SVG engine."""
import hashlib
import html
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import engine
import compensation
import basic_shapes

ROOT = Path(__file__).resolve().parent
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)


def add(a, b): return (a[0] + b[0], a[1] + b[1])
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def mul(a, k): return (a[0] * k, a[1] * k)
def norm(a): return math.hypot(*a)
def unit(a): return mul(a, 1 / norm(a))
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def normal(a): return (-a[1], a[0])


def flatten(d):
    """Parse the selected source paths: absolute M/L/H/V/C/Z; reject anything else."""
    tokens = re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', d)
    points, closed, i, command = [], False, 0, None

    def append(p):
        if not points or norm(sub(p, points[-1])) > 1e-8:
            points.append(p)

    def line(p):
        a = points[-1]
        steps = max(1, math.ceil(norm(sub(p, a)) / .075))
        for j in range(1, steps + 1): append(add(a, mul(sub(p, a), j / steps)))

    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
        if command == 'Z':
            closed = True
            line(points[0])
            break
        count = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6}.get(command)
        if count is None: raise ValueError(f'Unsupported SVG command: {command}')
        values = list(map(float, tokens[i:i + count]))
        if len(values) != count: raise ValueError('Incomplete path')
        i += count
        if command == 'M':
            if points: raise ValueError('Multiple subpaths require separate treatment')
            append(tuple(values)); command = 'L'
        elif command == 'L': line(tuple(values))
        elif command == 'H': line((values[0], points[-1][1]))
        elif command == 'V': line((points[-1][0], values[0]))
        elif command == 'C':
            a = points[-1]; b = tuple(values[:2]); c = tuple(values[2:4]); e = tuple(values[4:])
            steps = max(8, math.ceil((norm(sub(b, a)) + norm(sub(c, b)) + norm(sub(e, c))) / .055))
            for j in range(1, steps + 1):
                t = j / steps; u = 1 - t
                append(tuple(u**3 * a[k] + 3*u*u*t*b[k] + 3*u*t*t*c[k] + t**3*e[k] for k in (0, 1)))
    if closed and norm(sub(points[-1], points[0])) < 1e-8: points.pop()
    return points, closed


def pchip_slopes(stops):
    """Shape-preserving Hermite slopes; weighted harmonic mean / one-sided ends."""
    h = [b[0] - a[0] for a, b in zip(stops, stops[1:])]
    if not h or min(h) <= 0: raise ValueError('Width positions must increase')
    d = [(b[1] - a[1]) / step for a, b, step in zip(stops, stops[1:], h)]
    if len(d) == 1: return [d[0], d[0]]
    slopes = [0.0] * len(stops)
    for i in range(1, len(stops) - 1):
        if d[i-1] * d[i] <= 0: continue
        w1, w2 = 2*h[i] + h[i-1], h[i] + 2*h[i-1]
        slopes[i] = (w1 + w2) / (w1/d[i-1] + w2/d[i])
    def endpoint(h0, h1, d0, d1):
        m = ((2*h0 + h1)*d0 - h0*d1)/(h0 + h1)
        if m*d0 <= 0: return 0.0
        return math.copysign(min(abs(m), 3*abs(d0)), m) if d0*d1 < 0 else m
    slopes[0] = endpoint(h[0], h[1], d[0], d[1])
    slopes[-1] = endpoint(h[-1], h[-2], d[-1], d[-2])
    return slopes


def profile(stops, t, interpolation='smoothstep', flat_ends=False):
    t = max(0, min(1, t))
    slopes = pchip_slopes(stops) if interpolation == 'pchip' else None
    if slopes is not None and flat_ends: slopes[0] = slopes[-1] = 0.0
    for i, ((a, w0), (b, w1)) in enumerate(zip(stops, stops[1:])):
        if t <= b:
            u = (t - a) / (b - a)
            if interpolation == 'pchip':
                return (2*u**3-3*u*u+1)*w0 + (u**3-2*u*u+u)*(b-a)*slopes[i] + (-2*u**3+3*u*u)*w1 + (u**3-u*u)*(b-a)*slopes[i+1]
            if interpolation == 'smoothstep': u = u*u*(3 - 2*u)
            elif interpolation != 'linear': raise ValueError('Unknown interpolation')
            return w0 + (w1 - w0)*u
    return stops[-1][1]


def width_at(spec, point, t, base, amount):
    if spec['axis'] == 'x': t = (point[0] - spec['domain'][0]) / (spec['domain'][1] - spec['domain'][0])
    if spec['axis'] == 'y': t = (point[1] - spec['domain'][0]) / (spec['domain'][1] - spec['domain'][0])
    return base + amount * (profile(spec['stops'], t, spec.get('interpolation', 'smoothstep'), spec.get('flatEnds', False)) - base)


def arc(center, radius, start, sweep):
    steps = max(2, math.ceil(abs(sweep) / .10))
    return [add(center, (radius*math.cos(start + sweep*i/steps), radius*math.sin(start + sweep*i/steps))) for i in range(steps + 1)]


def outline(points, closed, widths, base=None, anchor='center', outer_side=None,
            trim_inner=False, butt_start=False, butt_end=False):
    n = len(points)
    if anchor == 'outer':
        if closed:
            signed_area = sum(cross(a, b) for a, b in zip(points, points[1:] + points[:1]))
            outer_side = -1 if signed_area > 0 else 1
        if outer_side not in (-1, 1) or base is None: raise ValueError('Outer anchoring needs side and base width')
    elif anchor != 'center': raise ValueError('Unknown anchoring')
    sides = []
    for side in (1, -1):
        boundary, inner_joins = [], []
        for i, (p, width) in enumerate(zip(points, widths)):
            radius = width / 2 if anchor == 'center' else (base/2 if side == outer_side else width - base/2)
            if not closed and i in (0, n - 1):
                direction = unit(sub(points[1], p)) if i == 0 else unit(sub(p, points[i-1]))
                boundary.append(add(p, mul(normal(direction), side*radius)))
                continue
            before = unit(sub(p, points[(i - 1) % n]))
            after = unit(sub(points[(i + 1) % n], p))
            n0, n1 = mul(normal(before), side), mul(normal(after), side)
            turn = math.atan2(cross(before, after), before[0]*after[0] + before[1]*after[1])
            # At actual corners, preserve a round outer join. Smooth samples use offset intersections.
            if abs(turn) > .30 and turn * side < 0:
                boundary.extend(arc(p, radius, math.atan2(n0[1], n0[0]), turn))
            else:
                denominator = 1 + n0[0]*n1[0] + n0[1]*n1[1]
                if denominator < .15: raise ValueError('Unsupported cusp in centerline')
                boundary.append(add(p, mul(add(n0, n1), radius / denominator)))
                if trim_inner and abs(turn) > .30 and turn*side > 0 and not (anchor == 'outer' and side == outer_side):
                    inner_joins.append((boundary[-1], 2*radius*(1+abs(math.tan(turn/2)))))
        if inner_joins:
            boundary = engine.trim_inner_joins(boundary, inner_joins, closed)
        sides.append(boundary)
    left, right = sides
    if closed: return [left, list(reversed(right))]
    end_center = mul(add(left[-1], right[-1]), .5)
    start_center = mul(add(left[0], right[0]), .5)
    end_normal = sub(left[-1], end_center)
    start_normal = sub(right[0], start_center)
    end_cap = [] if butt_end else arc(end_center, widths[-1]/2, math.atan2(end_normal[1], end_normal[0]), -math.pi)[1:]
    start_cap = [] if butt_start else arc(start_center, widths[0]/2, math.atan2(start_normal[1], start_normal[0]), -math.pi)[1:]
    return [left + end_cap + list(reversed(right)) + start_cap]


def trim_open_polyline(points, start_distance=0.0, end_distance=0.0):
    """Trim an open sampled centreline by arc length while preserving curves."""
    if len(points) < 2 or (start_distance <= 1e-9 and end_distance <= 1e-9):
        return points, 0.0, 0.0
    segments = [norm(sub(b, a)) for a, b in zip(points, points[1:])]
    total = sum(segments)
    start_distance = max(0.0, min(float(start_distance), total * .45))
    end_distance = max(0.0, min(float(end_distance), total * .45))
    if start_distance + end_distance >= total - 1e-8:
        return points, 0.0, 0.0

    def point_at(distance):
        remaining = distance
        for index, segment in enumerate(segments):
            if remaining <= segment or index == len(segments) - 1:
                ratio = 0.0 if segment < 1e-9 else remaining / segment
                return add(points[index], mul(sub(points[index + 1], points[index]), ratio))
            remaining -= segment

    start = point_at(start_distance)
    finish = point_at(total - end_distance)
    trimmed = [start]
    travelled = 0.0
    for index, segment in enumerate(segments):
        next_distance = travelled + segment
        if start_distance < next_distance - 1e-9 and next_distance < total - end_distance - 1e-9:
            trimmed.append(points[index + 1])
        travelled = next_distance
    trimmed.append(finish)
    return trimmed, start_distance, end_distance


def anchor_distance(points, distances, point):
    """Project a named anchor onto the sampled closed centerline, including closing edge."""
    candidates = []
    for i, a in enumerate(points):
        b = points[(i+1) % len(points)]; ab = sub(b, a); ap = sub(point, a)
        u = max(0, min(1, (ab[0]*ap[0] + ab[1]*ap[1])/(norm(ab)**2)))
        candidates.append((norm(sub(add(a, mul(ab, u)), point)), distances[i] + u*norm(ab)))
    return min(candidates)[1]


def path_data(contours):
    return ' '.join('M' + 'L'.join(f'{x:.4f} {y:.4f}' for x, y in contour) + 'Z' for contour in contours)


def derive(source, specs, amount, engine_settings=None, geometry_guard=True, compensate_bounds=False):
    normalized = basic_shapes.normalize(source)
    root = normalized.root
    measurements = []
    for index, path in enumerate(root.iter(f'{{{NS}}}path')):
        spec = specs.get(str(index))
        if spec is None: continue
        base = float(path.attrib['stroke-width'])
        points, closed = flatten(path.attrib['d'])
        if engine_settings:
            span = max(max(p[0] for p in points)-min(p[0] for p in points),
                       max(p[1] for p in points)-min(p[1] for p in points))
            symmetry = (engine._symmetry_axis(
                points, base*engine_settings.get('symmetryToleranceInBaseWidths', .3))
                if span >= 2*base else None)
            if symmetry:
                # Normalize the sampled centerline before offsetting. Applying
                # symmetry after offsetting can pair unrelated inner/outer
                # points at aircraft wings and create visible kinks.
                points = engine._enforce_reflection([points], *symmetry)[0]
        trim_start = float(spec.get('trimStart', 0.0))
        trim_end = float(spec.get('trimEnd', 0.0))
        if not closed and (trim_start > 1e-9 or trim_end > 1e-9):
            points, trim_start, trim_end = trim_open_polyline(points, trim_start, trim_end)
        native = normalized.converted.get(index)
        butt_start = bool(spec.get('buttStart'))
        butt_end = bool(spec.get('buttEnd'))
        if compensate_bounds and not native and (butt_start or butt_end or trim_start > 1e-9 or trim_end > 1e-9):
            target_contours = outline(points, closed, [base] * len(points), base,
                                      butt_start=butt_start, butt_end=butt_end)
            target_points = [p for contour in target_contours for p in contour]
            target_bounds = [min(p[0] for p in target_points), min(p[1] for p in target_points),
                             max(p[0] for p in target_points), max(p[1] for p in target_points)]
        else:
            target_bounds = (native['visibleBounds'] if native else compensation.stroke_bounds(path)) if compensate_bounds else None
        distances = [0.0]
        for a, b in zip(points, points[1:]): distances.append(distances[-1] + norm(sub(b, a)))
        length = distances[-1] + (norm(sub(points[-1], points[0])) if closed else 0)
        if engine_settings:
            spec = engine.prepare_profile(spec, base, length, closed, engine_settings)
        parameters = [s/length for s in distances]
        if spec['axis'] == 'paired-length':
            if not closed: raise ValueError('Paired length requires a closed contour')
            start = anchor_distance(points, distances, spec['anchors'][0])
            end = (anchor_distance(points, distances, spec['anchors'][1]) - start) % length
            if min(end, length-end) < 1e-6: raise ValueError('Distinct anchors required')
            parameters = []
            for s in distances:
                s = (s-start) % length
                parameters.append(s/end if s <= end else (length-s)/(length-end))
        elif spec['axis'] == 'side-arcs':
            if not closed: raise ValueError('Side arcs require a closed contour')
            anchors = [anchor_distance(points, distances, p) for p in spec['anchors']]
            start = anchors[0]
            a, b, c = [(s-start) % length for s in anchors[1:]]
            if not 0 < a < b < c < length: raise ValueError('Anchors must follow the contour')
            parameters = []
            for s in distances:
                s = (s-start) % length
                parameters.append(s/a if s <= a else 1 if s <= b else 1-(s-b)/(c-b) if s <= c else 0)
        widths = [width_at(spec, p, t, base, amount) for p, t in zip(points, parameters)]
        anchor = spec.get('anchor', 'center')
        geometry = (engine.diagnose_offsets(points, closed, widths, base, anchor, engine_settings)
                    if engine_settings and geometry_guard else None)
        contours = outline(points, closed, widths, base, anchor, spec.get('outerSide'),
                           trim_inner=bool(engine_settings and geometry_guard),
                           butt_start=butt_start, butt_end=butt_end)
        if geometry:
            contours = engine.fair_unlocked(contours, closed, anchor, points, base, engine_settings, geometry)
            if closed and symmetry:
                # Inner-join trimming can leave unequal samples on mirrored
                # wings. Restore the detected reflection on the finalized
                # contours, after topology repair and fairing, so serialization
                # cannot turn that sampling mismatch into a broken edge.
                contours = engine.enforce_contour_reflection(contours, *symmetry)
        path.attrib.clear()
        data = (engine.serialize(contours, closed, anchor, points,
                                 base*engine_settings.get('linearSegmentToleranceInBaseWidths', 0),
                                 base*engine_settings.get('curveFitToleranceInBaseWidths', 0))
                if geometry else path_data(contours))
        correction = None
        if compensate_bounds:
            options = engine_settings['compensation']
            if options['mode'] != 'per-path-visible-bounds': raise ValueError('Unsupported compensation mode')
            before_ink = compensation.ink_metrics([flatten(d)[0] for d in re.findall(r'M[^M]+', data)])
            source_ink = compensation.ink_metrics(outline(points, closed, [base]*len(points), base,
                                                           butt_start=butt_start, butt_end=butt_end))
            data, correction = compensation.compensate(data, target_bounds, options['tolerance'],
                                                       spec.get('compensationWidthScale', 1))
            sx, sy, tx, ty = correction['matrix']
            after_ink = {'area': before_ink['area']*sx*sy,
                         'centroid': [before_ink['centroid'][0]*sx+tx, before_ink['centroid'][1]*sy+ty]}
            correction['estimatedInk'] = {'source': source_ink, 'before': before_ink, 'after': after_ink}
            correction['centroidDeltaAfter'] = [a-b for a,b in zip(after_ink['centroid'], source_ink['centroid'])]
        path.attrib.update({'d': data, 'fill': 'currentColor', 'fill-rule': 'evenodd'})
        if native:
            path.set('stroke','none')  # Suppress a stroke inherited from a group.
            for key in ('id', 'opacity'):
                if key in native['sourceAttributes']:
                    path.set(key, native['sourceAttributes'][key])
        all_points = [p for contour in contours for p in contour]
        bounds = [min(p[0] for p in all_points), min(p[1] for p in all_points), max(p[0] for p in all_points), max(p[1] for p in all_points)]
        assert all(math.isfinite(v) for v in bounds)
        assert bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] <= 24 and bounds[3] <= 24, bounds
        measurements.append({'path': index, 'minWidth': round(min(widths), 3), 'maxWidth': round(max(widths), 3), 'bounds': [round(v, 3) for v in bounds], 'anchor': spec.get('anchor', 'center'), 'interpolation': spec.get('interpolation', 'smoothstep'), 'nodeCount': len(re.findall(r'[MLCZ]', data))})
        if native: measurements[-1]['normalizedFrom'] = native['sourceTag']
        if engine_settings:
            measurements[-1]['effectiveStops'] = spec['stops']
            measurements[-1]['geometry'] = geometry
        if correction:
            measurements[-1]['compensation'] = correction
            measurements[-1]['bounds'] = correction['afterBounds']
    return ET.tostring(root, encoding='unicode'), measurements


def centerlines(source, specs):
    root = basic_shapes.normalize(source).root
    out = ET.Element(f'{{{NS}}}svg', {'viewBox': '0 0 24 24', 'class': 'centerlines', 'aria-hidden': 'true'})
    for i, p in enumerate(root.iter(f'{{{NS}}}path')):
        if str(i) in specs:
            ET.SubElement(out, f'{{{NS}}}path', {'d': p.attrib['d'], 'fill': 'none', 'stroke': '#fff', 'stroke-width': '.13', 'stroke-dasharray': '.38 .32'})
    return ET.tostring(out, encoding='unicode')


def main():
    catalog = json.loads((ROOT / 'source-icons.json').read_text())
    config = json.loads((ROOT / 'width-profiles.json').read_text())
    revision = json.loads((ROOT / 'folder-revision.json').read_text())
    settings = json.loads((ROOT / 'engine-v2.json').read_text())
    engine_report, compensation_report = [], []
    rows, report = [], []
    for icon in catalog['icons']:
        assert hashlib.sha256(icon['svg'].encode()).hexdigest() == icon['sha256']
        name = icon['name']; spec = config['icons'][name]
        engine_specs = revision['variants']['refined'] if name == 'folder_open' else spec['paths']
        new_svg, new_measurements = derive(icon['svg'], engine_specs, 1, settings)
        folder = ROOT / 'svg' / 'engine'; folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{name}.svg').write_text(new_svg + '\n')
        engine_report.append({'name': name, 'paths': new_measurements})
        compensated_svg, compensated_measurements = derive(icon['svg'], engine_specs, 1, settings, compensate_bounds=True)
        folder = ROOT / 'svg' / 'compensated'; folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{name}.svg').write_text(compensated_svg+'\n')
        compensation_report.append({'name': name, 'paths': [{'path': p['path'], **p['compensation']} for p in compensated_measurements]})
        cells = []
        for variant, amount, label in [('original', 0, '原版'), ('gentle', .55, '轻微变化'), ('expressive', 1, '明显变化')]:
            svg, measurements = (icon['svg'], []) if variant == 'original' else derive(icon['svg'], spec['paths'], amount)
            folder = ROOT / 'svg' / variant; folder.mkdir(parents=True, exist_ok=True)
            (folder / f'{name}.svg').write_text(svg + '\n')
            report.append({'name': name, 'variant': variant, 'paths': measurements})
            if variant != 'original': continue  # Historical candidates remain on disk.
            small = ''.join(f'<span><img src="svg/{variant}/{name}.svg" width="{size}" height="{size}" alt="{name} {size}px {label}"><small>{size}</small></span>' for size in (24, 32, 48))
            cells.append(f'<div class="sample" data-label="{label}"><button type="button" class="large zoom-trigger" aria-label="放大查看 {name} {label}" aria-haspopup="dialog"><img src="svg/{variant}/{name}.svg" width="112" height="112" alt="{name} {label}">{centerlines(icon["svg"], spec["paths"])}</button><div class="sizes">{small}</div><a href="svg/{variant}/{name}.svg" download="{name}-{variant}.svg" aria-label="下载 {name} {label} SVG">下载 SVG</a></div>')
        for variant, label in [('engine', '通用算法 v2'), ('compensated', 'v2 · 尺寸补偿')]:
            small = ''.join(f'<span><img src="svg/{variant}/{name}.svg" width="{size}" height="{size}" alt="{name} {size}px {label}"><small>{size}</small></span>' for size in (24, 32, 48))
            cells.append(f'<div class="sample" data-label="{label}"><button type="button" class="large zoom-trigger" aria-label="放大查看 {name} {label}" aria-haspopup="dialog"><img src="svg/{variant}/{name}.svg" width="112" height="112" alt="{name} {label}">{centerlines(icon["svg"], engine_specs)}</button><div class="sizes">{small}</div><a href="svg/{variant}/{name}.svg" download="{name}-{variant}.svg">下载 SVG</a></div>')
        rows.append(f'<section class="icon-row"><div class="identity"><h2>{html.escape(name)}</h2><p>{html.escape(spec["description"])}</p></div>{"".join(cells)}</section>')
    icon = next(i for i in catalog['icons'] if i['name'] == 'folder_open')
    revision_cells, revision_report = [], []
    guide = '<svg class="alignment-guide" viewBox="0 0 24 24" aria-hidden="true"><rect x="1.5869" y="11" width="20.8262" height="10" fill="none" stroke="#888" stroke-width=".07" stroke-dasharray=".38 .3"/></svg>'
    for variant, specs in revision['variants'].items():
        svg, measurements = derive(icon['svg'], specs, 1)
        folder = ROOT / 'svg' / variant; folder.mkdir(exist_ok=True)
        (folder / 'folder_open.svg').write_text(svg + '\n')
        revision_report.append({'variant': variant, 'paths': measurements})
    width_svg, _ = derive(icon['svg'], revision['variants']['refined'], 1, settings, geometry_guard=False)
    (ROOT / 'svg' / 'engine-widths').mkdir(exist_ok=True)
    (ROOT / 'svg' / 'engine-widths' / 'folder_open.svg').write_text(width_svg+'\n')
    for variant, label in [('original', '原版'), ('expressive', '旧算法 · 未固定边界'), ('engine', '通用算法 v2'), ('compensated', 'v2 · 尺寸补偿')]:
        specs = revision['variants'].get(variant, config['icons']['folder_open']['paths'])
        small = ''.join(f'<span><img src="svg/{variant}/folder_open.svg" width="{size}" height="{size}" alt="文件夹 {label} {size}px"><small>{size}</small></span>' for size in (24, 32, 48))
        revision_cells.append(f'<div class="sample" data-label="{label}"><h3>{label}</h3><button type="button" class="large zoom-trigger" aria-label="放大查看文件夹修订 {label}" aria-haspopup="dialog"><img src="svg/{variant}/folder_open.svg" width="112" height="112" alt="文件夹 {label}">{centerlines(icon["svg"], specs)}{guide}</button><div class="sizes">{small}</div><a href="svg/{variant}/folder_open.svg" download="folder_open-{variant}.svg">下载 SVG</a></div>')
    (ROOT / 'folder-revision-report.json').write_text(json.dumps(revision_report, ensure_ascii=False, indent=2) + '\n')
    page = (ROOT / 'template.html').read_text().replace('<!-- ICON_ROWS -->', '\n'.join(rows)).replace('<!-- REVISION_CELLS -->', ''.join(revision_cells))
    page = page.replace('<!-- STUDY_NAV -->', '<p><a href="batch.html">查看第二批：12 个几何覆盖样本</a> · <a href="showcase.html">查看开源展示页</a></p>')
    (ROOT / 'index.html').write_text(page)
    (ROOT / 'geometry-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'engine-report.json').write_text(json.dumps(engine_report, ensure_ascii=False, indent=2) + '\n')
    (ROOT / 'compensation-report.json').write_text(json.dumps(compensation_report, ensure_ascii=False, indent=2) + '\n')
    print(f'Generated {len(rows)} compensation comparisons and a 4-way folder revision; {26+len(revision["variants"])} standalone SVGs fit 24×24.')


if __name__ == '__main__': main()
