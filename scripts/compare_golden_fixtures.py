#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path

def compare(a,b,path,atol,rtol,errors):
    if a is None or b is None:
        if a is not b: errors.append(f'{path}: {a!r} != {b!r}')
        return
    if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        if not math.isclose(float(a),float(b),abs_tol=atol,rel_tol=rtol): errors.append(f'{path}: {a} != {b} (atol={atol}, rtol={rtol})')
        return
    if isinstance(a,dict) and isinstance(b,dict):
        if set(a)!=set(b): errors.append(f'{path}: keys differ R={sorted(a)} Python={sorted(b)}'); return
        for k in a: compare(a[k],b[k],f'{path}.{k}',atol,rtol,errors)
        return
    if isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b): errors.append(f'{path}: lengths differ {len(a)} != {len(b)}'); return
        for i,(x,y) in enumerate(zip(a,b)): compare(x,y,f'{path}[{i}]',atol,rtol,errors)
        return
    if a!=b: errors.append(f'{path}: {a!r} != {b!r}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('r_json'); ap.add_argument('python_json'); ap.add_argument('--manifest',default='reference/golden/manifest.json'); ns=ap.parse_args()
    r=json.loads(Path(ns.r_json).read_text()); p=json.loads(Path(ns.python_json).read_text()); m=json.loads(Path(ns.manifest).read_text())
    cases={c['id']:c for c in m['cases']}; expected=set(cases)
    if set(r)!=expected or set(p)!=expected: raise SystemExit(f'case set mismatch manifest={sorted(expected)} R={sorted(r)} Python={sorted(p)}')
    errors=[]
    for cid in sorted(expected):
        c=cases[cid]; compare(r[cid],p[cid],cid,float(c.get('atol',m['default_atol'])),float(c.get('rtol',m['default_rtol'])),errors)
    if errors:
        print('\n'.join(errors[:100])); raise SystemExit(f'golden parity failed with {len(errors)} disagreement(s)')
    print(f'golden parity PASS: {len(expected)} cases')
if __name__=='__main__': main()
