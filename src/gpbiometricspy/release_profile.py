from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd

_DEFAULT_PATTERNS={
'import_export':r'import|read|parse|export|write|bundle|manifest|dictionary','validation_audit':r'audit|validate|check|detect|assess|flag','quality_control':r'quality|missingness|dropout|nonwear|artifact|outlier|smooth|filter|clean','pupil_gaze':r'(^|_)pupil($|_)|(^|_)gaze($|_)|fixation|aoi|scanpath|saccade|luminance','physiology':r'eda|gsr|scr|ppg|hr|ibi|hrv|beat|heart|pulse','synchronization':r'sync|lag|ttl|align|time|sampling|reset','modelling_statistics':r'model|fit|cluster|permutation|bootstrap|estimate|compare|prediction','reporting_review':r'report|summary|summarize|checklist|readiness|preregistration|pipeline|dashboard','simulation_reproducibility':r'simulate|synthetic|anonymize|reproducibility|roadmap','adapters_external':r'heartpy|pyppg|pspm|ledalab|cvxeda|gazer|eyetools|lsl|xdf|ctsi'}

def _path(path):
    if not isinstance(path,(str,Path)) or not str(path):raise ValueError('`path` must be a single non-empty path.')
    p=Path(path)
    if not p.exists():raise ValueError('`path` does not exist.')
    return p.resolve()

def _chars(x,name,allow=True):
    if x is None and allow:return None
    vals=[x] if isinstance(x,str) else list(x)
    if any(v is None or not str(v) for v in vals):raise ValueError(f'`{name}` must contain non-empty values.')
    return list(dict.fromkeys(map(str,vals)))

def summarize_gazepoint_feature_coverage(path='.',exports=None,patterns=None):
    p=_path(path)
    if exports is None:
        ns=p/'NAMESPACE';exports=[]
        if ns.exists(): exports=re.findall(r'export\(([^)]+)\)',ns.read_text(errors='replace'))
    else: exports=_chars(exports,'exports',False)
    patterns=_DEFAULT_PATTERNS if patterns is None else patterns
    if not isinstance(patterns,dict) or any(not str(k) or not isinstance(v,str) or not v for k,v in patterns.items()):raise ValueError('`patterns` must be a named mapping and each pattern a single non-empty string.')
    rows=[]
    for domain,pat in patterns.items():
        hits=[x for x in exports if re.search(pat,x,re.I)];rows.append({'domain':domain,'n_exports':len(hits),'examples':', '.join(hits[:6]) if hits else None})
    return pd.DataFrame(rows)

def create_gazepoint_release_checklist(audit=None,include_optional=True):
    if not isinstance(include_optional,bool):raise ValueError('`include_optional` must be TRUE or FALSE.')
    rows=[('package','DESCRIPTION is present and parseable',True),('package','NAMESPACE is present and contains exports',True),('package','R source files are present',True),('tests','testthat directory is present',True),('tests','exported helpers have at least heuristic test references',False),('documentation','manual pages exist for exported helpers',True),('documentation','vignettes or pkgdown articles are present',False),('documentation','NEWS/README/ROADMAP materials are reviewed manually',False),('pkgdown','pkgdown reference pages are current',False),('reproducibility','urlchecker and R CMD check are run before release',True),('scope','no unsupported biometric, clinical, diagnostic, or psychological claims are introduced',True)]
    if include_optional:rows += [('release','GitHub Actions are checked after push',False),('release','pkgdown site is rebuilt after reference changes',False),('release','release notes are checked against exported functions',False)]
    out=pd.DataFrame(rows,columns=['phase','item','required']);checks=audit.get('checks') if isinstance(audit,dict) else audit
    if not isinstance(checks,pd.DataFrame) or len(checks)==0:out['status']='not_checked';out['evidence']=None;return out
    lookup={'package':['package_structure','description','namespace'],'tests':['tests'],'documentation':['documentation'],'pkgdown':['pkgdown'],'reproducibility':['tests','pkgdown'],'scope':['roadmap','description'],'release':['pkgdown','tests','documentation']}
    status=[];evidence=[]
    for phase in out.phase:
        sub=checks[checks.area.isin(lookup.get(phase,[]))];sts=sub.status.astype(str).str.lower().tolist()
        st='fail' if any(x in {'fail','failed','error','missing','false'} for x in sts) else ('warn' if any(x in {'warn','warning','review','flag','flagged','caution'} for x in sts) else ('pass' if any(x in {'pass','passed','ok','complete','completed','true'} for x in sts) else 'not_checked'))
        status.append(st);evidence.append(', '.join(pd.unique(sub['check'])[:4]) if len(sub) else None)
    out['status']=status;out['evidence']=evidence;return out

def audit_gazepoint_release_readiness(path='.',required_files=('DESCRIPTION','NAMESPACE','R','man','tests/testthat','_pkgdown.yml'),expected_exports=None,roadmap_terms=None,require_pkgdown=True):
    p=_path(path);req=_chars(required_files,'required_files',False);exp=_chars(expected_exports,'expected_exports',True);terms=_chars(roadmap_terms,'roadmap_terms',True)
    if not isinstance(require_pkgdown,bool):raise ValueError('`require_pkgdown` must be TRUE or FALSE.')
    rows=[]
    def add(area,check,item,status,message):rows.append({'area':area,'check':check,'item':item,'status':status,'message':message})
    for r in req:add('package_structure','required_path',r,'pass' if (p/r).exists() else 'fail','Required path is present.' if (p/r).exists() else 'Required path is missing.')
    desc=p/'DESCRIPTION';add('description','parse_description','DESCRIPTION','pass' if desc.exists() and 'Package:' in desc.read_text(errors='replace') else 'fail','DESCRIPTION parsed.' if desc.exists() else 'DESCRIPTION missing.')
    ns=p/'NAMESPACE';exports=re.findall(r'export\(([^)]+)\)',ns.read_text(errors='replace')) if ns.exists() else []
    add('namespace','exports_present','NAMESPACE','pass' if exports else 'fail','Exports found.' if exports else 'No exports found.')
    if exp is not None:
        missing=[x for x in exp if x not in exports];add('namespace','expected_exports','exports','fail' if missing else 'pass','Missing: '+', '.join(missing) if missing else 'All expected exports present.')
    tests='\n'.join(f.read_text(errors='replace') for f in (p/'tests'/'testthat').glob('*.R')) if (p/'tests'/'testthat').exists() else ''
    ntest=sum(x in tests for x in exports);add('tests','export_test_references','exports','pass' if exports and ntest==len(exports) else ('warn' if ntest else 'fail'),f'{ntest}/{len(exports)} exports referenced in tests.')
    man=p/'man';manual=sum((man/(x+'.Rd')).exists() for x in exports);add('documentation','manual_files_present','man','pass' if man.exists() else 'fail','Manual directory present.' if man.exists() else 'Manual directory missing.');add('documentation','export_manual_pages','exports','pass' if exports and manual==len(exports) else 'warn',f'{manual}/{len(exports)} export manual pages found.')
    ref=p/'docs'/'reference';refs=sum((ref/(x+'.html')).exists() for x in exports)
    add('pkgdown','export_reference_pages','docs/reference','not_checked' if not require_pkgdown else ('pass' if exports and refs==len(exports) else 'warn'),f'{refs}/{len(exports)} reference pages found.')
    arts=list((p/'vignettes').glob('*')) if (p/'vignettes').exists() else [];arts += list((p/'docs'/'articles').glob('*')) if (p/'docs'/'articles').exists() else []
    add('documentation','vignettes_articles','articles','pass' if arts else 'warn',f'{len(arts)} article/vignette files found.')
    if terms:
        text='\n'.join(f.read_text(errors='replace') for root in ['R','tests','man','docs'] if (p/root).exists() for f in (p/root).rglob('*') if f.is_file())
        for term in terms:add('roadmap','roadmap_term_present',term,'pass' if re.search(re.escape(term),text,re.I) else 'warn','Roadmap term found.' if re.search(re.escape(term),text,re.I) else 'Roadmap term not found.')
    checks=pd.DataFrame(rows);nfail=int((checks.status=='fail').sum());nwarn=int((checks.status=='warn').sum());overview=pd.DataFrame([{'n_checks':len(checks),'n_pass':int((checks.status=='pass').sum()),'n_warn':nwarn,'n_fail':nfail,'n_not_checked':int((checks.status=='not_checked').sum()),'release_ready':nfail==0,'needs_review':(nfail+nwarn)>0}])
    out={'overview':overview,'checks':checks,'exports':exports,'feature_coverage':summarize_gazepoint_feature_coverage(p,exports),'settings':{'path':str(p),'required_files':req,'expected_exports':exp,'roadmap_terms':terms,'require_pkgdown':require_pkgdown}}
    out['checklist']=create_gazepoint_release_checklist(checks);return out

def _role(col):
    x=str(col).upper()
    if re.search(r'^(CNT|TIME|TIME_TICK|TIME_TICK_MS|TIMESTAMP|MSTIMER|TRIAL_TIME|TIME_MS)$|TIME|TICK|CNT',x):return 'time'
    if re.search(r'^TTL|TTL[0-9]+|MARKER|USER_DATA|USER$|EVENT',x):return 'ttl_event'
    if re.search(r'AOI|AREA_OF_INTEREST|INTEREST_AREA|IA_',x):return 'aoi'
    if re.search(r'PUPIL|LPMM|RPMM|LPD|RPD',x):return 'pupil'
    if re.search(r'GSR|EDA|SCR|SCL|PHASIC|TONIC',x):return 'eda_gsr'
    if re.search(r'^(HR|BPM)$|HEART|HEART_RATE|HEARTRATE',x):return 'heart_rate'
    if re.search(r'IBI|RRI|RR_INTERVAL|RR$|NNI|NN_INTERVAL',x):return 'ibi_rr'
    if re.search(r'PPG|PULSE|HRP|BVP',x):return 'ppg_pulse'
    if re.search(r'DIAL|ENGAGEMENT',x):return 'engagement_dial'
    if re.search(r'FPOG|BPOG|LPOG|RPOG|GAZE|X$|Y$',x):return 'gaze'
    return 'other'

def profile_gazepoint_export_folder(path,pattern=r'\.csv$',recursive=False,max_files=np.inf,max_rows=np.inf,na_strings=('', 'NA','NaN')):
    p=_path(path)
    if not p.is_dir():raise ValueError('`path` does not exist or is not a folder.')
    if max_files<=0 or max_rows<=0:raise ValueError('`max_files` and `max_rows` must be positive.')
    rx=re.compile(pattern,re.I);files=sorted([f for f in (p.rglob('*') if recursive else p.iterdir()) if f.is_file() and rx.search(f.name)])
    if np.isfinite(max_files):files=files[:int(max_files)]
    settings={'path':str(p),'pattern':pattern,'recursive':recursive,'max_files':max_files,'max_rows':max_rows}
    if not files:
        return {'overview':pd.DataFrame([{'path':str(p),'n_files':0,'n_readable_files':0,'n_read_errors':0,'total_rows_profiled':0,'total_size_bytes':0,'n_unique_extensions':0,'n_unique_column_sets':0,'any_time_columns':False,'any_ttl_columns':False,'any_aoi_columns':False,'any_signal_columns':False}]),'files':pd.DataFrame(),'columns':pd.DataFrame(),'warnings':pd.DataFrame([{'severity':'warning','issue':'no_matching_files','message':'No matching files found.'}]),'settings':settings}
    frows=[];crows=[]
    for f in files:
        st=f.stat();base={'file':str(f.resolve()),'relative_path':str(f.relative_to(p)),'file_label':f.name,'extension':f.suffix.lower(),'size_bytes':st.st_size,'modified_time':str(st.st_mtime)}
        try:
            nrows=None if np.isinf(max_rows) else int(max_rows);dat=pd.read_csv(f,nrows=nrows,na_values=list(na_strings))
            roles={c:_role(c) for c in dat.columns}
            for c in dat:
                x=dat[c];nm=x.dropna();numeric=pd.api.types.is_numeric_dtype(x);crows.append({**{k:base[k] for k in ['file','relative_path','file_label']},'column':c,'role':roles[c],'type':'numeric' if numeric else ('logical' if pd.api.types.is_bool_dtype(x) else 'character'),'n_missing':int(x.isna().sum()),'missing_prop':float(x.isna().mean()),'n_unique':int(nm.nunique()),'numeric_sd':float(nm.std(ddof=1)) if numeric and len(nm)>1 else np.nan,'all_zero':bool(numeric and len(nm)>0 and (nm==0).all()),'constant':bool(nm.nunique()<=1) if len(nm)>0 else np.nan})
            def cs(role):
                z=[c for c,r in roles.items() if r==role];return '; '.join(z) if z else None
            num=[c for c in dat if pd.api.types.is_numeric_dtype(dat[c])]
            frows.append({**base,'status':'readable','n_rows':len(dat),'n_cols':dat.shape[1],'column_signature':' | '.join(sorted(dat.columns)),'column_names':'; '.join(dat.columns),'time_columns':cs('time'),'ttl_columns':cs('ttl_event'),'aoi_columns':cs('aoi'),'gaze_columns':cs('gaze'),'pupil_columns':cs('pupil'),'eda_gsr_columns':cs('eda_gsr'),'heart_rate_columns':cs('heart_rate'),'ibi_rr_columns':cs('ibi_rr'),'ppg_pulse_columns':cs('ppg_pulse'),'engagement_dial_columns':cs('engagement_dial'),'numeric_cols':len(num),'constant_numeric_cols':sum(dat[c].dropna().nunique()<=1 for c in num),'zero_numeric_cols':sum(len(dat[c].dropna())>0 and (dat[c].dropna()==0).all() for c in num),'read_error':None})
        except Exception as e:
            frows.append({**base,'status':'read_error','n_rows':0,'n_cols':0,'column_signature':None,'column_names':None,'time_columns':None,'ttl_columns':None,'aoi_columns':None,'gaze_columns':None,'pupil_columns':None,'eda_gsr_columns':None,'heart_rate_columns':None,'ibi_rr_columns':None,'ppg_pulse_columns':None,'engagement_dial_columns':None,'numeric_cols':0,'constant_numeric_cols':0,'zero_numeric_cols':0,'read_error':str(e)})
    ft=pd.DataFrame(frows);ct=pd.DataFrame(crows);readable=ft.status=='readable';roles=set(ct.role) if len(ct) else set();signals={'gaze','pupil','eda_gsr','heart_rate','ibi_rr','ppg_pulse','engagement_dial'}
    ov=pd.DataFrame([{'path':str(p),'n_files':len(ft),'n_readable_files':int(readable.sum()),'n_read_errors':int((ft.status=='read_error').sum()),'total_rows_profiled':int(ft.n_rows.sum()),'total_size_bytes':int(ft.size_bytes.sum()),'n_unique_extensions':ft.extension.nunique(),'n_unique_column_sets':ft.loc[readable,'column_signature'].nunique(),'any_time_columns':'time' in roles,'any_ttl_columns':'ttl_event' in roles,'any_aoi_columns':'aoi' in roles,'any_signal_columns':bool(roles&signals)}])
    warnings=[]
    if ov.iloc[0].n_read_errors:warnings.append({'severity':'warning','issue':'read_errors','message':'Some files could not be read.'})
    if ov.iloc[0].n_readable_files==0:warnings.append({'severity':'error','issue':'no_readable_files','message':'No matching files could be read.'})
    if not ov.iloc[0].any_time_columns:warnings.append({'severity':'warning','issue':'no_time_columns_detected','message':'No likely time columns were detected.'})
    if not ov.iloc[0].any_signal_columns:warnings.append({'severity':'warning','issue':'no_signal_columns_detected','message':'No likely signal columns were detected.'})
    return {'overview':ov,'files':ft,'columns':ct,'warnings':pd.DataFrame(warnings,columns=['severity','issue','message']),'settings':settings}

def compare_gazepoint_export_profiles(*profiles,labels=None):
    if len(profiles)==1 and isinstance(profiles[0],(list,tuple)):profiles=tuple(profiles[0])
    if len(profiles)<2:raise ValueError('Provide at least two export-folder profiles.')
    if labels is None:labels=[f'profile_{i+1}' for i in range(len(profiles))]
    if len(labels)!=len(profiles):raise ValueError('`labels` must have one label per profile.')
    ov=pd.concat([p['overview'].assign(profile=l) for p,l in zip(profiles,labels)],ignore_index=True);ov=ov[['profile']+[c for c in ov if c!='profile']]
    rc=[]
    for p,l in zip(profiles,labels):
        if len(p['columns']):
            for role,n in p['columns'].role.value_counts().items():rc.append({'profile':l,'role':role,'n_columns':int(n)})
    allc=sorted(set().union(*(set(p['columns'].column) if len(p['columns']) else set() for p in profiles)));cp=[]
    for c in allc:
        present=[l for p,l in zip(profiles,labels) if len(p['columns']) and c in set(p['columns'].column)];cp.append({'column':c,'n_profiles_present':len(present),'profiles_present':'; '.join(present)})
    return {'overview':ov,'role_coverage':pd.DataFrame(rc),'column_presence':pd.DataFrame(cp),'labels':labels}

def write_gazepoint_export_profile(profile,path,prefix='gazepoint_export_profile',overwrite=False):
    if not isinstance(profile,dict) or 'overview' not in profile:raise TypeError('`profile` must be returned by `profile_gazepoint_export_folder()`.')
    out=Path(path);out.mkdir(parents=True,exist_ok=True);spec=[('overview','_overview.csv'),('files','_files.csv'),('columns','_columns.csv'),('warnings','_warnings.csv'),('summary','_summary.txt')];rows=[]
    for comp,suf in spec:
        f=out/(prefix+suf)
        if f.exists() and not overwrite:raise FileExistsError('Output file(s) already exist. Use `overwrite = TRUE`.')
        if comp=='summary':f.write_text('Gazepoint export folder profile\n================================\n\nPath: '+str(profile['settings']['path']))
        else:profile[comp].to_csv(f,index=False)
        rows.append({'component':comp,'file':str(f)})
    return pd.DataFrame(rows)

def plot_gazepoint_export_profile(profile,type='files',top_n=20):
    import matplotlib.pyplot as plt
    if top_n<=0:raise ValueError('`top_n` must be positive.')
    fig,ax=plt.subplots()
    if type=='files':d=profile['files'].extension.value_counts();ax.bar(d.index,d.values)
    elif type=='roles':d=profile['columns'].role.value_counts();ax.barh(d.index,d.values)
    elif type=='missingness':
        d=profile['columns'].groupby(['column','role']).missing_prop.mean().sort_values(ascending=False).head(top_n);ax.barh([x[0] for x in d.index],d.values)
    elif type=='activity':
        d=profile['files'].head(top_n);ax.bar(d.file_label,d.constant_numeric_cols,label='constant');ax.bar(d.file_label,d.zero_numeric_cols,bottom=d.constant_numeric_cols,label='zero')
    else:raise ValueError('Unsupported `type`.')
    fig.tight_layout();return fig
