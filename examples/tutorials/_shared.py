from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import json, tempfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import gpbiometricspy as gp

def demo(rows=900):
    d=gp.load_kiosk_demo(participants=['synthetic_kiosk_p001']).copy().iloc[:rows].reset_index(drop=True)
    return d

def pulse_frame(fs=100,seconds=20):
    t=np.arange(0,seconds+1/fs/2,1/fs); x=np.sin(2*np.pi*1.2*t)**8+.02*np.sin(2*np.pi*6*t)
    return pd.DataFrame({'participant':'P01','time_s':t,'pulse':x})

def summarize(value):
    if isinstance(value,pd.DataFrame): return {'type':'DataFrame','rows':len(value),'columns':len(value.columns)}
    if isinstance(value,pd.Series): return {'type':'Series','rows':len(value)}
    if isinstance(value,dict): return {'type':'dict','keys':sorted(map(str,value.keys()))[:20]}
    if isinstance(value,np.ndarray): return {'type':'ndarray','shape':list(value.shape)}
    return {'type':type(value).__name__}

def finish(name,**objects):
    plt.close('all'); print(json.dumps({'tutorial':name,'status':'PASS','objects':{k:summarize(v) for k,v in objects.items()}},sort_keys=True))
