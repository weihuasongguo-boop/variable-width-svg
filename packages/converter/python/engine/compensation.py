"""Per-path visible-bounds compensation, independent of icon identity.

All coordinates are absolute. Affine corrections are baked into path data so
SVG consumers need no runtime transforms. Bounds are analytic for cubics.
"""
import math
import re


def segments(d):
    tokens = re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', d)
    i = 0; command = None; p = (0, 0); start = p
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]; i += 1
        if command == 'Z':
            yield 'Z', (p, start)
            p = start; command = None; continue
        count = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6}.get(command)
        if count is None: raise ValueError(f'Unsupported compensation command {command}')
        v = list(map(float, tokens[i:i+count])); i += count
        if len(v) != count: raise ValueError('Incomplete SVG command')
        if command == 'M':
            p = start = tuple(v); yield 'M', (p,); command = 'L'
        elif command == 'C':
            q = (p, tuple(v[:2]), tuple(v[2:4]), tuple(v[4:]))
            yield 'C', q; p = q[-1]
        else:
            end = (v[0], p[1]) if command == 'H' else (p[0], v[0]) if command == 'V' else tuple(v)
            yield 'L', (p, end); p = end


def cubic_at(points, t):
    u = 1-t
    return tuple(u**3*points[0][k]+3*u*u*t*points[1][k]+3*u*t*t*points[2][k]+t**3*points[3][k] for k in (0, 1))


def path_bounds(d):
    candidates = []
    for kind, p in segments(d):
        candidates.extend([p[0], p[-1]])
        if kind != 'C': continue
        roots = set()
        for k in (0, 1):
            a = -p[0][k]+3*p[1][k]-3*p[2][k]+p[3][k]
            b = 2*(p[0][k]-2*p[1][k]+p[2][k]); c = p[1][k]-p[0][k]
            if abs(a) < 1e-12:
                if abs(b) > 1e-12: roots.add(-c/b)
            else:
                delta = b*b-4*a*c
                if delta >= 0:
                    roots.update(((-b-math.sqrt(delta))/(2*a), (-b+math.sqrt(delta))/(2*a)))
        candidates.extend(cubic_at(p, t) for t in roots if 0 < t < 1)
    if not candidates: raise ValueError('Empty path')
    return [min(p[0] for p in candidates), min(p[1] for p in candidates),
            max(p[0] for p in candidates), max(p[1] for p in candidates)]


def stroke_bounds(path):
    """Visible bounds for the selected round-cap/round-join source strokes.

    Smooth bevel-join curves are accepted; sharp bevel/miter geometry is not
    supported by this padding formula and must not silently enter this mode.
    """
    cap = path.get('stroke-linecap', 'butt'); join = path.get('stroke-linejoin', 'miter')
    if cap != 'round' or join not in ('round', 'bevel'):
        raise ValueError('Compensation requires validated round source strokes')
    if join == 'bevel':
        previous = None
        for kind, p in segments(path.get('d')):
            if kind in ('M', 'Z'): continue
            a = (p[1][0]-p[0][0], p[1][1]-p[0][1])
            b = (p[-1][0]-p[-2][0], p[-1][1]-p[-2][1])
            if previous and math.hypot(*a)*math.hypot(*previous) > 1e-12:
                angle = math.atan2(previous[0]*a[1]-previous[1]*a[0], previous[0]*a[0]+previous[1]*a[1])
                if abs(angle) > .01: raise ValueError('Sharp bevel joins require a stroke-aware bounds solver')
            previous = b
    r = float(path.get('stroke-width'))/2
    box = path_bounds(path.get('d'))
    return [box[0]-r, box[1]-r, box[2]+r, box[3]+r]


def transform_path(d, matrix):
    sx, sy, tx, ty = matrix
    fmt = lambda p: f'{sx*p[0]+tx:.6f} {sy*p[1]+ty:.6f}'
    out = []
    for kind, p in segments(d):
        if kind == 'Z': out.append('Z')
        elif kind == 'M': out.append('M'+fmt(p[0]))
        elif kind == 'C': out.append('C'+' '.join(fmt(q) for q in p[1:]))
        else: out.append('L'+fmt(p[-1]))
    return ''.join(out)


def adjusted_bounds(source, width_scale=1):
    """Explicit local width allowance; preserve horizontal center and Y bounds.

    Default compensation remains exact. This is a drawing input for interior
    strokes, not automatic widening of every small element.
    """
    if not math.isfinite(width_scale) or width_scale <= 0:
        raise ValueError('Compensation width scale must be finite and positive')
    center = (source[0]+source[2])/2
    half_width = (source[2]-source[0])*width_scale/2
    return [center-half_width, source[1], center+half_width, source[3]]


def compensate(d, target, tolerance=1e-4, width_scale=1):
    source = list(target)
    target = adjusted_bounds(source, width_scale)
    before = path_bounds(d)
    error = max(abs(a-b) for a, b in zip(before, target))
    if error <= tolerance:
        result = d; matrix = [1, 1, 0, 0]
    else:
        if min(before[2]-before[0], before[3]-before[1], target[2]-target[0], target[3]-target[1]) <= 1e-10:
            raise ValueError('Cannot compensate degenerate visible bounds')
        sx = (target[2]-target[0])/(before[2]-before[0])
        sy = (target[3]-target[1])/(before[3]-before[1])
        matrix = [sx, sy, target[0]-sx*before[0], target[1]-sy*before[1]]
        result = transform_path(d, matrix)
    after = path_bounds(result)
    if max(abs(a-b) for a, b in zip(after, target)) > tolerance:
        raise ValueError('Compensated path failed visible bounds tolerance')
    return result, {'sourceBounds': source, 'targetBounds': target, 'widthScale': width_scale,
                    'beforeBounds': before, 'afterBounds': after,
                    'matrix': matrix, 'maxErrorBefore': error,
                    'maxErrorAfter': max(abs(a-b) for a, b in zip(after, target))}


def ink_metrics(contours, rows=1024):
    """Scanline area/centroid estimate for one even-odd compound outline.

    A geometric diagnostic, not a perceptual center or multi-path union metric.
    """
    low = min(p[1] for c in contours for p in c); high = max(p[1] for c in contours for p in c)
    if high-low < 1e-10: return None
    step = (high-low)/rows; crossings = [[] for _ in range(rows)]
    for contour in contours:
        for a, b in zip(contour, contour[1:]+contour[:1]):
            if abs(a[1]-b[1]) < 1e-12: continue
            lo, hi = sorted((a[1], b[1]))
            start = max(0, math.ceil((lo-low)/step-.5))
            end = min(rows, math.ceil((hi-low)/step-.5))
            for row in range(start, end):
                y = low+(row+.5)*step
                crossings[row].append(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]))
    area = mx = my = 0.0
    for row, xs in enumerate(crossings):
        xs.sort()
        for a, b in zip(xs[::2], xs[1::2]):
            mass = (b-a)*step; area += mass; mx += mass*(a+b)/2; my += mass*(low+(row+.5)*step)
    if area < 1e-10: return None
    return {'area': area, 'centroid': [mx/area, my/area]}
