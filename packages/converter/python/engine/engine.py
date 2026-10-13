"""Geometry safeguards shared by all candidates; no icon names or coordinates.

For q(s)=p(s)+r(s)n(s), the tangential derivative component is 1-k(s)r(s).
Use it to detect compression, then fair the resulting contour as a whole.
This is a local repair, not a general boolean/topology solver. Large crossing
loops are rejected rather than silently deleting a meaningful icon feature.
"""
import bisect
import copy
import math
from collections import defaultdict


def sub(a, b): return (a[0]-b[0], a[1]-b[1])
def length(v): return math.hypot(*v)
def unit(v):
    n = length(v)
    return (v[0]/n, v[1]/n) if n else (0.0, 0.0)


def prepare_profile(spec, base, total_length, closed, settings):
    """Short, physical-length endpoint easing instead of a whole first interval."""
    result = copy.deepcopy(spec)
    result['interpolation'] = 'pchip'
    if closed or result['axis'] != 'length':
        return result
    stops = result['stops']
    first, second = stops[:2]
    before, last = stops[-2:]
    reach = settings['endpointEaseInBaseWidths']*base/total_length
    fraction = settings['endpointEaseMaxIntervalFraction']
    a = min(reach, fraction*(second[0]-first[0]))
    b = min(reach, fraction*(last[0]-before[0]))
    start = [first[0]+a, first[1]+(second[1]-first[1])*a/(second[0]-first[0])]
    end = [last[0]-b, last[1]-(last[1]-before[1])*b/(last[0]-before[0])]
    result['stops'] = [first, start, *stops[1:-1], end, last]
    result['flatEnds'] = True
    return result


def cubic_basis(t):
    t = abs(t)
    if t < 1: return (4-6*t*t+3*t*t*t)/6
    if t < 2: return (2-t)**3/6
    return 0.0


def diagnose_offsets(points, closed, widths, base, anchor, settings):
    n = len(points)
    curvature, sharp = [], []
    for i, p in enumerate(points):
        if not closed and i in (0, n-1):
            curvature.append(0.0); sharp.append(False); continue
        a, b = sub(p, points[i-1]), sub(points[(i+1) % n], p)
        u, v = unit(a), unit(b)
        turn = math.atan2(u[0]*v[1]-u[1]*v[0], u[0]*v[0]+u[1]*v[1])
        sharp.append(abs(turn) > .30)
        curvature.append(turn/((length(a)+length(b))/2))
    area = sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(points, points[1:]+points[:1]))
    outer = -1 if area > 0 else 1
    if anchor == 'outer' and not closed:
        raise ValueError('v2 outer anchoring currently requires a closed path')
    stats = []
    for side in (1, -1):
        locked = anchor == 'outer' and side == outer
        radii = [base/2 if locked else w-base/2 if anchor == 'outer' else w/2 for w in widths]
        if min(radii) < 0: raise ValueError('Width smaller than locked outer half-width')
        ratios = [max(0, side*k)*r if not corner else 0 for k, r, corner in zip(curvature, radii, sharp)]
        if closed and sum(q > 1 for q in ratios) > n/2:
            raise ValueError('Offset reverses over most of a closed contour; possible collapsed hole')
        stats.append({'side': side, 'locked': locked,
                      'maxRatioBefore': round(max(ratios), 6),
                      'compressedSamples': sum(q > settings['offsetCurvatureTrigger'] for q in ratios),
                      'reversedTangentialSamples': sum(q > 1 for q in ratios)})
    return {'sides': stats, 'sharpJoins': sum(sharp)}


def signed_area(points):
    return sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(points, points[1:]+points[:1]))/2


def trim_inner_joins(boundary, joins, closed):
    """Join actual incoming/outgoing offset chains, removing inner overlap.

    A miter can lie behind many densely sampled offset points. Inserting it
    alone leaves two hairpins; a later proper-crossing test can miss one.
    Search only the width/angle-sized neighborhood of a known inner corner.
    Intersect the two chains BEFORE their artificial miter edges and trim both.
    """
    result = list(boundary)
    for vertex, reach in joins:
        if vertex not in result:
            continue  # An adjacent join already consumed this overlap.
        j = result.index(vertex)
        if closed:
            start = (j-len(result)//2) % len(result)
            result = result[start:]+result[:start]
            j = result.index(vertex)
        lo, hi, distance = j, j, 0.0
        while lo > 0 and distance < reach:
            distance += length(sub(result[lo], result[lo-1])); lo -= 1
        distance = 0.0
        while hi < len(result)-1 and distance < reach:
            distance += length(sub(result[hi+1], result[hi])); hi += 1
        hits = []
        cross = lambda a,b: a[0]*b[1]-a[1]*b[0]
        for a in range(lo, j-1):
            p, q = result[a], result[a+1]
            u = sub(q,p)
            for b in range(j+1, hi):
                r, s = result[b], result[b+1]
                v = sub(s,r); den = cross(u,v)
                if abs(den) < 1e-12:
                    continue
                t, z = cross(sub(r,p),v)/den, cross(sub(r,p),u)/den
                if -1e-8 <= t <= 1+1e-8 and -1e-8 <= z <= 1+1e-8:
                    point = (p[0]+t*u[0], p[1]+t*u[1])
                    hits.append((b-a, a, b, point))
        if hits:
            _, a, b, point = min(hits)
            result = result[:a+1]+[point]+result[b+1:]
            # The intersection can land almost on one of the two incoming
            # samples. Keeping that microscopic edge gives the fairing pass a
            # false cusp, which cubic serialization can turn into a visible
            # nick on an otherwise smooth contour. Collapse only the local
            # artifact, using a small geometric threshold tied to this join's
            # reach; ordinary contour spacing and intentional corners remain.
            try:
                j = result.index(point)
            except ValueError:
                continue
            threshold = min(0.04, max(0.008, reach * 0.015))
            for _ in range(2):
                if len(result) < 6:
                    break
                prev = (j - 1) % len(result) if closed else j - 1
                nxt = (j + 1) % len(result) if closed else j + 1
                prev_d = length(sub(point, result[prev])) if prev >= 0 else float('inf')
                next_d = length(sub(result[nxt], point)) if nxt < len(result) else float('inf')
                if min(prev_d, next_d) >= threshold:
                    break
                if prev_d <= next_d and prev >= 0:
                    del result[prev]
                    j -= 1
                elif nxt < len(result):
                    del result[nxt]
    return result


def first_crossing(points, cell_size=.25):
    """Find proper non-neighbor intersections using a uniform spatial grid."""
    buckets = defaultdict(list); seen = set(); n = len(points)
    cross = lambda a, b: a[0]*b[1]-a[1]*b[0]
    for i, a in enumerate(points):
        b = points[(i+1)%n]
        for x in range(math.floor(min(a[0], b[0])/cell_size), math.floor(max(a[0], b[0])/cell_size)+1):
            for y in range(math.floor(min(a[1], b[1])/cell_size), math.floor(max(a[1], b[1])/cell_size)+1):
                for j in buckets[x, y]:
                    if i-j == 1 or (j == 0 and i == n-1) or (j, i) in seen: continue
                    seen.add((j, i)); c, d = points[j], points[(j+1)%n]
                    ab, cd = sub(b, a), sub(d, c); den = cross(ab, cd)
                    if abs(den) < 1e-12: continue
                    t, u = cross(sub(c, a), cd)/den, cross(sub(c, a), ab)/den
                    if 1e-7 < t < 1-1e-7 and 1e-7 < u < 1-1e-7:
                        return j, i, (a[0]+t*ab[0], a[1]+t*ab[1])
                buckets[x, y].append(i)
    return None


def remove_local_loops(points, area_limit):
    result = list(points); removed = []
    for _ in range(32):
        crossing = first_crossing(result)
        if crossing is None: return result, removed
        i, j, p = crossing
        a, b = [p]+result[i+1:j+1], [p]+result[j+1:]+result[:i+1]
        keep, discard = sorted([a, b], key=lambda c: abs(signed_area(c)), reverse=True)
        area = abs(signed_area(discard))
        if area > area_limit: raise ValueError('Offset has a large loop; topology needs explicit treatment')
        removed.append(area); result = keep
    raise ValueError('Too many offset loops; refuse ambiguous contour')


def _line_segment(points, i, tolerance):
    n = len(points)
    a, b, c, d = points[(i-1) % n], points[i], points[(i+1) % n], points[(i+2) % n]
    ab, bc, cd = sub(b, a), sub(c, b), sub(d, c)
    lengths = (length(ab), length(bc), length(cd))
    if min(lengths) < 1e-9: return False
    # A straight run must not cross a cap or a real corner, even when the
    # local points happen to fall within the distance tolerance.
    forward = (ab[0]*bc[0] + ab[1]*bc[1])/(lengths[0]*lengths[1])
    onward = (bc[0]*cd[0] + bc[1]*cd[1])/(lengths[1]*lengths[2])
    return (forward > .96 and onward > .96 and
            _point_segment_distance(b, a, c) <= tolerance and
            _point_segment_distance(c, b, d) <= tolerance)


def _linear_run(points, start, end, tolerance):
    """Check the whole candidate run, avoiding gradual round-cap turns."""
    n = len(points)
    a, b = points[start], points[(end + 1) % n]
    return all(_point_segment_distance(points[k % n], a, b) <= tolerance
               for k in range(start, end + 2))


def _cubic_eval(segment, t):
    p0, c1, c2, p3 = segment
    u = 1-t
    return tuple(u**3*p0[k] + 3*u*u*t*c1[k] + 3*u*t*t*c2[k] + t**3*p3[k] for k in (0, 1))


def _fit_cubic(segments, start, end):
    first, last = segments[start], segments[end]
    p0, p3 = first[0], last[3]
    t0 = unit(sub(first[1], p0))
    t1 = unit(sub(p3, last[2]))
    chord = length(sub(p3, p0))
    if chord < 1e-9:
        return (p0, first[1], last[2], p3)
    # A chord/3 handle is suitable for a short, nearly straight span, but it
    # makes circular arcs look pinched and forces the greedy fitter to emit a
    # cubic for almost every sampled segment. Estimate the tangent turn and
    # use the circular-arc handle ratio 1 / (3 cos(theta / 4)); this keeps a
    # quarter circle close with one cubic while leaving sharp turns guarded by
    # the normal error test below.
    tangent_dot = max(-1.0, min(1.0, t0[0]*t1[0] + t0[1]*t1[1]))
    turn = math.acos(tangent_dot)
    handle_ratio = 1 / (3 * max(math.cos(turn/4), 0.25))
    handle = chord * handle_ratio
    return (p0, (p0[0]+t0[0]*handle, p0[1]+t0[1]*handle),
            (p3[0]-t1[0]*handle, p3[1]-t1[1]*handle), p3)


def _fit_error(segments, start, end, candidate):
    count = end-start+1
    error = 0.0
    for index in range(count):
        segment = segments[start+index]
        for sample in (0.25, 0.5, 0.75):
            actual = _cubic_eval(segment, sample)
            t = (index+sample)/count
            error = max(error, length(sub(actual, _cubic_eval(candidate, t))))
    return error


def _reflection_error(points, axis, center):
    """Return the worst nearest-point error after reflecting a point set."""
    if len(points) < 4: return float('inf')
    sample = points if len(points) <= 360 else [points[i] for i in range(0, len(points), len(points)//360)]
    error = 0.0
    for p in sample:
        target = (2*center-p[0], p[1]) if axis == 'x' else (p[0], 2*center-p[1])
        error = max(error, min(length(sub(target, q)) for q in points))
    return error


def _symmetry_axis(points, tolerance):
    """Detect a strong horizontal/vertical reflection in a centerline."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    candidates = [('x', (min(xs)+max(xs))/2), ('y', (min(ys)+max(ys))/2)]
    axis, center, error = min(((a, c, _reflection_error(points, a, c)) for a, c in candidates),
                              key=lambda item: (item[2],
                                                (max(ys)-min(ys)) if item[0] == 'y' else (max(xs)-min(xs))))
    return (axis, center) if error <= tolerance else None


def _enforce_reflection(contours, axis, center):
    """Pair offset points with their reflected neighbours and average them."""
    points = [p for contour in contours for p in contour]
    if not points: return contours
    adjusted = []
    for p in points:
        target = (2*center-p[0], p[1]) if axis == 'x' else (p[0], 2*center-p[1])
        q = min(points, key=lambda candidate: length(sub(target, candidate)))
        reflected = (2*center-q[0], q[1]) if axis == 'x' else (q[0], 2*center-q[1])
        adjusted.append(((p[0]+reflected[0])/2, (p[1]+reflected[1])/2))
    result, index = [], 0
    for contour in contours:
        result.append(adjusted[index:index+len(contour)])
        index += len(contour)
    return result


def enforce_contour_reflection(contours, axis, center):
    """Make a detected symmetric contour pair exact after offset/fairing.

    Offset joins can delete different local samples on the two sides of a
    symmetric source. Pairing by nearest Euclidean point is unsafe around
    wings and concave corners, so estimate the cyclic arc-length phase and
    pair points in reverse contour order (reflection reverses orientation).
    The operation is applied per contour and is reverted if it introduces a
    proper crossing.
    """
    result = []
    for contour in contours:
        clean = []
        for p in contour:
            if not clean or length(sub(p, clean[-1])) > 1e-9:
                clean.append(p)
        if len(clean) < 8:
            result.append(contour)
            continue
        n = len(clean)
        stride = max(1, n // 120)

        def reflect(p):
            return ((2*center-p[0], p[1]) if axis == 'x'
                    else (p[0], 2*center-p[1]))

        best_shift, best_error = 0, float('inf')
        for shift in range(0, n, stride):
            error = 0.0
            count = 0
            for i in range(0, n, stride):
                j = (shift - i) % n
                q = reflect(clean[j])
                dx, dy = clean[i][0]-q[0], clean[i][1]-q[1]
                error += dx*dx + dy*dy
                count += 1
            error /= max(1, count)
            if error < best_error:
                best_shift, best_error = shift, error

        adjusted = []
        for i, p in enumerate(clean):
            q = reflect(clean[(best_shift-i) % n])
            adjusted.append(((p[0]+q[0])/2, (p[1]+q[1])/2))
        if first_crossing(adjusted):
            result.append(contour)
        else:
            result.append(adjusted)
    return result


def contour_path(points, curved, linear_tolerance=0, curve_tolerance=0):
    """Periodic cubic B-spline converted to SVG C commands (C2 before rounding).

    Positive control weights stay in each local control hull. Locked contours
    retain their old polygon exactly. The curve approximates, not interpolates,
    the dense contour samples.
    """
    fmt = lambda p: f'{p[0]:.5f} {p[1]:.5f}'
    if not curved: return 'M'+'L'.join(f'{p[0]:.4f} {p[1]:.4f}' for p in points)+'Z'
    clean = []
    for p in points:
        if not clean or length(sub(p, clean[-1])) > 1e-8: clean.append(p)
    if length(sub(clean[0], clean[-1])) < 1e-8: clean.pop()
    n = len(clean)
    knot = lambda a, b, c: tuple((a[k]+4*b[k]+c[k])/6 for k in (0, 1))
    knots = [knot(clean[i-1], clean[i], clean[(i+1) % n]) for i in range(n)]
    segments = []
    for i, p in enumerate(clean):
        q = clean[(i+1) % n]
        c1 = tuple((2*p[k]+q[k])/3 for k in (0, 1))
        c2 = tuple((p[k]+2*q[k])/3 for k in (0, 1))
        segments.append((knots[i], c1, c2, knots[(i+1) % n]))
    out = ['M'+fmt(knots[0])]
    i = 0
    while i < n:
        if linear_tolerance > 0 and _line_segment(clean, i, linear_tolerance):
            end = i
            # Keep the final segment for the seam. Letting a run consume it
            # would jump back to the initial knot and collapse a narrow open
            # stroke's closed outline to a zero-area path.
            while end + 1 < n - 1 and _line_segment(clean, end + 1, linear_tolerance):
                candidate = end + 1
                if not _linear_run(clean, i, candidate, linear_tolerance): break
                end = candidate
            out.append('L'+fmt(knots[(end+1) % n]))
            i = end + 1
            continue
        end = i
        if curve_tolerance > 0:
            while end + 1 < n:
                candidate = _fit_cubic(segments, i, end + 1)
                if _fit_error(segments, i, end + 1, candidate) > curve_tolerance:
                    break
                end += 1
            candidate = _fit_cubic(segments, i, end)
        else:
            candidate = segments[i]
        out.append('C'+fmt(candidate[1])+' '+fmt(candidate[2])+' '+fmt(candidate[3]))
        i = end + 1
    return ''.join(out)+'Z'


def fair_contour(points, radius, sample_spacing=None):
    """Symmetric physical-arc-length convolution of a closed candidate outline.

    Equal spacing prevents dense source knots from biasing the fairing. The
    positive symmetric kernel keeps straight spans straight and cannot exceed
    the raw contour's bounding box. A local fold is averaged with its neighbors
    instead of changing stroke width at isolated curvature peaks.
    """
    clean = [points[0]]
    for p in points[1:]:
        if length(sub(p, clean[-1])) > 1e-9: clean.append(p)
    if length(sub(clean[0], clean[-1])) < 1e-9: clean.pop()
    distances = [0.0]
    for a, b in zip(clean, clean[1:]+clean[:1]): distances.append(distances[-1]+length(sub(b, a)))
    total = distances[-1]
    spacing = min(.08, radius/8) if sample_spacing is None else max(1e-4, sample_spacing)
    count = max(32, math.ceil(total/spacing))
    step = total/count
    uniform = []
    for i in range(count):
        s = i*step; j = min(len(clean)-1, bisect.bisect_right(distances, s)-1)
        u = (s-distances[j])/(distances[j+1]-distances[j]); a, b = clean[j], clean[(j+1)%len(clean)]
        uniform.append((a[0]+u*(b[0]-a[0]), a[1]+u*(b[1]-a[1])))
    reach = math.ceil(radius/step)
    weights = [(j, cubic_basis(2*j*step/radius)) for j in range(-reach, reach+1)]
    total_weight = sum(w for _, w in weights)
    result = [tuple(sum(w*uniform[(i+j)%count][axis] for j, w in weights)/total_weight
                    for axis in (0, 1)) for i in range(count)]
    displacement = max(length(sub(a, b)) for a, b in zip(uniform, result))
    return result, displacement


def _point_segment_distance(p, a, b):
    ab = sub(b, a); den = ab[0]*ab[0] + ab[1]*ab[1]
    if den < 1e-16: return length(sub(p, a))
    t = max(0.0, min(1.0, ((p[0]-a[0])*ab[0] + (p[1]-a[1])*ab[1])/den))
    return length(sub(p, (a[0]+t*ab[0], a[1]+t*ab[1])))


def _rdp(points, tolerance):
    if len(points) <= 2: return list(points)
    a, b = points[0], points[-1]
    index, farthest = max(enumerate(points[1:-1], 1),
                          key=lambda item: _point_segment_distance(item[1], a, b))
    distance = _point_segment_distance(farthest, a, b)
    if distance <= tolerance: return [a, b]
    left = _rdp(points[:index+1], tolerance)
    right = _rdp(points[index:], tolerance)
    return left[:-1] + right


def simplify_closed(points, tolerance):
    """Reduce sampled closed contours under a geometric error bound."""
    clean = []
    for p in points:
        if not clean or length(sub(p, clean[-1])) > 1e-9: clean.append(p)
    if len(clean) < 4: return clean
    # Split the ring at a farthest pair so RDP sees two ordinary open chains.
    anchor = clean[0]
    opposite = max(range(1, len(clean)), key=lambda i: length(sub(clean[i], anchor)))
    first = _rdp(clean[:opposite+1], tolerance)
    second = _rdp(clean[opposite:]+[anchor], tolerance)
    reduced = first[:-1] + second[:-1]
    return reduced if len(reduced) >= 3 else clean


def fair_unlocked(contours, closed, anchor, points, base, settings, geometry):
    area = sum(a[0]*b[1]-a[1]*b[0] for a, b in zip(points, points[1:]+points[:1]))
    locked = (1 if area > 0 else 0) if closed and anchor == 'outer' else None
    result = []
    for i, c in enumerate(contours):
        risk = (geometry['sides'][i]['maxRatioBefore'] if closed else
                max(s['maxRatioBefore'] for s in geometry['sides']))
        if i == locked:
            result.append(c); continue
        c, loops = remove_local_loops(c, base*base*settings['loopAreaLimitInBaseWidthsSquared'])
        smooth, displacement = (fair_contour(c, base*settings['fairingRadiusInBaseWidths'],
                                             base*settings.get('fairingSampleSpacingInBaseWidths', .04))
                                if risk > settings['offsetCurvatureTrigger'] else (c, 0.0))
        if first_crossing(smooth): raise ValueError('Contour still crosses after fairing')
        simplify_tolerance = base*settings.get('outputSimplificationToleranceInBaseWidths', 0)
        simplified = simplify_closed(smooth, simplify_tolerance) if simplify_tolerance > 0 else smooth
        geometry.setdefault('fairing', []).append({'contour': i, 'maxDisplacement': round(displacement, 6),
                                                   'nodesBeforeSimplification': len(smooth),
                                                   'nodesAfterSimplification': len(simplified),
                                                   'removedLoopAreas': [round(a, 8) for a in loops]})
        if first_crossing(simplified): raise ValueError('Contour crosses after node simplification')
        result.append(simplified)
    return result


def serialize(contours, closed, anchor, points, linear_tolerance=0, curve_tolerance=0):
    # Locked contours keep their computed geometry and width compensation, but
    # can use the same compact cubic representation. Serialization does not
    # alter the contour points; it only replaces dense polygonal spelling with
    # line/cubic commands after the geometry is already finalized.
    return ' '.join(contour_path(c, True, linear_tolerance, curve_tolerance) for c in contours)
