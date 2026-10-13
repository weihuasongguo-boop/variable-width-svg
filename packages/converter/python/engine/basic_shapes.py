"""Normalize plain stroked SVG basic shapes to the engine's M/L/C/Z input.

Numeric user-unit geometry only; CSS, transforms and dashed/vector-effect
strokes need separate handling. Elliptical arcs use <=45 degree cubics.
Source SVG is never mutated; native bounds remain the compensation reference.
"""
from dataclasses import dataclass
import math
import re
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
NUMBER = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?\Z')
PRESENTATION = ('fill', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
                'stroke-dasharray', 'vector-effect', 'stroke-opacity', 'fill-opacity')


def number(attrs, key, default=0):
    value = str(attrs.get(key, default))
    if not NUMBER.fullmatch(value) or not math.isfinite(float(value)):
        raise ValueError(f'{key} requires a finite number in user units')
    return float(value)


def fmt(p):
    return ' '.join(f'{v:.10f}'.rstrip('0').rstrip('.') if abs(v)>1e-10 else '0' for v in p)


def arc(cx, cy, rx, ry, start, sweep):
    commands = []
    count = max(1, math.ceil(abs(sweep)/(math.pi/4)))
    delta = sweep/count
    for i in range(count):
        a, b = start+i*delta, start+(i+1)*delta
        k = 4/3*math.tan(delta/4)
        p = (cx+rx*math.cos(a), cy+ry*math.sin(a))
        q = (cx+rx*math.cos(b), cy+ry*math.sin(b))
        c1 = (p[0]-k*rx*math.sin(a), p[1]+k*ry*math.cos(a))
        c2 = (q[0]+k*rx*math.sin(b), q[1]-k*ry*math.cos(b))
        commands.append('C'+fmt(c1)+' '+fmt(c2)+' '+fmt(q))
    return ''.join(commands)


def geometry(tag, attrs):
    if tag == 'rect':
        x,y,w,h = [number(attrs,k) for k in ('x','y','width','height')]
        if w <= 0 or h <= 0:
            raise ValueError('Non-positive rectangle extent; no drawable centerline')
        rx = None if attrs.get('rx','auto') == 'auto' else number(attrs,'rx')
        ry = None if attrs.get('ry','auto') == 'auto' else number(attrs,'ry')
        if rx is None: rx = ry if ry is not None else 0
        if ry is None: ry = rx
        if min(rx,ry)<0: raise ValueError('Negative corner radius')
        rx,ry = min(rx,w/2),min(ry,h/2)
        if min(rx,ry)==0:
            d='M'+fmt((x,y))+'L'+fmt((x+w,y))+'L'+fmt((x+w,y+h))+'L'+fmt((x,y+h))+'Z'
        else:
            d=('M'+fmt((x+rx,y))+'L'+fmt((x+w-rx,y))+arc(x+w-rx,y+ry,rx,ry,-math.pi/2,math.pi/2)
               +'L'+fmt((x+w,y+h-ry))+arc(x+w-rx,y+h-ry,rx,ry,0,math.pi/2)
               +'L'+fmt((x+rx,y+h))+arc(x+rx,y+h-ry,rx,ry,math.pi/2,math.pi/2)
               +'L'+fmt((x,y+ry))+arc(x+rx,y+ry,rx,ry,math.pi,math.pi/2)+'Z')
        return d,[x,y,x+w,y+h]
    cx,cy = number(attrs,'cx'),number(attrs,'cy')
    if tag=='circle': rx=ry=number(attrs,'r')
    else:
        rx=None if attrs.get('rx','auto')=='auto' else number(attrs,'rx')
        ry=None if attrs.get('ry','auto')=='auto' else number(attrs,'ry')
        if rx is None: rx=ry or 0
        if ry is None: ry=rx
    if min(rx,ry)<=0: raise ValueError('Non-positive ellipse radius; no drawable centerline')
    return 'M'+fmt((cx+rx,cy))+arc(cx,cy,rx,ry,0,math.tau)+'Z',[cx-rx,cy-ry,cx+rx,cy+ry]


@dataclass
class Normalized:
    root: ET.Element
    converted: dict
    original_path_map: dict
    retained: list


def normalize(source):
    root = ET.fromstring(source)
    if any(any(k in e.attrib for k in ('transform','style','class')) or e.tag=='{'+NS+'}style' for e in root.iter()):
        raise ValueError('Transforms and CSS require a separate SVG normalization stage')
    old_paths = list(root.iter('{'+NS+'}path'))
    metadata, retained = {}, []

    def visit(e, inherited):
        effective = {**inherited, **{k:v for k,v in e.attrib.items() if k in PRESENTATION}}
        tag=e.tag.rsplit('}',1)[-1]
        if tag in ('rect','circle','ellipse'):
            try:
                if effective.get('fill','black')!='none' or effective.get('stroke','none')=='none':
                    raise ValueError('Filled shape or no visible stroke; preserve source')
                if effective.get('stroke-dasharray','none')!='none' or effective.get('vector-effect','none')!='none':
                    raise ValueError('Dashed/vector-effect strokes require separate handling')
                if number(effective,'stroke-opacity',1)!=1:
                    raise ValueError('Stroke opacity requires separate paint handling')
                if number(effective,'fill-opacity',1)!=1:
                    raise ValueError('Fill opacity requires separate paint handling')
                base=number(effective,'stroke-width',1)
                if base<=0: raise ValueError('Non-positive stroke width')
                d,box=geometry(tag,e.attrib)
                old=dict(e.attrib)
                for key in ('x','y','width','height','rx','ry','cx','cy','r'):
                    e.attrib.pop(key,None)
                e.tag='{'+NS+'}path'
                e.attrib.update({k:effective[k] for k in PRESENTATION if k in effective})
                e.set('stroke-width',str(base));e.set('d',d)
                metadata[id(e)]={'sourceTag':tag,'sourceAttributes':old,'centerBounds':box,
                                 'visibleBounds':[box[0]-base/2,box[1]-base/2,box[2]+base/2,box[3]+base/2]}
            except ValueError as error:
                retained.append({'element':tag,'reason':str(error)})
        for child in e: visit(child,effective)

    visit(root,{})
    paths=list(root.iter('{'+NS+'}path'))
    indices={id(p):i for i,p in enumerate(paths)}
    return Normalized(root,{indices[k]:v for k,v in metadata.items()},
                      {str(i):str(indices[id(p)]) for i,p in enumerate(old_paths)},retained)
