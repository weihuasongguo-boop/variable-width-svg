"""Prepare inherited SVG strokes without changing the published converter API."""
import re
import xml.etree.ElementTree as ET
PRESENTATION = ("fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "vector-effect", "stroke-opacity", "fill-opacity")

def absolute(d):
 tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',d);i=0;cmd=None;x=y=sx=sy=0;out=[]
 arity={'M':2,'L':2,'H':1,'V':1,'C':6,'Q':4}
 while i<len(tokens):
  if tokens[i].isalpha():cmd=tokens[i];i+=1
  upper=cmd.upper();relative=cmd.islower()
  if upper=='Z':out.append('Z');x,y=sx,sy;cmd=None;continue
  if upper not in arity:raise ValueError('Unsupported command '+upper)
  n=arity[upper];vals=list(map(float,tokens[i:i+n]));i+=n
  if len(vals)!=n:raise ValueError('Incomplete coordinates')
  if upper in ['M','L']:
   nx,ny=vals;nx+=x if relative else 0;ny+=y if relative else 0;out.append(f'{upper}{nx} {ny}');x,y=nx,ny
   if upper=='M':sx,sy=x,y;cmd='l' if relative else 'L'
  elif upper=='H':x=vals[0]+(x if relative else 0);out.append(f'L{x} {y}')
  elif upper=='V':y=vals[0]+(y if relative else 0);out.append(f'L{x} {y}')
  else:
   pts=[(vals[j]+(x if relative else 0),vals[j+1]+(y if relative else 0)) for j in range(0,n,2)]
   if upper=='Q':
    (qx,qy),(nx,ny)=pts;pts=[(x+2*(qx-x)/3,y+2*(qy-y)/3),(nx+2*(qx-nx)/3,ny+2*(qy-ny)/3),(nx,ny)]
   out.append('C'+' '.join(str(v) for p in pts for v in p));x,y=pts[-1]
 return ''.join(out)

def canonical(svg):
 root=ET.fromstring(svg)
 def walk(el,inherited):
  attrs={**inherited,**{k:v for k,v in el.attrib.items() if k in PRESENTATION}}
  if el.tag.rsplit('}',1)[-1] in ['path','circle','ellipse','rect','line','polyline','polygon']:
   for k,v in attrs.items():el.set(k,v)
   if el.tag.endswith('path'):el.set('d',absolute(el.get('d','')))
  else:
   for k in PRESENTATION:el.attrib.pop(k,None)
  for child in el:walk(child,attrs)
 walk(root,{})
 return ET.tostring(root,encoding='unicode')
