from __future__ import annotations

import gzip
import importlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import signal, stats


def _df(x: Any, name: str = "dat") -> pd.DataFrame:
    if not isinstance(x, pd.DataFrame):
        raise TypeError(f"`{name}` must be a data frame.")
    return x.copy()


def _cols(x):
    if x is None:
        return []
    return [x] if isinstance(x, str) else list(x)


def _groups(df: pd.DataFrame, cols=None):
    cols = _cols(cols)
    miss = [c for c in cols if c not in df]
    if miss:
        raise ValueError("Missing `group_cols`: " + ", ".join(miss))
    if not cols:
        return [("all_rows", np.arange(len(df)), {})]
    keys = df[cols].astype(object).where(df[cols].notna(), "<NA>").astype(str).agg(" | ".join, axis=1)
    out = []
    for key in pd.unique(keys):
        idx = np.flatnonzero(keys.to_numpy() == key)
        base = df.iloc[idx[0]][cols].to_dict() if len(idx) else {}
        out.append((str(key), idx, base))
    return out


def _sampling_rate(t, supplied=None):
    if supplied is not None:
        supplied = float(supplied)
        return supplied if np.isfinite(supplied) and supplied > 0 else np.nan
    x = np.asarray(t, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan
    d = np.diff(x)
    d = d[np.isfinite(d) & (d > 0)]
    if not len(d):
        return np.nan
    m = float(np.median(d))
    return 1000.0 / m if m > 10 else 1.0 / m


def analyze_gazepoint_ac_susceptance(dat, conductance_col=None, susceptance_col=None, admittance_col=None, phase_col=None, frequency_col=None, time_col=None, group_cols=None):
    df = _df(dat)
    sig = [c for c in [conductance_col, susceptance_col, admittance_col, phase_col] if c is not None]
    if not sig:
        raise ValueError("Supply at least one AC EDA signal column")
    required = [c for c in [*sig, frequency_col, time_col] if c is not None]
    miss = [c for c in required if c not in df]
    if miss:
        raise ValueError("Missing required columns: " + ", ".join(miss))
    nonnum = [c for c in required if not pd.api.types.is_numeric_dtype(df[c])]
    if nonnum:
        raise TypeError("These required columns are not numeric: " + ", ".join(nonnum))
    _groups(df, group_cols)
    out = df.copy()
    g = pd.to_numeric(df[conductance_col], errors="coerce").to_numpy(float) if conductance_col else np.full(len(df), np.nan)
    b = pd.to_numeric(df[susceptance_col], errors="coerce").to_numpy(float) if susceptance_col else np.full(len(df), np.nan)
    adm = pd.to_numeric(df[admittance_col], errors="coerce").to_numpy(float) if admittance_col else (np.sqrt(g*g+b*b) if np.isfinite(g).any() and np.isfinite(b).any() else np.full(len(df), np.nan))
    phase = pd.to_numeric(df[phase_col], errors="coerce").to_numpy(float) if phase_col else (np.arctan2(b,g) if np.isfinite(g).any() and np.isfinite(b).any() else np.full(len(df), np.nan))
    out["ac_eda_conductance_component"] = g
    out["ac_eda_susceptance_component"] = b
    out["ac_eda_admittance_magnitude"] = adm
    out["ac_eda_phase_radians"] = phase
    out["ac_eda_frequency"] = pd.to_numeric(df[frequency_col], errors="coerce") if frequency_col else np.nan
    summary_cols = _cols(group_cols) + (["ac_eda_frequency"] if frequency_col else [])
    rows=[]
    for gid, idx, base in _groups(out, summary_cols):
        rows.append({**base,"group_id":gid,"n_rows":len(idx),"mean_conductance_component":float(np.nanmean(g[idx])) if np.isfinite(g[idx]).any() else np.nan,"mean_susceptance_component":float(np.nanmean(b[idx])) if np.isfinite(b[idx]).any() else np.nan,"mean_admittance_magnitude":float(np.nanmean(adm[idx])) if np.isfinite(adm[idx]).any() else np.nan,"mean_phase_radians":float(np.nanmean(phase[idx])) if np.isfinite(phase[idx]).any() else np.nan,"sd_admittance_magnitude":float(np.nanstd(adm[idx],ddof=1)) if np.isfinite(adm[idx]).sum()>1 else np.nan,"status":"ac_eda_summary_created"})
    sm=pd.DataFrame(rows)
    return {"overview":pd.DataFrame([{"input_rows":len(df),"output_rows":len(out),"summary_rows":len(sm),"status":"ac_eda_susceptance_analysis_complete","interpretation":"AC EDA outputs describe admittance, susceptance, and phase properties when true AC recordings are available. They do not infer emotion, stress, cognition, health status, or diagnosis."}]),"timeseries":out,"summary":sm,"settings":{"conductance_col":conductance_col,"susceptance_col":susceptance_col,"admittance_col":admittance_col,"phase_col":phase_col,"frequency_col":frequency_col,"time_col":time_col,"group_cols":_cols(group_cols)},"class":["gazepoint_ac_susceptance","list"]}


def _holm(p):
    p=np.asarray(p,float);out=np.full(len(p),np.nan);ok=np.flatnonzero(np.isfinite(p))
    if not len(ok): return out
    order=ok[np.argsort(p[ok])];m=len(order);adj=np.empty(m);running=0
    for rank,ix in enumerate(order):
        val=(m-rank)*p[ix];running=max(running,val);adj[rank]=min(1,running)
    for a,ix in zip(adj,order):out[ix]=a
    return out


def run_gazepoint_automated_statistics(dat, outcome_cols, group_col, alpha=.05, p_adjust_method="holm", normality_alpha=.05, min_group_n=3):
    df=_df(dat); outs=_cols(outcome_cols);req=outs+[group_col];miss=[c for c in req if c not in df]
    if miss: raise ValueError("Missing required columns: "+", ".join(miss))
    non=[c for c in outs if not pd.api.types.is_numeric_dtype(df[c])]
    if non: raise TypeError("These `outcome_cols` are not numeric: "+", ".join(non))
    tests=[];normal=[];post=[]
    for oc in outs:
        d=pd.DataFrame({"outcome":pd.to_numeric(df[oc],errors="coerce"),"group":df[group_col]}).dropna(); groups=[(str(g),z.outcome.to_numpy(float)) for g,z in d.groupby("group",sort=True)]
        if len(d)<min_group_n*2 or len(groups)<2 or any(len(x)<min_group_n for _,x in groups):
            tests.append({"outcome":oc,"test":np.nan,"statistic":np.nan,"df1":np.nan,"df2":np.nan,"p_value":np.nan,"p_adjusted":np.nan,"normality_screen_passed":np.nan,"status":"insufficient_group_data"});continue
        normp=[]
        for g,x in groups:
            pv=stats.shapiro(x).pvalue if 3<=len(x)<=5000 and np.std(x,ddof=1)>0 else np.nan;normp.append(pv);normal.append({"outcome":oc,"group":g,"n":len(x),"shapiro_p":pv,"normality_passed":bool(np.isfinite(pv) and pv>=normality_alpha)})
        passn=all(np.isfinite(normp)) and all(v>=normality_alpha for v in normp)
        if passn:
            st,p=stats.f_oneway(*[x for _,x in groups]);name="one_way_anova";df1=len(groups)-1;df2=len(d)-len(groups)
            pairs=[]
            for i in range(len(groups)):
                for j in range(i+1,len(groups)):
                    tt=stats.ttest_ind(groups[i][1],groups[j][1],equal_var=False);pairs.append((groups[i][0],groups[j][0],tt.pvalue))
        else:
            st,p=stats.kruskal(*[x for _,x in groups]);name="kruskal_wallis";df1=len(groups)-1;df2=np.nan;pairs=[]
            for i in range(len(groups)):
                for j in range(i+1,len(groups)):
                    ww=stats.mannwhitneyu(groups[i][1],groups[j][1],alternative='two-sided');pairs.append((groups[i][0],groups[j][0],ww.pvalue))
        padj=_holm([x[2] for x in pairs]) if p_adjust_method=="holm" else np.asarray([x[2] for x in pairs])
        for (g1,g2,pv),pa in zip(pairs,padj):post.append({"outcome":oc,"group_1":g1,"group_2":g2,"p_adjusted":pa,"significant":bool(np.isfinite(pa) and pa<alpha)})
        tests.append({"outcome":oc,"test":name,"statistic":st,"df1":df1,"df2":df2,"p_value":p,"p_adjusted":np.nan,"normality_screen_passed":passn,"status":"test_completed"})
    tt=pd.DataFrame(tests);ok=np.isfinite(pd.to_numeric(tt.p_value,errors='coerce'));tt.loc[ok,'p_adjusted']=_holm(tt.loc[ok,'p_value']) if p_adjust_method=="holm" else tt.loc[ok,'p_value']
    completed=int((tt.status=="test_completed").sum());status="automated_statistics_complete" if completed==len(tt) else ("automated_statistics_partial" if completed else "automated_statistics_failed")
    return {"overview":pd.DataFrame([{"outcome_count":len(outs),"completed_tests":completed,"insufficient_tests":len(tt)-completed,"significant_tests":int((pd.to_numeric(tt.p_adjusted,errors='coerce')<alpha).sum()),"posthoc_rows":len(post),"status":status}]),"test_table":tt,"posthoc_table":pd.DataFrame(post),"normality_table":pd.DataFrame(normal),"settings":{"outcome_cols":outs,"group_col":group_col,"alpha":alpha,"p_adjust_method":p_adjust_method,"normality_alpha":normality_alpha,"min_group_n":min_group_n},"class":["gazepoint_automated_statistics","list"]}


def analyze_gazepoint_cardiorespiratory_causality(dat, respiration_col, cardiac_col, time_col=None, group_cols=None, lag_order=3, min_rows=30, standardise=True):
    df=_df(dat);req=[respiration_col,cardiac_col]+([time_col] if time_col else []);miss=[c for c in req if c not in df]
    if miss:raise ValueError("Missing required columns: "+", ".join(miss))
    rows=[]
    def ols_rss(y,X):
        X=np.c_[np.ones(len(X)),X];coef=np.linalg.lstsq(X,y,rcond=None)[0];res=y-X@coef;return float(res@res)
    for gid,idx,base in _groups(df,group_cols):
        g=df.iloc[idx].copy()
        if time_col:g=g.sort_values(time_col,kind='stable')
        r=pd.to_numeric(g[respiration_col],errors='coerce').to_numpy(float);c=pd.to_numeric(g[cardiac_col],errors='coerce').to_numpy(float);ok=np.isfinite(r)&np.isfinite(c);r=r[ok];c=c[ok]
        if standardise and len(r)>1:
            r=(r-r.mean())/(r.std(ddof=1) or 1);c=(c-c.mean())/(c.std(ddof=1) or 1)
        if len(r)<max(min_rows,2*lag_order+3):
            rows.append({**base,"group_id":gid,"n_rows":len(r),"respiration_to_cardiac_f":np.nan,"respiration_to_cardiac_p":np.nan,"cardiac_to_respiration_f":np.nan,"cardiac_to_respiration_p":np.nan,"status":"insufficient_rows"});continue
        def granger(target, own, other):
            y=target[lag_order:];ownlags=np.column_stack([own[lag_order-k:-k] for k in range(1,lag_order+1)]);othlags=np.column_stack([other[lag_order-k:-k] for k in range(1,lag_order+1)])
            rr=ols_rss(y,ownlags);ru=ols_rss(y,np.c_[ownlags,othlags]);dfn=lag_order;dfd=len(y)-(1+2*lag_order);F=((rr-ru)/dfn)/(ru/dfd) if ru>0 and dfd>0 else np.nan;p=stats.f.sf(F,dfn,dfd) if np.isfinite(F) else np.nan;return F,p
        f1,p1=granger(c,c,r);f2,p2=granger(r,r,c);rows.append({**base,"group_id":gid,"n_rows":len(r),"respiration_to_cardiac_f":f1,"respiration_to_cardiac_p":p1,"cardiac_to_respiration_f":f2,"cardiac_to_respiration_p":p2,"status":"directionality_estimated"})
    sm=pd.DataFrame(rows);good=(sm.status=="directionality_estimated") if len(sm) else pd.Series(dtype=bool);st="cardiorespiratory_directionality_estimated" if len(sm) and good.all() else ("cardiorespiratory_directionality_partial" if good.any() else "cardiorespiratory_directionality_failed")
    return {"overview":pd.DataFrame([{"group_count":len(sm),"status":st,"interpretation":"Granger-style predictive directionality does not prove physiological causality."}]),"causality_summary":sm,"settings":{"respiration_col":respiration_col,"cardiac_col":cardiac_col,"lag_order":lag_order,"min_rows":min_rows,"standardise":standardise},"class":["gazepoint_cardiorespiratory_causality","list"]}


def compare_gazepoint_conditions_bootstrap(data, outcome_col, condition_col, participant_col=None, condition_levels=None, paired=False, by_cols=None, statistic="mean_difference", n_boot=2000, conf_level=.95, seed=None, na_rm=True):
    df=_df(data,"data")
    if len(df)==0:raise ValueError("`data` has no rows.")
    req=[outcome_col,condition_col]+_cols(participant_col)+_cols(by_cols);miss=[c for c in req if c not in df]
    if miss:raise ValueError("Missing columns: "+", ".join(miss))
    if paired and participant_col is None:raise ValueError("`participant_col` is required when `paired = TRUE`.")
    if n_boot<1:raise ValueError("`n_boot` must be a positive integer.")
    if not 0<conf_level<1:raise ValueError("`conf_level` must be between 0 and 1.")
    rng=np.random.default_rng(seed);by=_cols(by_cols);groups=[((),df)] if not by else list(df.groupby(by,sort=False,dropna=False));rows=[];boots={}
    def effect(x1,x2):
        x1=np.asarray(x1,float);x2=np.asarray(x2,float)
        if statistic=="median_difference":return float(np.median(x2)-np.median(x1))
        if statistic=="standardized_mean_difference":
            if paired:
                d=x2-x1;sd=np.std(d,ddof=1);return float(np.mean(d)/sd) if sd>0 else np.nan
            sp=math.sqrt(((len(x1)-1)*np.var(x1,ddof=1)+(len(x2)-1)*np.var(x2,ddof=1))/(len(x1)+len(x2)-2));return float((np.mean(x2)-np.mean(x1))/sp) if sp>0 else np.nan
        return float(np.mean(x2)-np.mean(x1))
    for key,g in groups:
        work=g.copy();work['.y']=pd.to_numeric(work[outcome_col],errors='coerce');work['.c']=work[condition_col].astype(str);work=work[np.isfinite(work['.y'])] if na_rm else work
        levels=list(map(str,condition_levels)) if condition_levels is not None else [str(v) for v in pd.unique(work['.c']) if str(v) not in {'nan','None',''}]
        if len(levels)!=2:raise ValueError("`condition_col` must contain exactly two non-missing conditions, or supply `condition_levels`.")
        unit='row';n_pairs=np.nan
        if participant_col:
            ag=work.groupby([participant_col,'.c'],sort=False,dropna=False)['.y'].mean().reset_index();unit='participant_condition_mean'
            if paired:
                wide=ag[ag['.c'].isin(levels)].pivot(index=participant_col,columns='.c',values='.y').dropna(subset=levels);x1=wide[levels[0]].to_numpy();x2=wide[levels[1]].to_numpy();n_pairs=len(wide);n1=int((ag['.c']==levels[0]).sum());n2=int((ag['.c']==levels[1]).sum())
            else:x1=ag.loc[ag['.c']==levels[0],'.y'].to_numpy();x2=ag.loc[ag['.c']==levels[1],'.y'].to_numpy();n1=len(x1);n2=len(x2)
        else:x1=work.loc[work['.c']==levels[0],'.y'].to_numpy();x2=work.loc[work['.c']==levels[1],'.y'].to_numpy();n1=len(x1);n2=len(x2)
        est=effect(x1,x2);bs=[]
        for _ in range(int(n_boot)):
            if paired:
                ii=rng.integers(0,len(x1),len(x1));bs.append(effect(x1[ii],x2[ii]))
            else:bs.append(effect(rng.choice(x1,len(x1),replace=True),rng.choice(x2,len(x2),replace=True)))
        finite=np.asarray(bs)[np.isfinite(bs)];alpha=1-conf_level;lo,hi=np.quantile(finite,[alpha/2,1-alpha/2],method='weibull') if len(finite) else (np.nan,np.nan);p=2*min(np.mean(finite<=0),np.mean(finite>=0)) if len(finite) else np.nan
        row={"condition_1":levels[0],"condition_2":levels[1],"contrast":f"{levels[1]} - {levels[0]}","statistic":statistic,"estimate":est,"ci_low":lo,"ci_high":hi,"conf_level":conf_level,"p_boot_two_sided":min(1,p) if np.isfinite(p) else np.nan,"n_boot":int(n_boot),"n_valid_boot":len(finite),"paired":paired,"unit_level":unit,"n_condition_1":n1,"n_condition_2":n2,"n_pairs":n_pairs}
        if by:
            if not isinstance(key,tuple):key=(key,)
            row={**dict(zip(by,key)),**row};bkey=" | ".join(map(str,key))
        else:bkey="all"
        rows.append(row);boots[bkey]=np.asarray(bs)
    out=pd.DataFrame(rows);out.attrs['class']=['gazepoint_bootstrap_condition_comparison','data.frame'];out.attrs['bootstrap_samples']=boots;out.attrs['settings']={"outcome_col":outcome_col,"condition_col":condition_col,"participant_col":participant_col,"condition_levels":condition_levels,"paired":paired,"by_cols":by,"statistic":statistic,"n_boot":n_boot,"conf_level":conf_level,"seed":seed,"na_rm":na_rm};return out


def prepare_gazepoint_ctsi_input(dat, eda_col="GSR_US", time_col="CNT", group_cols=None, event_onset_col=None, event_name_col=None, sampling_rate=None, tau0_range=(2,4), tau1_range=(.5,1), sparsity_grid=(.001,.01,.1,1), output_dir=None, prefix="gazepoint_ctsi"):
    df=_df(dat);req=[eda_col,time_col]+_cols(group_cols)+([event_onset_col] if event_onset_col else [])+([event_name_col] if event_name_col else []);miss=[c for c in req if c not in df]
    if miss:raise ValueError("Missing required columns: "+", ".join(miss))
    sig=pd.DataFrame({"time":pd.to_numeric(df[time_col],errors='coerce'),"conductance":pd.to_numeric(df[eda_col],errors='coerce')})
    for c in _cols(group_cols):sig[c]=df[c].to_numpy()
    sig=sig[np.isfinite(sig.time)].sort_values('time').reset_index(drop=True);fs=_sampling_rate(sig.time,sampling_rate)
    ev=pd.DataFrame()
    if event_onset_col:
        ev=pd.DataFrame({"onset":pd.to_numeric(df[event_onset_col],errors='coerce'),"name":df[event_name_col].astype(str) if event_name_col else 'event'})
        for c in _cols(group_cols):ev[c]=df[c].to_numpy()
        ev=ev[np.isfinite(ev.onset)].drop_duplicates().sort_values('onset').reset_index(drop=True)
    cfg=pd.DataFrame([{"sampling_rate_hz":fs,"tau0_min":tau0_range[0],"tau0_max":tau0_range[1],"tau1_min":tau1_range[0],"tau1_max":tau1_range[1],"sparsity_penalty":v} for v in sparsity_grid])
    notes=["Prepared for downstream continuous-time system identification (CTSI) sparse EDA deconvolution.","This bridge does not run the external CTSI solver."]
    written=[]
    if output_dir:
        od=Path(output_dir);od.mkdir(parents=True,exist_ok=True);sf=od/f"{prefix}_signal.csv";cf=od/f"{prefix}_config.csv";sig.to_csv(sf,index=False);cfg.to_csv(cf,index=False);written += [str(sf),str(cf)]
        if len(ev):ef=od/f"{prefix}_events.csv";ev.to_csv(ef,index=False);written.append(str(ef))
    return {"overview":pd.DataFrame([{"signal_rows":len(sig),"event_rows":len(ev),"config_rows":len(cfg),"sampling_rate_hz":fs,"output_written":bool(written),"status":"ctsi_input_prepared" if len(sig) else "ctsi_input_empty_signal"}]),"signal_table":sig,"event_table":ev,"ctsi_config":cfg,"ctsi_notes":notes,"written_files":written,"settings":{"eda_col":eda_col,"time_col":time_col,"group_cols":_cols(group_cols),"sampling_rate":fs},"class":["gazepoint_ctsi_input","list"]}


def optimize_gazepoint_cvxeda_tau(dat, eda_col="GSR_US", time_col="CNT", group_cols=None, tau0_grid=np.arange(2,4.01,.25), tau1=.7, sampling_rate=None, ridge_lambda=.01, max_irf_seconds=20):
    df=_df(dat);grid=np.unique(np.sort(np.asarray(tau0_grid,float)))
    if not len(grid) or np.any(~np.isfinite(grid)) or np.any(grid<=tau1):raise ValueError("`tau0_grid` must contain finite values larger than `tau1`.")
    rows=[]
    for gid,idx,base in _groups(df,group_cols):
        g=df.iloc[idx].sort_values(time_col);t=pd.to_numeric(g[time_col],errors='coerce').to_numpy(float);x=pd.to_numeric(g[eda_col],errors='coerce').to_numpy(float);fs=_sampling_rate(t,sampling_rate);finite=np.isfinite(x)
        for tau0 in grid:
            if not np.isfinite(fs) or finite.sum()<20:rows.append({**base,"group_id":gid,"tau0":tau0,"tau1":tau1,"sampling_rate_hz":fs,"n_samples":len(x),"n_finite":int(finite.sum()),"rmse":np.nan,"mae":np.nan,"residual_sd":np.nan,"correlation":np.nan,"status":"insufficient_signal_or_sampling_rate"});continue
            y=pd.Series(x).interpolate(limit_direction='both').to_numpy(float);y=y-y.mean();tt=np.arange(0,max_irf_seconds+1/fs,1/fs);h=np.exp(-tt/tau0)-np.exp(-tt/tau1);h[h<0]=0;h=h/h.sum() if h.sum()>0 else h;n=len(y);nf=1<<int(np.ceil(np.log2(n+len(h)-1)));yf=np.fft.fft(np.r_[y,np.zeros(nf-n)]);hf=np.fft.fft(np.r_[h,np.zeros(nf-len(h))]);driver=np.conj(hf)*yf/(np.abs(hf)**2+ridge_lambda);recon=np.real(np.fft.ifft(hf*driver))[:n];res=y-recon;rows.append({**base,"group_id":gid,"tau0":tau0,"tau1":tau1,"sampling_rate_hz":fs,"n_samples":len(x),"n_finite":int(finite.sum()),"rmse":float(np.sqrt(np.mean(res**2))),"mae":float(np.mean(np.abs(res))),"residual_sd":float(np.std(res,ddof=1)),"correlation":float(np.corrcoef(y,recon)[0,1]),"status":"tau_fit_evaluated"})
    tab=pd.DataFrame(rows);best=[]
    for gid,d in tab.groupby('group_id',sort=False):
        ok=d[np.isfinite(d.rmse)];r=(ok.loc[ok.rmse.idxmin()] if len(ok) else d.iloc[0]).copy();r['status']='best_tau_selected' if np.isfinite(r.rmse) else 'best_tau_not_selected';best.append(r)
    bt=pd.DataFrame(best).reset_index(drop=True);good=bt.status.eq('best_tau_selected');st='cvxeda_tau_optimization_complete' if good.all() else ('cvxeda_tau_optimization_partial' if good.any() else 'cvxeda_tau_optimization_failed')
    return {"overview":pd.DataFrame([{"group_count":len(bt),"candidate_tau_count":len(grid),"optimization_rows":len(tab),"successful_groups":int(good.sum()),"problem_groups":int((~good).sum()),"status":st}]),"best_tau":bt,"optimization_table":tab,"settings":{"eda_col":eda_col,"time_col":time_col,"group_cols":_cols(group_cols),"tau0_grid":grid.tolist(),"tau1":tau1,"sampling_rate":sampling_rate,"ridge_lambda":ridge_lambda,"max_irf_seconds":max_irf_seconds},"class":["gazepoint_cvxeda_tau_optimization","list"]}


def create_gazepoint_eda_analysis_pipeline(include_external_bridges=True, include_model_templates=True, include_reporting_guidance=True, style="compact"):
    for nm,v in [('include_external_bridges',include_external_bridges),('include_model_templates',include_model_templates),('include_reporting_guidance',include_reporting_guidance)]:
        if not isinstance(v,(bool,np.bool_)):raise ValueError(f"`{nm}` must be TRUE or FALSE.")
    if style not in {'compact','detailed'}:raise ValueError("Invalid `style`.")
    phases=pd.DataFrame([
        [1,'Ingestion and QC','Import, schema, time-reset, activity, and artifact checks'],[2,'Preprocessing and peaks','Standardize/decompose EDA and detect SCR peaks/windows'],[3,'External bridges','Prepare optional external EDA-tool inputs'],[4,'Synchronization and model formatting','Align events and prepare model-ready tables'],[5,'Model templates','Provide conservative exploratory/model templates'],[6,'Reporting','Create methods, checklists, and reproducible report bundles']],columns=['phase','phase_name','purpose'])
    fmap=[(1,'import_gazepoint_biometrics'),(1,'audit_gazepoint_time_resets'),(1,'audit_gazepoint_signal_activity'),(1,'audit_gazepoint_eda_artifacts'),(2,'detect_gazepoint_scr_peaks'),(2,'summarise_gazepoint_scr_event_windows'),(2,'classify_gazepoint_eda_response_pattern'),(4,'align_gazepoint_biometrics_to_ttl'),(4,'estimate_gazepoint_signal_lag'),(4,'prepare_gazepoint_scr_hurdle_model_data'),(4,'prepare_gazepoint_biometrics_lme_data'),(6,'export_gazepoint_biometrics_report_bundle'),(6,'create_gazepoint_biometrics_methods_text')]
    if include_external_bridges:fmap += [(3,'prepare_gazepoint_cvxeda_input'),(3,'prepare_gazepoint_ledalab_input'),(3,'prepare_gazepoint_pspm_input'),(3,'prepare_gazepoint_neurokit_eda_input')]
    fm=pd.DataFrame(fmap,columns=['phase','function_name']);fm['available']=True
    models=pd.DataFrame(columns=['package','template','notes'])
    if include_model_templates:models=pd.DataFrame([{'package':'brms','template':'brm(response ~ condition + (1|participant), family = hurdle_lognormal())','notes':'Template only; verify design and priors.'},{'package':'lme4','template':'lme4::lmer(outcome ~ condition + (1 | participant), data = dat)','notes':'Template only; verify residual assumptions.'}])
    reporting=pd.DataFrame(columns=['topic','guidance']) if not include_reporting_guidance else pd.DataFrame([{'topic':'preprocessing','guidance':'Report units, artifacts, baseline rules, thresholds, and sensitivity analyses.'},{'topic':'interpretation','guidance':'EDA/SCR does not identify emotional valence by itself.'}])
    guard=pd.DataFrame([{'signal_or_method':'GSR/EDA','conservative_interpretation':'Electrodermal activity indexes peripheral conductance/arousal-related dynamics, not emotional valence.'},{'signal_or_method':'Pupil','conservative_interpretation':'Pupil variation is affected by luminance and physiology; it is not direct cognition.'},{'signal_or_method':'Synchronization','conservative_interpretation':'Estimated lag/drift supports timing QC; it is not causal timing.'}])
    return {"overview":pd.DataFrame([{"phase_count":6,"status":"eda_analysis_pipeline_created"}]),"phases":phases,"function_map":fm,"model_templates":models,"reporting_guidance":reporting,"interpretation_guardrails":guard,"settings":{"include_external_bridges":include_external_bridges,"include_model_templates":include_model_templates,"include_reporting_guidance":include_reporting_guidance,"style":style},"class":["gazepoint_eda_analysis_pipeline","list"]}


def run_gazepoint_eda_analysis_pipeline(data=None, path=None, eda_col=None, time_col=None, group_cols=None, signal_cols=None, sampling_rate=None, baseline_window=None, event_windows=None, event_data=None, lag_signal_pair=None, convert_resistance_to_us=False, prepare_external_bridges=True, bridge_methods=("neurokit","cvxeda","ledalab","pspm"), prepare_model_data=True, create_reports=True, output_dir=None, prefix="gazepoint_eda_pipeline", continue_on_error=True):
    from .frontdoor import import_gazepoint_biometrics
    from .qc_dropouts import audit_gazepoint_time_resets, audit_gazepoint_signal_activity
    from .endgame_science import audit_gazepoint_eda_artifacts, detect_gazepoint_scr_peaks
    from .advanced_physiology import prepare_gazepoint_cvxeda_input, prepare_gazepoint_ledalab_input, prepare_gazepoint_pspm_input
    from .deterministic_extensions import prepare_gazepoint_neurokit_eda_input
    if data is None:
        if path is None:raise ValueError("Supply `data` or `path`.")
        data=import_gazepoint_biometrics(path)
    df=_df(data,"data");eda_col=eda_col or next((c for c in ['GSR_US','EDA','GSR'] if c in df),None);time_col=time_col or next((c for c in ['CNT','time','TIME','timestamp'] if c in df),None)
    if eda_col is None or eda_col not in df:raise ValueError(f"Column `{eda_col or 'EDA'}` was not found in `data`.")
    for c in _cols(group_cols):
        if c not in df:raise ValueError(f"Column `{c}` was not found in `data`.")
    blueprint=create_gazepoint_eda_analysis_pipeline(include_external_bridges=prepare_external_bridges,include_model_templates=prepare_model_data,include_reporting_guidance=create_reports)
    phases={}
    phases['phase_1_ingestion_qc']={'data':df,'time_resets':audit_gazepoint_time_resets(df,time_col=time_col,group_cols=group_cols) if time_col else None,'signal_activity':audit_gazepoint_signal_activity(df,signal_cols=signal_cols or [eda_col],group_cols=group_cols),'eda_artifacts':audit_gazepoint_eda_artifacts(df,signal_col=eda_col,time_col=time_col,group_cols=group_cols)}
    phases['phase_2_preprocessing_peaks']={'peaks':detect_gazepoint_scr_peaks(df,signal_col=eda_col,time_col=time_col,group_cols=group_cols)}
    bridges={}
    if prepare_external_bridges:
        funs={'cvxeda':prepare_gazepoint_cvxeda_input,'ledalab':prepare_gazepoint_ledalab_input,'pspm':prepare_gazepoint_pspm_input,'neurokit':prepare_gazepoint_neurokit_eda_input}
        for m in bridge_methods:
            if m in funs:
                try:bridges[m]=funs[m](df,eda_col=eda_col,time_col=time_col,group_cols=group_cols) if m!='neurokit' else funs[m](df,eda_col=eda_col,time_col=time_col,group_cols=group_cols)
                except Exception as e:
                    if not continue_on_error:raise
                    bridges[m]={"error":str(e),"class":["gazepoint_eda_pipeline_error","list"]}
    phases['phase_3_external_bridges']=bridges
    phases['phase_4_sync_model_formatting']={}
    phases['phase_5_model_templates']=blueprint['model_templates']
    phases['phase_6_reporting']={}
    return {"overview":pd.DataFrame([{"phase_count":6,"input_rows":len(df),"eda_col":eda_col,"time_col":time_col,"status":"eda_analysis_pipeline_run_complete"}]),"phases":phases,"model_templates":blueprint['model_templates'],"interpretation_guardrails":blueprint['interpretation_guardrails'],"settings":{"sampling_rate":sampling_rate,"prepare_external_bridges":prepare_external_bridges,"prepare_model_data":prepare_model_data,"create_reports":create_reports},"class":["gazepoint_eda_analysis_pipeline_run","list"]}


def import_gazepoint_lsl_xdf(path, stream_name_pattern="Gazepoint|GP3|GSR|EDA|Biometric|TTL|Pupil|Gaze", include_all_streams=False, flatten=True, pyxdf_module="pyxdf"):
    p=Path(path)
    if not p.exists():raise FileNotFoundError(f"File does not exist: {p}")
    try:mod=importlib.import_module(pyxdf_module)
    except Exception as e:raise ImportError(f"Python module `{pyxdf_module}` is required to read XDF files.") from e
    streams,header=mod.load_xdf(str(p));rows=[];selected=[]
    rx=re.compile(stream_name_pattern,re.I)
    for i,s in enumerate(streams):
        info=s.get('info',{});name=(info.get('name') or ['stream'])[0] if isinstance(info.get('name'),list) else info.get('name','stream')
        if include_all_streams or rx.search(str(name)):selected.append(s)
        if include_all_streams or rx.search(str(name)):
            ts=np.asarray(s.get('time_stamps',[]),float);series=np.asarray(s.get('time_series',[]),object)
            if flatten and series.ndim>=1:
                if series.ndim==1:series=series[:,None]
                for j,t in enumerate(ts):
                    row={'stream_name':str(name),'stream_index':i+1,'timestamp':t}
                    for k,v in enumerate(series[j] if j<len(series) else []):row[f'value_{k+1}']=v
                    rows.append(row)
    return {"overview":pd.DataFrame([{"stream_count":len(streams),"selected_stream_count":len(selected),"flattened_rows":len(rows),"status":"xdf_import_complete"}]),"streams":selected,"data":pd.DataFrame(rows) if flatten else None,"header":header,"settings":{"path":str(p),"stream_name_pattern":stream_name_pattern,"include_all_streams":include_all_streams,"flatten":flatten,"pyxdf_module":pyxdf_module},"class":["gazepoint_lsl_xdf_import","list"]}


def run_gazepoint_online_design_optimization(candidate_table, condition_col="condition", utility_col="expected_utility", block_col=None, cost_col=None, previous_assignments=None, exploration_weight=.10, balance_weight=.10, maximise=True):
    df=_df(candidate_table,"candidate_table");req=[condition_col,utility_col]+([block_col] if block_col else [])+([cost_col] if cost_col else []);miss=[c for c in req if c not in df]
    if miss:raise ValueError("Missing required columns: "+", ".join(miss))
    prev=[] if previous_assignments is None else (previous_assignments[condition_col].astype(str).tolist() if isinstance(previous_assignments,pd.DataFrame) else list(map(str,previous_assignments)))
    out=df.copy();out['.condition']=out[condition_col].astype(str);counts=pd.Series(prev).value_counts();out['.previous_n']=out['.condition'].map(counts).fillna(0).astype(int);mx=max(out['.previous_n'].max(),0);out['.exploration_bonus']=exploration_weight/(out['.previous_n']+1);out['.balance_penalty']=balance_weight*np.where(mx>0,out['.previous_n']/mx,0);out['.cost']=pd.to_numeric(out[cost_col],errors='coerce') if cost_col else 0;out['.optimization_score']=pd.to_numeric(out[utility_col],errors='coerce')+out['.exploration_bonus']-out['.balance_penalty']-out['.cost'];out=out.sort_values('.optimization_score',ascending=not maximise).reset_index(drop=True);out['optimization_rank']=np.arange(1,len(out)+1);rec=out.iloc[[0]].copy();summary=pd.DataFrame({'condition':out['.condition'].unique()});summary['previous_n']=summary.condition.map(counts).fillna(0).astype(int)
    return {"overview":pd.DataFrame([{"candidate_count":len(df),"previous_assignment_count":len(prev),"recommended_condition":rec.iloc[0]['.condition'],"recommended_score":rec.iloc[0]['.optimization_score'],"status":"online_design_recommendation_created"}]),"ranked_candidates":out,"recommendation":rec,"assignment_summary":summary,"settings":{"condition_col":condition_col,"utility_col":utility_col,"cost_col":cost_col,"exploration_weight":exploration_weight,"balance_weight":balance_weight,"maximise":maximise},"class":["gazepoint_online_design_optimization","list"]}


def prepare_gazepoint_pspm_dcm_input(dat, eda_col="GSR_US", time_col="CNT", event_onset_col=None, event_duration_col=None, event_name_col=None, participant_col=None, session_col=None, sampling_rate=None, output_dir=None, prefix="gazepoint_pspm_dcm"):
    df=_df(dat);req=[c for c in [eda_col,time_col,event_onset_col,event_duration_col,event_name_col,participant_col,session_col] if c];miss=[c for c in req if c not in df]
    if miss:raise ValueError("Missing required columns: "+", ".join(miss))
    sig=pd.DataFrame({'time':pd.to_numeric(df[time_col],errors='coerce'),'conductance':pd.to_numeric(df[eda_col],errors='coerce')})
    if participant_col:sig['participant']=df[participant_col].to_numpy()
    if session_col:sig['session']=df[session_col].to_numpy()
    sig=sig[np.isfinite(sig.time)].sort_values('time').reset_index(drop=True);fs=_sampling_rate(sig.time,sampling_rate);ev=pd.DataFrame()
    if event_onset_col:
        ev=pd.DataFrame({'onset':pd.to_numeric(df[event_onset_col],errors='coerce'),'duration':pd.to_numeric(df[event_duration_col],errors='coerce') if event_duration_col else 0,'name':df[event_name_col].astype(str) if event_name_col else 'event'})
        if participant_col:ev['participant']=df[participant_col].to_numpy()
        if session_col:ev['session']=df[session_col].to_numpy()
        ev=ev[np.isfinite(ev.onset)].drop_duplicates().sort_values('onset').reset_index(drop=True)
    notes=["Prepared Gazepoint EDA signal and event tables for downstream PsPM DCM workflows.","This bridge does not run MATLAB, PsPM, Bayesian model inversion, or DCM estimation inside Python."]
    files=[]
    if output_dir:
        od=Path(output_dir);od.mkdir(parents=True,exist_ok=True);sf=od/f'{prefix}_signal.csv';sig.to_csv(sf,index=False);files.append(str(sf))
        if len(ev):ef=od/f'{prefix}_events.csv';ev.to_csv(ef,index=False);files.append(str(ef))
        nf=od/f'{prefix}_notes.txt';nf.write_text('\n'.join(notes));files.append(str(nf))
    return {"overview":pd.DataFrame([{"signal_rows":len(sig),"event_rows":len(ev),"sampling_rate_hz":fs,"output_written":bool(files),"status":"pspm_dcm_input_prepared" if len(sig) else "pspm_dcm_input_empty_signal"}]),"signal_table":sig,"event_table":ev,"pspm_notes":notes,"written_files":files,"settings":{"eda_col":eda_col,"time_col":time_col,"sampling_rate":fs,"output_dir":output_dir,"prefix":prefix},"class":["gazepoint_pspm_dcm_input","list"]}


def run_gazepoint_scr_multiverse(dat, signal_col="GSR_US", time_col="time", trial_cols=None, condition_col=None, participant_col=None, event_time_col=None, latency_windows=((1,3),(1,4),(1,5)), thresholds=(.01,.05), baseline_methods=("median","mean"), baseline_window=(-1,0), response_metrics=("max_minus_baseline",), model_function=None):
    df=_df(dat);req=[signal_col,time_col]+_cols(trial_cols)+([condition_col] if condition_col else [])+([participant_col] if participant_col else [])+([event_time_col] if event_time_col else []);miss=[c for c in req if c not in df]
    if miss:raise ValueError("Missing required columns: "+", ".join(miss))
    tcols=_cols(trial_cols)
    if not tcols:df=df.copy();df['.gpbiometrics_trial_id']='trial_1';tcols=['.gpbiometrics_trial_id']
    specs=[];sid=0
    for wi,w in enumerate(latency_windows,1):
        for th in thresholds:
            for bm in baseline_methods:
                for metric in response_metrics:
                    sid+=1;specs.append({'window_id':wi,'threshold':float(th),'baseline_method':bm,'response_metric':metric,'latency_lower':w[0],'latency_upper':w[1],'specification_id':f'spec_{sid}'})
    grid=pd.DataFrame(specs);rows=[]
    for _,sp in grid.iterrows():
        for gid,idx,base in _groups(df,tcols):
            rel=pd.to_numeric(df.iloc[idx][time_col],errors='coerce').to_numpy(float);x=pd.to_numeric(df.iloc[idx][signal_col],errors='coerce').to_numpy(float)
            if event_time_col:rel=rel-float(pd.to_numeric(df.iloc[idx][event_time_col],errors='coerce').iloc[0])
            bm=(rel>=baseline_window[0])&(rel<=baseline_window[1])&np.isfinite(x);resp=(rel>=sp.latency_lower)&(rel<=sp.latency_upper)&np.isfinite(x);basev=0 if sp.baseline_method=='none' or not bm.any() else (float(np.nanmedian(x[bm])) if sp.baseline_method=='median' else float(np.nanmean(x[bm])))
            amp=peak=np.nan;status='no_response_window_samples'
            if resp.any():
                xx=x[resp];tt=rel[resp];j=int(np.nanargmax(xx));amp=float(np.nanmax(xx)-basev) if sp.response_metric=='max_minus_baseline' else float(np.nanmax(xx)-np.nanmin(xx));peak=float(tt[j]);status='scr_scored'
            row={**sp.to_dict(),"trial_id":gid,**{c:str(df.iloc[idx[0]][c]) for c in [*tcols,participant_col,condition_col] if c and c in df},"baseline_value":basev,"response_amplitude":amp,"response_present":bool(np.isfinite(amp) and amp>=sp.threshold),"peak_time":peak,"status":status};rows.append(row)
    scored=pd.DataFrame(rows);agg=scored.groupby(['specification_id','latency_lower','latency_upper','threshold','baseline_method','response_metric'],dropna=False).agg(mean_response_amplitude=('response_amplitude','mean'),response_rate=('response_present','mean')).reset_index();good=(scored.status=='scr_scored');st='scr_multiverse_complete' if good.all() else ('scr_multiverse_partial' if good.any() else 'scr_multiverse_failed')
    models=None
    if model_function is not None:models={k:model_function(d.copy()) for k,d in scored.groupby('specification_id',sort=False)}
    return {"overview":pd.DataFrame([{"specification_count":len(grid),"trial_count":scored.trial_id.nunique(),"scored_rows":len(scored),"successful_rows":int(good.sum()),"problem_rows":int((~good).sum()),"status":st}]),"specification_grid":grid,"scored_trials":scored,"specification_summary":agg,"model_results":models,"settings":{"signal_col":signal_col,"time_col":time_col,"trial_cols":tcols,"condition_col":condition_col,"participant_col":participant_col,"event_time_col":event_time_col},"class":["gazepoint_scr_multiverse","list"]}
