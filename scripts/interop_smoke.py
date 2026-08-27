#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import argparse, importlib, tempfile
import numpy as np
import pandas as pd
import gpbiometricspy as gp

def pulse(fs=100, seconds=15):
    t=np.arange(0,seconds+1/fs/2,1/fs); x=np.sin(2*np.pi*1.2*t)**8+.02*np.sin(2*np.pi*6*t); return t,x

def run(name):
    if name=='heartpy':
        hp=importlib.import_module('heartpy'); t,x=pulse(); wd,m=hp.process(x,sample_rate=100); assert np.isfinite(m['bpm'])
        d=pd.DataFrame({'time_s':t,'pulse':x,'participant':'P01'}); out=gp.run_gazepoint_heartpy_crosscheck(d,'pulse','time_s','participant',100,high_precision=False); assert out['heartpy_available']
    elif name=='biosppy':
        importlib.import_module('biosppy'); from biosppy.signals import ppg
        t,x=pulse(); ext=ppg.ppg(signal=x,sampling_rate=100,show=False); assert len(ext['heart_rate'])>0
        d=pd.DataFrame({'time_s':t,'ppg':x,'participant':'P01'}); assert len(gp.run_gazepoint_biosppy_ppg(d,'ppg','time_s','participant',100)['peaks'])>5
    elif name=='pyhrv':
        importlib.import_module('pyhrv'); td=importlib.import_module('pyhrv.time_domain'); nni=800+20*np.sin(np.linspace(0,8*np.pi,120)); res=td.rmssd(nni=nni); assert res is not None
        native=gp.run_gazepoint_pyhrv_style(nni_ms=nni); assert 'time_domain' in native
    elif name=='neurokit':
        importlib.import_module('neurokit2'); fs=50; t=np.arange(0,30,1/fs); eda=1+.01*t+.3*np.exp(-((t-8)**2)/.8)+.2*np.exp(-((t-18)**2)); d=pd.DataFrame({'time_s':t,'GSR_US':eda,'participant':'P01'})
        out=gp.run_gazepoint_neurokit_eda_crosscheck(d,eda_col='GSR_US',time_col='time_s',group_cols='participant',sampling_rate=fs,execute=True); assert bool(out['overview'].iloc[0]['executed'])
    elif name=='mne':
        mne=importlib.import_module('mne'); d=pd.DataFrame({'time_s':[0,.01,.02,.03],'pupil':[3,3.1,3.2,3.3],'GSR_US':[1,1.1,1.2,1.3]}); prep=gp.prepare_gazepoint_mne_input(d,channel_cols=['pupil','GSR_US'],time_col='time_s',sampling_rate_hz=100)
        info=mne.create_info(ch_names=prep['channel_info']['channel_name'].tolist(),sfreq=100,ch_types=['misc']*2); raw=mne.io.RawArray(prep['data'],info,verbose=False); assert raw.n_times==4
    elif name=='pylsl':
        pylsl=importlib.import_module('pylsl'); assert np.isfinite(float(pylsl.local_clock()))
        synced=gp.sync_gazepoint_signals_via_lsl({'a':pd.DataFrame({'time_s':[0,1,2],'x':[1,2,3]}),'b':pd.DataFrame({'time_s':[.1,1.1,2.1],'y':[4,5,6]})},reference='a',clock_offsets_s={'a':0,'b':-.1}); assert np.allclose(synced['streams']['b']['.lsl_time_relative_s'],[0,1,2])
    elif name=='pyxdf':
        pyxdf=importlib.import_module('pyxdf'); assert hasattr(pyxdf,'load_xdf')
        shaped={'gaze':{'time_stamps':[10,10.1,10.2],'time_series':pd.DataFrame({'x':[.2,.3,.4]})}}; synced=gp.sync_gazepoint_signals_via_lsl(shaped); assert len(synced['streams']['gaze'])==3
    else: raise ValueError(name)
    print(f'interoperability smoke PASS: {name}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('backend',choices=['heartpy','biosppy','pyhrv','neurokit','mne','pylsl','pyxdf']); ns=ap.parse_args(); run(ns.backend)
if __name__=='__main__': main()
