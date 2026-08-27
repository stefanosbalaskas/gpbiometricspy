#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import argparse, json
import numpy as np
import pandas as pd
import gpbiometricspy as gp

def clean(v):
    if isinstance(v, np.generic): return clean(v.item())
    if isinstance(v, float): return None if not np.isfinite(v) else float(v)
    if isinstance(v, (int, str, bool)) or v is None: return v
    if isinstance(v, np.ndarray): return [clean(x) for x in v.tolist()]
    if isinstance(v, pd.Series): return [clean(x) for x in v.tolist()]
    if isinstance(v, pd.DataFrame):
        return {c:[clean(x) for x in v[c].tolist()] for c in v.columns}
    if isinstance(v, dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v, (list, tuple)): return [clean(x) for x in v]
    return clean(str(v))

def generate():
    out={}
    ohms=pd.DataFrame({'GSR_OHMS':[1_000_000.,500_000.,250_000.,np.nan]})
    out['gsr_ohms_to_us']=gp.convert_gazepoint_gsr_to_conductance(ohms,input_unit='ohms')['GSR_US'].to_numpy()
    kohms=pd.DataFrame({'GSR_KOHMS':[1000.,500.,250.,np.nan]})
    out['gsr_kohms_to_us']=gp.convert_gazepoint_gsr_to_conductance(kohms,gsr_col='GSR_KOHMS',input_unit='kohms')['GSR_US'].to_numpy()
    scr=np.array([.1,.2,.4,np.nan])
    for method in ('percent_max','range','center','z','log_z'):
        out[f'scr_{method}']=gp.normalize_gazepoint_scr(scr,method=method)
    nni=np.array([800.,810.,790.,805.,795.,815.])
    out['pyhrv_sdnn']=gp.compute_gazepoint_pyhrv_sdnn(nni)
    out['pyhrv_rmssd']=gp.compute_gazepoint_pyhrv_rmssd(nni)
    out['pyhrv_sdsd']=gp.compute_gazepoint_pyhrv_sdsd(nni)
    out['pyhrv_nn20']=gp.compute_gazepoint_pyhrv_nn20(nni)
    out['pyhrv_nn50']=gp.compute_gazepoint_pyhrv_nn50(nni)
    pup=pd.DataFrame({'participant':['P01']*6,'pupil_left':[3.,3.2,3.4,np.nan,3.3,3.1]})
    out['pupil_moving_average']=gp.smooth_gazepoint_pupil(pup,pupil_cols='pupil_left',id_cols='participant',window=3)['data']['pupil_left_smooth']
    ttl=pd.DataFrame({'CNT':range(6),'TTLV':[1]*6,'TTL0':[0,1,1,0,2,2]})
    ev=gp.extract_gazepoint_ttl_events(ttl,ttl_columns=['TTL0'])
    out['ttl_changes']={'ttl_value':ev['ttl_value'],'previous_ttl_value':ev['previous_ttl_value'],'event_order':ev['event_order']}
    z=pd.DataFrame({'participant':['A']*3+['B']*3,'SCR_Amplitude':[1.,2.,3.,10.,12.,14.]})
    out['zscore_grouped']=gp.standardize_gazepoint_zscore(z,signal_col='SCR_Amplitude',group_col='participant')['SCR_Amplitude_Z']
    bg=pd.DataFrame({'participant':['A']*4,'GSR_US':[1.,2.,3.,4.],'GSRV':[1,1,1,1]})
    out['baseline_gsr']=gp.baseline_correct_gazepoint_gsr(bg,[True,True,False,False],group_columns=['participant'])['GSR_US_baseline_corrected']
    bh=pd.DataFrame({'participant':['A']*4,'HR':[60.,62.,65.,67.],'HRV':[1,1,1,1]})
    out['baseline_hr']=gp.baseline_correct_gazepoint_hr(bh,[True,True,False,False],group_columns=['participant'])['HR_baseline_corrected']
    return clean(out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',default='artifacts/golden/python.json'); ns=ap.parse_args()
    p=Path(ns.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(generate(),indent=2,sort_keys=True)+'\n')
    print(f'wrote {p}')
if __name__=='__main__': main()
