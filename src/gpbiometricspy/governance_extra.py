from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import importlib.metadata, platform
import numpy as np, pandas as pd

_REQ=[('design','design_conditions','Conditions, participant/trial identifiers, and design structure are specified.',True,'design','condition,participant,trial'),('sampling','sampling_plan','Sampling plan, inclusion criteria, and intended sample size are documented.',True,'sampling','sample_size,inclusion_criteria'),('outcomes','primary_outcomes','Primary outcomes or main dependent variables are identified.',True,'outcomes','outcome,role'),('preprocessing','preprocessing_plan','Preprocessing steps and their ordering are documented.',True,'preprocessing','step,decision'),('quality_control','qc_thresholds','Quality-control metrics, thresholds, or flagging rules are documented.',True,'quality_control','metric,rule'),('exclusions','exclusion_rules','Exclusion rules and their intended actions are documented.',True,'exclusions','rule,action'),('missingness','missing_data_plan','Missing-data handling decisions are documented.',True,'missingness','variable,handling'),('time_windows','analysis_windows','Analysis windows or event-aligned time intervals are documented where applicable.',True,'time_windows','window_start,window_end'),('analysis','analysis_models','Planned analysis models or summary comparisons are documented.',True,'analysis','outcome,model'),('reporting','reporting_decisions','Reporting decisions, tables, figures, or reviewer-facing outputs are documented.',True,'reporting','item,decision')]
_OPT=[('randomization','randomization_checks','Randomization or balance checks are documented where applicable.',False,'randomization','check,result'),('robustness','sensitivity_analyses','Planned sensitivity analyses or robustness checks are documented.',False,'sensitivity','analysis,reason'),('reproducibility','data_dictionary','A data dictionary or variable map is available.',False,'dictionary','variable,description'),('reproducibility','analysis_manifest','An analysis manifest or reproducibility ledger is available.',False,'manifest','field,value')]
def create_gazepoint_preregistration_checklist(study_id=None,include_optional=True,custom_items=None):
 if study_id is not None and not isinstance(study_id,str):raise ValueError('`study_id` must be NULL or a single character string.')
 if not isinstance(include_optional,bool):raise ValueError('`include_optional` must be TRUE or FALSE.')
 rows=list(_REQ)+(list(_OPT) if include_optional else [])
 if custom_items is not None:
  if not isinstance(custom_items,pd.DataFrame) or not {'domain','item_id','item'}<=set(custom_items):raise ValueError('`custom_items` is missing required columns.')
  x=custom_items.copy();x['required']=x.get('required',True);x['evidence_key']=x.get('evidence_key',x['item_id']);x['required_fields']=x.get('required_fields','');rows += list(x[['domain','item_id','item','required','evidence_key','required_fields']].itertuples(index=False,name=None))
 out=pd.DataFrame(rows,columns=['domain','item_id','item','required','evidence_key','required_fields']);out.insert(0,'study_id',study_id);out['status']='not_checked';out['notes']=None;return out

def _evidence_info(obj):
 if isinstance(obj,pd.DataFrame):return 'data.frame',len(obj),len(obj)>0,list(obj.columns),True
 if isinstance(obj,dict):return 'list',len(obj),len(obj)>0,list(obj.keys()),True
 if isinstance(obj,(list,tuple,str,np.ndarray,pd.Series)):return type(obj).__name__,len(obj),len(obj)>0,[],False
 if obj is None:return 'None',0,False,[],False
 return type(obj).__name__,1,True,[],False

def audit_gazepoint_preregistration_consistency(checklist=None,evidence=None,require_required_fields=True):
 if checklist is None:checklist=create_gazepoint_preregistration_checklist()
 req={'required','evidence_key','required_fields','item_id','domain'}
 if not isinstance(checklist,pd.DataFrame) or not req<=set(checklist):raise ValueError('`checklist` is missing required columns.')
 if not isinstance(require_required_fields,bool):raise ValueError('`require_required_fields` must be TRUE or FALSE.')
 evidence={} if evidence is None else evidence
 if not isinstance(evidence,dict) or any(not str(k) for k in evidence):raise ValueError('`evidence` must be a named list.')
 rows=[]
 for _,r in checklist.iterrows():
  key=r.evidence_key;has=key in evidence;typ=None;n=np.nan;complete=False;present=[];missing=[]
  if has:
   typ,n,complete,present,checkable=_evidence_info(evidence[key]);required=[x.strip() for x in str(r.required_fields).split(',') if x.strip()]
   if require_required_fields and required and checkable:missing=[x for x in required if x not in present];complete=complete and not missing
  if bool(r.required):status='complete_required' if has and complete else ('incomplete_required' if has else 'missing_required')
  else:status='complete_optional' if has and complete else ('incomplete_optional' if has else 'missing_optional')
  rows.append({**r.to_dict(),'has_evidence':has,'evidence_type':typ,'evidence_rows':n,'evidence_complete':complete,'missing_fields':','.join(missing),'present_fields':','.join(present),'audit_status':status,'audit_pass':status in {'complete_required','complete_optional','not_applicable_optional'}})
 item=pd.DataFrame(rows);return {'checklist':checklist,'item_results':item,'summary':summarize_gazepoint_preregistration_readiness(item),'parameters':{'evidence_names':list(evidence),'require_required_fields':require_required_fields}}

def summarize_gazepoint_preregistration_readiness(audit,by=None):
 item=audit['item_results'] if isinstance(audit,dict) and 'item_results' in audit else audit
 if not isinstance(item,pd.DataFrame) or not {'required','audit_status','audit_pass'}<=set(item):raise ValueError('`audit` is missing required columns.')
 if by is not None and (not isinstance(by,str) or by not in item):raise ValueError('`by` contains columns not found in `audit`.')
 pieces=[('all',item)] if by is None else list(item.groupby(by,sort=True,dropna=False));rows=[]
 for key,p in pieces:
  required=p.required.fillna(False).astype(bool);passed=p.audit_pass.fillna(False).astype(bool);nr=int(required.sum());nc=int((required&passed).sum());score=nc/nr if nr else np.nan
  label='not_applicable' if not np.isfinite(score) else ('complete' if score==1 else ('partly_complete' if score>0 else 'not_ready'))
  g={'summary_id':'all'} if by is None else {by:key};st=p.audit_status.astype(str)
  rows.append({**g,'n_items':len(p),'n_required':nr,'n_optional':int((~required).sum()),'n_required_complete':nc,'n_optional_complete':int(((~required)&passed).sum()),'n_missing_required':int((st=='missing_required').sum()),'n_incomplete_required':int((st=='incomplete_required').sum()),'n_missing_optional':int((st=='missing_optional').sum()),'n_incomplete_optional':int((st=='incomplete_optional').sum()),'readiness_score':score,'readiness_label':label,'incomplete_required_items':','.join(p.loc[required&~passed,'item_id'].astype(str)) if 'item_id' in p else ''})
 return pd.DataFrame(rows)

def gazepoint_interoperability_manifest(include_support=True):
 if not isinstance(include_support,bool):raise ValueError('`include_support` must be TRUE or FALSE.')
 rows=[('eyetrackingR','R','eyetrackingR','r_package',None,'current-installed','r-eye-bridges','prepare_gazepoint_eyetrackingr_input',True),('PupillometryR','R','PupillometryR','r_package',None,'current-installed','r-eye-bridges','prepare_gazepoint_pupillometryr_input',True),('gazeR','R','gazer','r_package',None,'current-installed','r-eye-bridges','prepare_gazepoint_gazer_input',True),('MNE-Python','Python','mne','python_module','1.11.0','floor-and-current','mne-lsl','prepare_gazepoint_mne_events;prepare_gazepoint_mne_input;write_gazepoint_mne_fif',True),('pylsl','Python','pylsl','python_module','1.16.2','floor-and-current','mne-lsl','sync_gazepoint_signals_via_lsl;estimate_gazepoint_lsl_clock_offsets',True),('BioSPPy','Python','biosppy','python_module','2.1.0','floor-and-current','python-physiology','prepare_gazepoint_biosppy_input;run_gazepoint_biosppy_eda;run_gazepoint_biosppy_ppg',True),('HeartPy','Python','heartpy','python_module','1.2.7','floor-and-current','python-physiology','prepare_gazepoint_heartpy_input;run_gazepoint_heartpy_crosscheck',True),('pyHRV','Python','pyhrv','python_module','0.4.1','floor-and-current','python-physiology','prepare_gazepoint_pyhrv_input;run_gazepoint_pyhrv_style',True),('BIDS','Standard','BIDS','standard','1.11.1','specification','bids-export','export_gazepoint_to_bids;prepare_gazepoint_bids_eye;prepare_gazepoint_bids_physio;check_gazepoint_bids',False)]
 if include_support:rows += [('NumPy','Python','numpy','python_module','1.26.4','floor-and-current','python-support','',True),('pandas','Python','pandas','python_module','2.2.3','floor-and-current','python-support','',True)]
 return pd.DataFrame(rows,columns=['target','ecosystem','dependency','dependency_type','minimum_tested_version','version_policy','test_group','bridge_functions','optional'])

def _vtuple(v):
 try:return tuple(int(x) for x in str(v).split('.')[:3])
 except:return None

def audit_gazepoint_interoperability_versions(manifest=None,include_python=True,strict=False):
 if not isinstance(include_python,bool) or not isinstance(strict,bool):raise ValueError('flags must be TRUE or FALSE.')
 m=gazepoint_interoperability_manifest() if manifest is None else manifest.copy();required={'target','ecosystem','dependency','dependency_type','minimum_tested_version','version_policy','test_group','bridge_functions','optional'}
 if not isinstance(m,pd.DataFrame) or not required<=set(m):raise ValueError('`manifest` has an invalid contract.')
 from . import R_EXPORTS
 now=datetime.now(timezone.utc).isoformat();rows=[]
 for _,r in m.iterrows():
  bridges=[x.strip() for x in str(r.bridge_functions or '').split(';') if x.strip()];missing=[x for x in bridges if x not in R_EXPORTS];typ=r.dependency_type;installed=None;runtime=platform.python_version() if typ=='python_module' else None
  if typ=='standard':status='declared';installed=r.minimum_tested_version
  elif typ=='python_module':
   if not include_python:status='not_checked'
   else:
    try:installed=importlib.metadata.version(r.dependency);status='available'
    except importlib.metadata.PackageNotFoundError:status='missing_dependency'
  elif typ=='r_package':status='not_checked'
  else:raise ValueError('Unsupported dependency type.')
  minimum=r.minimum_tested_version
  if status=='available' and minimum and _vtuple(installed) and _vtuple(minimum) and _vtuple(installed)<_vtuple(minimum):status='below_minimum'
  if missing:status='missing_bridge'
  optional=bool(r.optional);pass_=status not in {'missing_bridge','below_minimum','version_unreadable'}
  if not optional and status in {'missing_dependency','runtime_unavailable','not_checked'}:pass_=False
  review=status in {'available_unpinned','missing_dependency','runtime_unavailable','not_checked'}
  rows.append({**r.to_dict(),'installed_version':installed,'runtime_version':runtime,'operating_system':platform.platform(),'missing_bridge_functions':';'.join(missing),'status':status,'pass':pass_,'needs_review':review,'message':f'{r.target}: {status}','timestamp_utc':now})
 res=pd.DataFrame(rows);summary=pd.DataFrame([{'n_targets':len(res),'n_pass':int(res['pass'].sum()),'n_fail':int((~res['pass']).sum()),'n_review':int(res.needs_review.sum()),'n_available':int(res.status.isin(['available','available_unpinned','declared']).sum()),'n_missing_optional':int((res.optional.astype(bool)&(res.status=='missing_dependency')).sum()),'overall_pass':bool(res['pass'].all())}]);session=pd.DataFrame([{'timestamp_utc':now,'gpbiometricspy_version':'0.1.0.dev0','python_version':platform.python_version(),'platform':platform.platform(),'operating_system':platform.system()}]);out={'results':res,'summary':summary,'session':session,'manifest':m.copy()}
 if strict and not summary.iloc[0].overall_pass:raise RuntimeError('Interoperability audit failed for: '+', '.join(res.loc[~res['pass'],'target']))
 return out

def write_gazepoint_interoperability_audit(x,output_dir,prefix='gpbiometrics-interoperability',overwrite=False):
 if not isinstance(x,dict) or not {'results','summary','session','manifest'}<=set(x):raise TypeError('`x` must be returned by the interoperability audit.')
 if not isinstance(prefix,str) or not prefix or '/' in prefix or '\\' in prefix:raise ValueError('`prefix` must be one non-empty filename prefix.')
 out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);files={k:out/f'{prefix}-{k}.csv' for k in ['results','summary','session','manifest']}
 if not overwrite and any(f.exists() for f in files.values()):raise FileExistsError('Refusing to overwrite existing interoperability audit files.')
 for k,f in files.items():x[k].to_csv(f,index=False)
 return files
