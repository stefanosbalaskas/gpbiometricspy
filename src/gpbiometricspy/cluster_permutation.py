from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import t as t_dist
import matplotlib.pyplot as plt


def _req(data, cols):
    if not isinstance(data,pd.DataFrame): raise TypeError('`data` must be a data frame.')
    miss=[c for c in cols if c not in data]
    if miss: raise ValueError('Missing required column(s): '+', '.join(miss))


def prepare_gazepoint_timecourse_test_data(data,outcome_col,time_col,condition_col,participant_col,condition_a=None,condition_b=None,time_bin_width=None,aggregation='mean',require_complete=True):
    _req(data,[outcome_col,time_col,condition_col,participant_col])
    if aggregation not in {'mean','median'}: raise ValueError('Invalid `aggregation`.')
    if not pd.api.types.is_numeric_dtype(data[outcome_col]): raise TypeError('`outcome_col` must identify a numeric column.')
    if not pd.api.types.is_numeric_dtype(data[time_col]): raise TypeError('`time_col` must identify a numeric column.')
    time=pd.to_numeric(data[time_col],errors='coerce').to_numpy(float)
    if time_bin_width is not None:
        if not np.isfinite(time_bin_width) or time_bin_width<=0: raise ValueError('`time_bin_width` must be a positive numeric scalar.')
        time=np.floor(time/time_bin_width)*time_bin_width
    x=pd.DataFrame({'participant':data[participant_col].astype(str),'condition':data[condition_col].astype(str),'time':time,'value':pd.to_numeric(data[outcome_col],errors='coerce')})
    x=x[np.isfinite(x.value)&np.isfinite(x.time)&data[condition_col].notna().to_numpy()&data[participant_col].notna().to_numpy()]
    if x.empty: raise ValueError('No complete finite rows remain after filtering.')
    levels=sorted(x.condition.unique())
    if condition_a is None or condition_b is None:
        if len(levels)!=2: raise ValueError('Exactly two condition levels are required, or provide `condition_a` and `condition_b`.')
        condition_a,condition_b=levels
    if condition_a==condition_b: raise ValueError('`condition_a` and `condition_b` must be different.')
    if condition_a not in levels or condition_b not in levels: raise ValueError('`condition_a` and/or `condition_b` not found in `condition_col`.')
    x=x[x.condition.isin([condition_a,condition_b])]
    fun='mean' if aggregation=='mean' else 'median'; out=x.groupby(['participant','condition','time'],as_index=False,sort=True)['value'].agg(fun)
    subjects=sorted(out.participant.unique()); times=sorted(out.time.unique()); expected=len(subjects)*2*len(times)
    dup=out.groupby(['participant','condition','time']).size()
    if (dup!=1).any(): raise ValueError('Prepared data must contain exactly one value per participant, condition, and time.')
    if len(out)!=expected and require_complete: raise ValueError(f'The prepared data are not a complete participant by condition by time grid. Expected {expected} rows but found {len(out)}.')
    out.attrs['gpbiometrics_settings']={'outcome_col':outcome_col,'time_col':time_col,'condition_col':condition_col,'participant_col':participant_col,'condition_a':condition_a,'condition_b':condition_b,'time_bin_width':time_bin_width,'aggregation':aggregation,'require_complete':require_complete}
    return out.reset_index(drop=True)


def _matrices(prep,a,b):
    subjects=sorted(prep.participant.unique()); times=np.array(sorted(prep.time.unique()),float)
    mats=[]
    for cond in [a,b]:
        piv=prep[prep.condition==cond].pivot(index='participant',columns='time',values='value').reindex(index=subjects,columns=times)
        if piv.isna().any().any(): raise ValueError('Complete condition matrices could not be created.')
        mats.append(piv.to_numpy(float))
    return mats[0],mats[1],subjects,times


def _time_t(diff):
    n=diff.shape[0]; mean=np.mean(diff,axis=0); sd=np.std(diff,axis=0,ddof=1); stat=np.divide(mean,sd/np.sqrt(n),out=np.zeros_like(mean),where=np.isfinite(sd)&(sd>0)); p=2*t_dist.sf(np.abs(stat),n-1)
    return stat,p,mean,sd


def _clusters(stat,times,thr,tail):
    rows=[]
    directions=[]
    if tail in {'two.sided','positive'}:directions.append(('positive',stat>=thr))
    if tail in {'two.sided','negative'}:directions.append(('negative',stat<=-thr))
    for direction,inc in directions:
        i=0
        while i<len(inc):
            if not inc[i]:i+=1;continue
            j=i+1
            while j<len(inc) and inc[j]:j+=1
            vals=stat[i:j]; rows.append({'cluster_id':0,'direction':direction,'start_index':i+1,'end_index':j,'start_time':times[i],'end_time':times[j-1],'n_timepoints':j-i,'signed_mass':float(np.sum(vals)),'mass':float(np.sum(np.abs(vals))),'p_value':np.nan,'significant':False});i=j
    for i,r in enumerate(rows,1):r['cluster_id']=i
    return pd.DataFrame(rows,columns=['cluster_id','direction','start_index','end_index','start_time','end_time','n_timepoints','signed_mass','mass','p_value','significant'])


def run_gazepoint_cluster_permutation(data,outcome_col='value',time_col='time',condition_col='condition',participant_col='participant',design='within',condition_a=None,condition_b=None,n_permutations=1000,cluster_forming_alpha=.05,cluster_alpha=.05,tail='two.sided',seed=None,time_bin_width=None,aggregation='mean'):
    if design!='within': raise ValueError('Only `within` design is supported.')
    if tail not in {'two.sided','positive','negative'}: raise ValueError('Invalid `tail`.')
    if int(n_permutations)<1: raise ValueError('`n_permutations` must be positive.')
    if not 0<cluster_forming_alpha<1 or not 0<cluster_alpha<1: raise ValueError('Alpha values must be between 0 and 1.')
    prep=prepare_gazepoint_timecourse_test_data(data,outcome_col,time_col,condition_col,participant_col,condition_a,condition_b,time_bin_width,aggregation,True)
    st=prep.attrs['gpbiometrics_settings']; a,b=st['condition_a'],st['condition_b']; ma,mb,subjects,times=_matrices(prep,a,b); diff=ma-mb
    if len(subjects)<3: raise ValueError('At least three complete participants are required.')
    stat,p,mean,sd=_time_t(diff); df=len(subjects)-1; thr=float(t_dist.ppf(1-cluster_forming_alpha/2 if tail=='two.sided' else 1-cluster_forming_alpha,df)); cl=_clusters(stat,times,thr,tail)
    rng=np.random.default_rng(seed); null=np.zeros(int(n_permutations))
    for z in range(int(n_permutations)):
        signs=rng.choice([-1,1],size=len(subjects)); ps,*_=_time_t(diff*signs[:,None]); pc=_clusters(ps,times,thr,tail); null[z]=float(pc.mass.max()) if len(pc) else 0.0
    if len(cl):
        cl['p_value']=[(1+np.sum(null>=m))/(len(null)+1) for m in cl.mass]; cl['significant']=cl.p_value<=cluster_alpha
    tw=pd.DataFrame({'time':times,'t':stat,'p_uncorrected':p,'mean_difference':mean,'sd_difference':sd,'n':len(subjects)})
    cs=prep.groupby(['condition','time'],as_index=False).value.agg(['mean','std','count']).reset_index(); cs['se']=cs['std']/np.sqrt(cs['count']); cs=cs[['condition','time','mean','se']]
    return {'timewise':tw,'clusters':cl,'null_distribution':null,'condition_summary':cs,'prepared_data':prep,'settings':{'design':design,'condition_a':a,'condition_b':b,'n_permutations':int(n_permutations),'cluster_forming_alpha':cluster_forming_alpha,'cluster_alpha':cluster_alpha,'tail':tail,'threshold_value':thr,'df':df,'n_participants':len(subjects),'n_times':len(times),'seed':seed,'aggregation':aggregation,'time_bin_width':time_bin_width},'warnings':['Within-subject sign-flip permutations only.','Two-condition one-dimensional time-course test only.','Cluster timing is descriptive and must not be interpreted as precise onset or offset.'],'class':'gazepoint_cluster_permutation'}


def summarize_gazepoint_time_clusters(x,alpha=None):
    if not isinstance(x,dict) or x.get('class')!='gazepoint_cluster_permutation': raise TypeError('`x` must be returned by run_gazepoint_cluster_permutation().')
    c=x['clusters'].copy(); alpha=x['settings']['cluster_alpha'] if alpha is None else alpha
    if len(c):c['significant']=c.p_value<=alpha
    return c


def plot_gazepoint_cluster_permutation(x,alpha=None,show_all_clusters=False):
    c=summarize_gazepoint_time_clusters(x,alpha); cs=x['condition_summary']; fig,ax=plt.subplots()
    for cond,b in cs.groupby('condition',sort=False):
        ax.plot(b.time,b['mean'],label=str(cond)); ax.fill_between(b.time,b['mean']-b.se,b['mean']+b.se,alpha=.12)
    if not show_all_clusters and len(c):c=c[c.significant]
    for _,r in c.iterrows():ax.axvspan(r.start_time,r.end_time,alpha=.12)
    ax.set(xlabel='Time',ylabel='Mean signal',title='Gazepoint cluster permutation time course'); ax.legend(); return fig


def simulate_gazepoint_cluster_timecourse_data(n_subjects=12,n_time=60,conditions=('A','B'),effect_start=25,effect_end=38,effect_size=.6,noise_sd=.4,subject_sd=.25,time_start=1,time_step=1,effect_condition='B',seed=None):
    if len(conditions)!=2: raise ValueError('`conditions` must contain exactly two condition labels.')
    if effect_condition not in conditions: raise ValueError('`effect_condition` must be one of `conditions`.')
    if n_subjects<2 or n_time<2: raise ValueError('Need at least two subjects and time bins.')
    rng=np.random.default_rng(seed); subjects=[f'S{i:02d}' for i in range(1,n_subjects+1)]; times=time_start+np.arange(n_time)*time_step; shifts=dict(zip(subjects,rng.normal(0,subject_sd,n_subjects))); smooth=dict(zip(times,np.sin(np.linspace(0,2*np.pi,n_time)))); rows=[]
    for s in subjects:
        for cond in conditions:
            for tt in times:
                eff=effect_size if cond==effect_condition and effect_start<=tt<=effect_end else 0.0; rows.append({'subject':s,'condition':cond,'time':tt,'value':shifts[s]+.1*smooth[tt]+eff+rng.normal(0,noise_sd),'true_effect':eff})
    return pd.DataFrame(rows)


def audit_gazepoint_timecourse_grid(data,subject,condition,time,value=None,max_report_cells=1000):
    _req(data,[subject,condition,time]+([value] if value else [])); d=pd.DataFrame({'subject':data[subject].astype(str),'condition':data[condition].astype(str),'time':data[time]}); cells=d.groupby(['subject','condition','time'],as_index=False).size().rename(columns={'size':'n'}); subs=sorted(d.subject.unique()); conds=sorted(d.condition.unique()); times=sorted(d.time.unique()); expected=pd.MultiIndex.from_product([subs,conds,times],names=['subject','condition','time']).to_frame(index=False); keys=lambda z:set(map(tuple,z[['subject','condition','time']].to_numpy())); missing=expected[~expected.apply(tuple,axis=1).isin(keys(cells))]; dup=cells[cells.n>1]; counts=pd.crosstab(d.subject,d.condition).reset_index(); summary=pd.DataFrame([{'n_rows':len(data),'n_subjects':len(subs),'n_conditions':len(conds),'n_time_bins':len(times),'expected_cells':len(expected),'observed_unique_cells':len(cells),'missing_cells':len(missing),'duplicate_cells':len(dup),'missing_values':int(data[value].isna().sum()) if value else np.nan,'complete_grid':len(missing)==0 and len(dup)==0}]); return {'summary':summary,'missing_cells':missing.head(max_report_cells),'duplicate_cells':dup.head(max_report_cells),'subject_condition_counts':counts,'columns':{'subject':subject,'condition':condition,'time':time,'value':value},'max_report_cells':max_report_cells,'class':'gazepoint_timecourse_grid_audit'}


def diagnose_gazepoint_cluster_design(data,subject,condition,time,value=None,design='within',min_subjects=10):
    if design not in {'within','between'}:raise ValueError('Invalid design.')
    a=audit_gazepoint_timecourse_grid(data,subject,condition,time,value); s=a['summary'].iloc[0]; counts=a['subject_condition_counts'].set_index('subject'); presence=(counts>0).sum(axis=1)
    rows=[('two_conditions',s.n_conditions==2,'error'),('complete_grid',bool(s.complete_grid),'error'),('minimum_subjects',s.n_subjects>=min_subjects,'warning')]
    if design=='within':rows += [('within_subject_condition_presence',bool((presence==counts.shape[1]).all()),'error'),('supported_by_current_runner',True,'ok')]
    else:rows += [('between_subject_condition_presence',bool((presence==1).all()),'error'),('supported_by_current_runner',False,'warning')]
    checks=pd.DataFrame([{'check':n,'passed':p,'severity':('ok' if p else sev),'message':n.replace('_',' ')} for n,p,sev in rows]); passed=bool(checks.loc[checks.severity=='error','passed'].all())
    return {'design':design,'checks':checks,'audit':a,'passed':passed,'columns':{'subject':subject,'condition':condition,'time':time,'value':value},'class':'gazepoint_cluster_design_diagnostic'}


def plot_gazepoint_cluster_null_distribution(result,cluster_id=1,observed_mass=None,bins=30):
    null=np.asarray(result.get('null_distribution',[]),float); null=null[np.isfinite(null)]
    if not len(null):raise ValueError('Could not find a finite null distribution.')
    if observed_mass is None and len(result.get('clusters',[])):
        c=result['clusters']; hit=c[c.cluster_id==cluster_id]; observed_mass=float(hit.mass.iloc[0]) if len(hit) else np.nan
    fig,ax=plt.subplots(); ax.hist(np.abs(null),bins=bins); 
    if observed_mass is not None and np.isfinite(observed_mass):ax.axvline(abs(observed_mass),linestyle='--')
    ax.set(title='Cluster-permutation null distribution',xlabel='Maximum absolute cluster mass',ylabel='Permutation count'); return fig


def report_gazepoint_cluster_permutation(result,cluster_alpha=.05,digits=3,include_assumptions=True):
    c=result.get('clusters',pd.DataFrame()); sig=c[c.p_value<=cluster_alpha] if len(c) and 'p_value' in c else pd.DataFrame()
    if len(sig): desc='; '.join(f"cluster {int(r.cluster_id)} (descriptive time range: {r.start_time} to {r.end_time}, p = {r.p_value:.{digits}f})" for _,r in sig.iterrows()); main='The cluster-based permutation test indicated cluster-level evidence of a condition difference in the tested time course: '+desc+'.'
    else: main=f'The cluster-based permutation test did not indicate cluster-level evidence of a condition difference at alpha = {cluster_alpha}.'
    caution='The temporal extent of any detected cluster should be interpreted descriptively. The test evaluates evidence against the global null of no condition difference anywhere in the tested time range; it does not provide a precise estimate of effect onset or offset.'
    assumptions=['two-condition comparison','participant-level time courses','common participant-condition-time grid','permutation scheme matched to the supported design','cluster timing interpreted descriptively']; text=main+' '+caution+((' Assumptions checked/reported: '+'; '.join(assumptions)+'.') if include_assumptions else '')
    return {'text':text,'clusters':c.copy(),'cluster_alpha':cluster_alpha,'assumptions':assumptions,'class':'gazepoint_cluster_report'}


def run_gazepoint_cluster_threshold_sensitivity(data,dv,time,condition,subject,thresholds=(.01,.025,.05,.10),cluster_alpha=.05,seed=None,**kwargs):
    rows=[]; results={}
    for i,thr in enumerate(thresholds):
        r=run_gazepoint_cluster_permutation(data,outcome_col=dv,time_col=time,condition_col=condition,participant_col=subject,cluster_forming_alpha=thr,cluster_alpha=cluster_alpha,seed=None if seed is None else seed+i,**kwargs); c=r['clusters']; pmin=float(c.p_value.min()) if len(c) else np.nan; rows.append({'threshold':thr,'n_clusters':len(c),'min_p_value':pmin,'n_significant':int((c.p_value<=cluster_alpha).sum()) if len(c) else 0});results[f'threshold_{thr}']=r
    return {'summary':pd.DataFrame(rows),'results':results,'thresholds':list(thresholds),'cluster_alpha':cluster_alpha,'seed':seed,'audit':audit_gazepoint_timecourse_grid(data,subject,condition,time,dv),'class':'gazepoint_cluster_threshold_sensitivity'}


def export_gazepoint_cluster_results(result,path='.',prefix='gazepoint_cluster',overwrite=False):
    od=Path(path);od.mkdir(parents=True,exist_ok=True); outputs={'clusters':result.get('clusters',pd.DataFrame()),'timewise_statistics':result.get('timewise',pd.DataFrame()),'null_distribution':pd.DataFrame({'max_cluster_mass':result.get('null_distribution',[])}),'parameters':pd.DataFrame({'parameter':list(result.get('settings',{})),'value':[str(v) for v in result.get('settings',{}).values()]})}; files=[]
    for n,d in outputs.items():
        q=od/f'{prefix}_{n}.csv'
        if q.exists() and not overwrite:raise FileExistsError(f'File exists: {q}')
        d.to_csv(q,index=False);files.append({'component':n,'file':str(q)})
    rq=od/f'{prefix}_report.txt';
    if rq.exists() and not overwrite:raise FileExistsError(f'File exists: {rq}')
    rq.write_text(report_gazepoint_cluster_permutation(result)['text'],encoding='utf-8');files.append({'component':'report','file':str(rq)});return pd.DataFrame(files)


def _unsupported(name):
    raise NotImplementedError(f'`{name}()` is not implemented as a runnable inferential engine in gpbiometrics yet. The current validated scope is the conservative within-subject, two-condition, one-dimensional time-course workflow.')

def run_gazepoint_cluster_permutation_anova(*args,**kwargs):return _unsupported('run_gazepoint_cluster_permutation_anova')
def run_gazepoint_cluster_permutation_lmer(*args,**kwargs):return _unsupported('run_gazepoint_cluster_permutation_lmer')
def run_gazepoint_tfce(*args,**kwargs):return _unsupported('run_gazepoint_tfce')
def run_gazepoint_multidimensional_cluster_permutation(*args,**kwargs):return _unsupported('run_gazepoint_multidimensional_cluster_permutation')
def estimate_gazepoint_cluster_onset(*args,**kwargs):return _unsupported('estimate_gazepoint_cluster_onset')
def estimate_gazepoint_cluster_offset(*args,**kwargs):return _unsupported('estimate_gazepoint_cluster_offset')
def run_gazepoint_cluster_permutation_covariate_adjusted(*args,**kwargs):return _unsupported('run_gazepoint_cluster_permutation_covariate_adjusted')
def run_gazepoint_cluster_permutation_parallel(*args,**kwargs):return _unsupported('run_gazepoint_cluster_permutation_parallel')


def _long(data,outcome_col,time_col,condition_col,participant_col,aggregate=True):
    _req(data,[outcome_col,time_col,condition_col,participant_col]); d=pd.DataFrame({'participant':data[participant_col].astype(str),'condition':data[condition_col].astype(str),'time':data[time_col],'value':pd.to_numeric(data[outcome_col],errors='coerce')})
    if d.isna().any().any():raise ValueError('Input columns must contain no missing values.')
    if aggregate:d=d.groupby(['participant','condition','time'],as_index=False).value.mean()
    return d.sort_values(['participant','condition','time']).reset_index(drop=True)

def _write(outputs,path,prefix,overwrite):
    if path is None:return outputs
    od=Path(path);od.mkdir(parents=True,exist_ok=True); rows=[]
    for n,d in outputs.items():
        q=od/f'{prefix}_{n}.csv'
        if q.exists() and not overwrite:raise FileExistsError(f'Refusing to overwrite existing file: {q}')
        d.to_csv(q,index=False);rows.append({'component':n,'file':str(q)})
    return pd.DataFrame(rows)

def export_gazepoint_mne_cluster_input(data,outcome_col,time_col,condition_col,participant_col,condition_a=None,condition_b=None,path=None,prefix='gazepoint_mne_cluster',overwrite=False,aggregate=True):
    d=_long(data,outcome_col,time_col,condition_col,participant_col,aggregate); conds=sorted(d.condition.unique());
    if len(conds)!=2:raise ValueError('Difference-matrix export requires exactly two conditions.')
    a=condition_a or conds[0];b=condition_b or conds[1]; wide=d.pivot(index=['participant','time'],columns='condition',values='value').reset_index(); wide['difference']=wide[b]-wide[a]; dm=wide.pivot(index='participant',columns='time',values='difference').reset_index(); dm.columns=['participant']+[f'difference.{c}' for c in dm.columns[1:]]; meta=pd.DataFrame({'field':['source','intended_workflow','condition_a','condition_b','difference_definition','timing_warning'],'value':['gpbiometrics','MNE-style one-sample cluster test on participant-level differences',a,b,'condition_b - condition_a','Cluster timing is descriptive and should not be interpreted as precise onset or offset.']}); return _write({'long':d,'difference_matrix':dm,'metadata':meta},path,prefix,overwrite)

def export_gazepoint_permuco_cluster_input(data,outcome_col,time_col,condition_col,participant_col,path=None,prefix='gazepoint_permuco_cluster',overwrite=False,aggregate=True):
    d=_long(data,outcome_col,time_col,condition_col,participant_col,aggregate); meta=pd.DataFrame({'field':['source','intended_workflow','timing_warning'],'value':['gpbiometrics','permuco-style cluster permutation','Cluster timing is descriptive.']});return _write({'long':d,'metadata':meta},path,prefix,overwrite)

def export_gazepoint_permutes_cluster_input(data,outcome_col,time_col,condition_col,participant_col,path=None,prefix='gazepoint_permutes_cluster',overwrite=False,aggregate=True):
    d=_long(data,outcome_col,time_col,condition_col,participant_col,aggregate); meta=pd.DataFrame({'field':['source','intended_workflow','timing_warning'],'value':['gpbiometrics','permutes-style cluster permutation','Cluster timing is descriptive.']});return _write({'long':d,'metadata':meta},path,prefix,overwrite)
