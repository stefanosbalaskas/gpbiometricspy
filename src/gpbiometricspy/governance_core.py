from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import re
import numpy as np
import pandas as pd

_LOG_COLS=['decision_id','timestamp','stage','object_type','object_id','decision','reason','function_name','parameter','value','reviewer_note']
def create_gazepoint_analysis_decision_log(study_id=None,analyst=None,description=None):
 d=pd.DataFrame({c:pd.Series(dtype='object') for c in _LOG_COLS});d.attrs.update(study_id=study_id,analyst=analyst,description=description,created_at=datetime.now(timezone.utc).isoformat(),package_version='0.1.0',gazepoint_analysis_decision_log=True);return d

def _valstr(v):
 if isinstance(v,dict):return '; '.join(f'{k}={v[k]}' for k in v)
 if isinstance(v,(list,tuple,np.ndarray)):
  return '; '.join(f'{k}={x}' for k,x in zip(['start','end'] if len(v)==2 else range(len(v)),v))
 if isinstance(v,float):return format(v,'g')
 return '' if v is None else str(v)
def add_gazepoint_decision(log,stage,object_type,decision,object_id=None,reason=None,function_name=None,parameter=None,value=None,reviewer_note=None,timestamp=None):
 if not isinstance(log,pd.DataFrame) or not log.attrs.get('gazepoint_analysis_decision_log'):raise TypeError('`log` must be created by `create_gazepoint_analysis_decision_log()`.')
 for x,n in [(stage,'stage'),(object_type,'object_type'),(decision,'decision')]:
  if not isinstance(x,str) or not x:raise ValueError(f'`{n}` must be non-empty.')
 row={'decision_id':len(log)+1,'timestamp':timestamp or datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),'stage':stage,'object_type':object_type,'object_id':object_id,'decision':decision,'reason':reason,'function_name':function_name,'parameter':parameter,'value':_valstr(value),'reviewer_note':reviewer_note}
 attrs=log.attrs.copy();out=pd.concat([log,pd.DataFrame([row])],ignore_index=True);out.attrs=attrs;return out

def summarise_gazepoint_decision_log(log):
 if not isinstance(log,pd.DataFrame) or not log.attrs.get('gazepoint_analysis_decision_log'):raise TypeError('`log` must be created by `create_gazepoint_analysis_decision_log()`.')
 def tab(c):return log[c].value_counts(dropna=False).rename_axis(c).reset_index(name='n') if len(log) else pd.DataFrame(columns=[c,'n'])
 return {'overview':pd.DataFrame([{'study_id':log.attrs.get('study_id'),'analyst':log.attrs.get('analyst'),'n_decisions':len(log)}]),'by_stage':tab('stage'),'by_object_type':tab('object_type'),'by_decision':tab('decision'),'by_function':tab('function_name')}

def write_gazepoint_decision_log(log,path,summary_path=None,overwrite=False):
 if not isinstance(path,(str,Path)) or not str(path):raise ValueError('`path` must be a non-empty path.')
 p=Path(path);files=[p]+([Path(summary_path)] if summary_path else []);exist=[x for x in files if x.exists()]
 if exist and not overwrite:raise FileExistsError('Output file(s) already exist.')
 p.parent.mkdir(parents=True,exist_ok=True);log.to_csv(p,index=False);rows=[{'component':'log','file':str(p)}]
 if summary_path:
  q=Path(summary_path);q.parent.mkdir(parents=True,exist_ok=True);s=summarise_gazepoint_decision_log(log);q.write_text(f'Gazepoint analysis decision log\n===============================\nNumber of decisions: {len(log)}\n');rows.append({'component':'summary','file':str(q)})
 return pd.DataFrame(rows)

_DEFAULT_STEPS=[('import','Import','data_io','Import Gazepoint exports'),('schema','Schema','data_io','Inspect schema'),('timing','Timing','sync','Audit timing'),('quality_control','Quality control','qc','Audit quality'),('preprocessing','Preprocessing','preprocessing','Preprocess signals'),('events','Events','events','Align events'),('features','Features','features','Extract features'),('modelling','Modelling','analysis','Fit models'),('sensitivity','Sensitivity','analysis','Run sensitivity checks'),('reporting','Reporting','reporting','Create reports')]
def create_gazepoint_pipeline_map(steps=None,edges=None,pipeline_id='gazepoint_pipeline',include_default=True):
 if not isinstance(include_default,bool):raise ValueError('`include_default` must be TRUE or FALSE.')
 if not isinstance(pipeline_id,str) or not pipeline_id:raise ValueError('`pipeline_id` must be one non-empty string.')
 if steps is None:
  if not include_default:raise ValueError('`steps` must be supplied when include_default is FALSE.')
  nodes=pd.DataFrame(_DEFAULT_STEPS,columns=['step_id','label','domain','description']);nodes['expected_order']=range(1,len(nodes)+1);nodes['required']=True;nodes['status']='planned';nodes['notes']=''
 else:
  if not isinstance(steps,pd.DataFrame) or 'step_id' not in steps:raise ValueError('`steps` must contain `step_id`.')
  nodes=steps.copy();
  if nodes.step_id.astype(str).eq('').any():raise ValueError('`step_id` must be non-empty.')
  if nodes.step_id.duplicated().any():raise ValueError('`step_id` values must be unique.')
  defaults={'label':nodes.step_id.astype(str),'domain':'other','description':'','expected_order':range(1,len(nodes)+1),'required':True,'status':'planned','notes':''}
  for c,v in defaults.items():
   if c not in nodes:nodes[c]=v
 if edges is None:
  ed=pd.DataFrame({'from':nodes.step_id.iloc[:-1].tolist(),'to':nodes.step_id.iloc[1:].tolist(),'edge_type':'required','description':'','required':True}) if len(nodes)>1 else pd.DataFrame(columns=['from','to','edge_type','description','required'])
 else:
  if not isinstance(edges,pd.DataFrame) or not {'from','to'}<=set(edges):raise ValueError('`edges` is missing required columns.')
  ed=edges.copy();unknown=set(ed['from'])|set(ed['to'])-set(nodes.step_id)
  if any(x not in set(nodes.step_id) for x in set(ed['from'])|set(ed['to'])):raise ValueError('`edges` contains unknown step ids.')
  for c,v in [('edge_type','required'),('description',''),('required',True)]:
   if c not in ed:ed[c]=v
 summary=pd.DataFrame([{'n_steps':len(nodes),'n_edges':len(ed),'n_required_steps':int(nodes.required.astype(bool).sum()),'n_optional_steps':int((~nodes.required.astype(bool)).sum())}])
 return {'pipeline_id':pipeline_id,'nodes':nodes.reset_index(drop=True),'edges':ed.reset_index(drop=True),'summary':summary,'parameters':{'custom_steps':steps is not None,'custom_edges':edges is not None,'include_default':include_default}}

def audit_gazepoint_pipeline_steps(pipeline,expected_steps=None,required_order=None,allow_extra=True):
 if isinstance(pipeline,pd.DataFrame):pipeline=create_gazepoint_pipeline_map(pipeline,include_default=False)
 if not isinstance(pipeline,dict) or 'nodes' not in pipeline:raise TypeError('`pipeline` must be a pipeline map or steps data frame.')
 if not isinstance(allow_extra,bool):raise ValueError('`allow_extra` must be TRUE or FALSE.')
 nodes=pipeline['nodes'];actual=list(nodes.step_id.astype(str));expected=actual if expected_steps is None else list(expected_steps)
 if any(not isinstance(x,str) for x in expected):raise ValueError('`expected_steps` must be character values.')
 order=expected if required_order is None else list(required_order);checks=[]
 missing=[x for x in expected if x not in actual]
 if missing:
  for x in missing:checks.append({'check':'expected_steps','item':x,'status':'fail','message':'missing','domain':'pipeline'})
 else:checks.append({'check':'expected_steps','item':'all_expected_steps','status':'pass','message':'all expected steps present','domain':'pipeline'})
 extras=[x for x in actual if x not in expected]
 if extras:
  for x in extras:checks.append({'check':'extra_steps','item':x,'status':'pass' if allow_extra else 'warn','message':'extra step','domain':'pipeline'})
 else:checks.append({'check':'extra_steps','item':'none','status':'pass','message':'no extra steps','domain':'pipeline'})
 seq=[x for x in actual if x in order];target=[x for x in order if x in actual];ok=seq==target and all(x in actual for x in order)
 checks.append({'check':'ordering','item':'required_order','status':'pass' if ok else 'warn','message':'order valid' if ok else 'ordering requires review','domain':'pipeline'})
 edge_ok=all((r['from'] in actual and r['to'] in actual) for _,r in pipeline['edges'].iterrows())
 checks.append({'check':'edges','item':'known_nodes','status':'pass' if edge_ok else 'fail','message':'edges valid' if edge_ok else 'invalid edge','domain':'pipeline'})
 unique=not nodes.step_id.duplicated().any();checks.append({'check':'step_ids','item':'unique','status':'pass' if unique else 'fail','message':'unique step ids' if unique else 'duplicate step ids','domain':'pipeline'})
 c=pd.DataFrame(checks);nf=int((c.status=='fail').sum());nw=int((c.status=='warn').sum());summary=pd.DataFrame([{'n_steps':len(nodes),'n_edges':len(pipeline['edges']),'n_fail':nf,'n_warn':nw,'audit_pass':nf==0}])
 return {'pipeline_id':pipeline.get('pipeline_id'),'checks':c,'summary':summary,'parameters':{'expected_steps':expected_steps,'required_order':required_order,'allow_extra':allow_extra}}

def export_gazepoint_pipeline_dot(pipeline,file=None,graph_name='gazepoint_pipeline',rankdir='LR',include_descriptions=False):
 if not isinstance(graph_name,str) or not graph_name:raise ValueError('`graph_name` must be non-empty.')
 if not isinstance(rankdir,str) or not rankdir:raise ValueError('`rankdir` must be non-empty.')
 if not isinstance(include_descriptions,bool):raise ValueError('`include_descriptions` must be TRUE or FALSE.')
 def ident(x):return re.sub(r'\W','_',str(x)) if re.match(r'^\d',str(x)) is None else 'n_'+re.sub(r'\W','_',str(x))
 def esc(x):return str(x).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
 graph_id=re.sub(r'\W','_',graph_name)
 lines=[f'digraph {graph_id} {{',f'  graph [rankdir="{rankdir}"];']
 for _,r in pipeline['nodes'].iterrows():
  lab=esc(r.get('label',r.step_id));desc=esc(r.get('description',''))
  if include_descriptions and desc:lab+=r'\n'+desc
  lines.append(f'  {ident(r.step_id)} [label="{lab}"];')
 for _,r in pipeline['edges'].iterrows():lines.append(f'  {ident(r["from"])} -> {ident(r["to"])};')
 lines.append('}');text='\n'.join(lines)
 if file:Path(file).write_text(text)
 return text

_STATMAP={'ok':'pass','complete':'pass','passed':'pass','pass':'pass','warning':'warn','warn':'warn','flagged':'warn','missing':'fail','error':'fail','fail':'fail','skip':'not_checked','skipped':'not_checked','not_checked':'not_checked','present':'recorded','recorded':'recorded'}
def _audit_rows(obj,audit_id,include_summary=False):
 frames=[]
 if isinstance(obj,pd.DataFrame):frames=[('data',obj)]
 elif isinstance(obj,dict):
  if isinstance(obj.get('checks'),pd.DataFrame):frames.append(('checks',obj['checks']))
  if include_summary and isinstance(obj.get('summary'),pd.DataFrame):frames.append(('summary',obj['summary']))
  elif not frames and isinstance(obj.get('summary'),pd.DataFrame):frames.append(('summary',obj['summary']))
  elif not frames:return [dict(audit_id=audit_id,object_class='dict',source_table='object',row_number=1,check='object_record',item='',status='recorded',message='',path='',domain='')]
 else:return []
 rows=[]
 for src,df in frames:
  for i,r in df.reset_index(drop=True).iterrows():
   raw=str(r.get('status','not_checked')).strip().lower();st=_STATMAP.get(raw,'other')
   rows.append({'audit_id':audit_id,'object_class':type(obj).__name__,'source_table':src,'row_number':i+1,'check':str(r.get('check','summary_record' if src=='summary' else 'record')),'item':str(r.get('item','')),'status':st,'message':str(r.get('message','')),'path':str(r.get('path','')),'domain':str(r.get('domain',''))})
 return rows

def create_gazepoint_audit_index(audits=None,audit_ids=None,include_summary_rows=False):
 cols=['audit_id','object_class','source_table','row_number','check','item','status','message','path','domain']
 if audits is None:return pd.DataFrame(columns=cols)
 if not isinstance(include_summary_rows,bool):raise ValueError('`include_summary_rows` must be TRUE or FALSE.')
 if isinstance(audits,(pd.DataFrame,dict)) and not (isinstance(audits,dict) and ('checks' in audits or 'summary' in audits)):
  items=list(audits.items()) if isinstance(audits,dict) else [('audit_1',audits)]
 elif isinstance(audits,list):items=[(f'audit_{i+1}',x) for i,x in enumerate(audits)]
 elif isinstance(audits,dict):items=[('audit_1',audits)]
 else:raise TypeError('`audits` must be an audit object, data frame, list, or NULL.')
 if audit_ids is not None:
  if len(audit_ids)!=len(items):raise ValueError('`audit_ids` must match number of audits.')
  items=list(zip(audit_ids,[x[1] for x in items]))
 rows=[]
 for aid,obj in items:rows.extend(_audit_rows(obj,str(aid),include_summary_rows))
 return pd.DataFrame(rows,columns=cols)

def summarize_gazepoint_audit_trail(audit_index,by=None):
 if not isinstance(audit_index,pd.DataFrame):raise TypeError('`audit_index` must be a data frame.')
 if by is not None and (not isinstance(by,str) or by not in audit_index):raise ValueError('`by` must name a known column.')
 def one(p,g=None):
  st=p.status if len(p) else pd.Series(dtype=str);r={'n_records':len(p),'n_pass':int((st=='pass').sum()),'n_warn':int((st=='warn').sum()),'n_fail':int((st=='fail').sum()),'n_not_checked':int((st=='not_checked').sum()),'n_recorded':int((st=='recorded').sum()),'audit_pass':not (st=='fail').any(),'needs_review':bool((st.isin(['warn','fail','not_checked'])).any())};return {**({by:g} if by else {}),**r}
 if len(audit_index)==0:return pd.DataFrame(columns=([by] if by else [])+['n_records','n_pass','n_warn','n_fail','n_not_checked','n_recorded','audit_pass','needs_review'])
 if by:return pd.DataFrame([one(p,k) for k,p in audit_index.groupby(by,dropna=False,sort=True)])
 return pd.DataFrame([one(audit_index)])

def export_gazepoint_audit_trail_markdown(audit_index,summary=None,title='Gazepoint audit trail',include_details=True,max_details=100,file=None):
 if not isinstance(summary,(pd.DataFrame,type(None))):raise TypeError('`summary` must be a data frame or NULL.')
 if not isinstance(title,str) or not title:raise ValueError('`title` must be non-empty.')
 if not isinstance(include_details,bool):raise ValueError('`include_details` must be TRUE or FALSE.')
 if max_details<0:raise ValueError('`max_details` must be non-negative.')
 summary=summarize_gazepoint_audit_trail(audit_index) if summary is None else summary
 def md(df):
  if len(df)==0:return '_No records._'
  cols=list(df.columns);lines=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
  for _,r in df.iterrows():lines.append('| '+' | '.join('' if pd.isna(r[c]) else str(r[c]) for c in cols)+' |')
  return '\n'.join(lines)
 text=f'# {title}\n\n## Summary\n\n{md(summary)}'
 if include_details:
  d=audit_index.head(max_details);text+='\n\n## Details\n\n'+md(d[['audit_id','item','status','message']] if len(d) else d)
  if len(audit_index)>max_details:text+=f'\n\n_Detail table truncated to {max_details} rows._'
 if file:Path(file).write_text(text)
 return text


def _ptype(name):
 n=name.lower()
 if 'all_gaze' in n:return 'all_gaze'
 if 'fixation' in n:return 'fixations'
 if 'biometric' in n or 'eda' in n:return 'biometrics'
 if 'event' in n:return 'events'
 if name.lower().endswith('.json'):return 'sidecar'
 return 'unknown'
def summarize_gazepoint_export_inventory(path,recursive=True):
 if not isinstance(recursive,bool):raise ValueError('`recursive` must be TRUE or FALSE.')
 paths=[path] if isinstance(path,(str,Path)) else list(path)
 if not paths:raise ValueError('`path` must not be empty.')
 files=[]
 for x in paths:
  p=Path(x)
  if not p.exists():raise ValueError('path not found')
  if p.is_dir():files.extend([f for f in (p.rglob('*') if recursive else p.iterdir()) if f.is_file()])
  else:files.append(p)
 rows=[]
 for f in sorted(set(files)):
  parent=f.parent.name;participant=parent if re.match(r'sub-',parent,re.I) else None;side=f.with_suffix('.json').exists() if f.suffix.lower()!='.json' else True
  st=f.stat();rows.append({'path':str(f.resolve()),'relative_path':str(f.name if len(paths)>1 else f.relative_to(Path(paths[0]) if Path(paths[0]).is_dir() else f.parent)),'directory':str(f.parent),'file_name':f.name,'extension':f.suffix.lower().lstrip('.'),'size_bytes':st.st_size,'modified_time':str(st.st_mtime),'is_empty':st.st_size==0,'likely_export_type':_ptype(f.name),'participant_id':participant,'has_sidecar':side})
 return pd.DataFrame(rows,columns=['path','relative_path','directory','file_name','extension','size_bytes','modified_time','is_empty','likely_export_type','participant_id','has_sidecar'])

def audit_gazepoint_dataset_structure(root,expected_dirs=None,expected_files=None,expected_patterns=None,allowed_extensions=None,require_sidecars=False):
 p=Path(root)
 if not p.exists() or not p.is_dir():raise ValueError('`root` must be an existing directory.')
 if not isinstance(require_sidecars,bool):raise ValueError('`require_sidecars` must be TRUE or FALSE.')
 for x,n in [(expected_dirs,'expected_dirs'),(expected_files,'expected_files')]:
  if x is not None and (isinstance(x,(int,float)) or any(not isinstance(v,str) for v in ([x] if isinstance(x,str) else x))):raise ValueError(f'`{n}` must be character values.')
 inv=summarize_gazepoint_export_inventory(p);rows=[]
 for d in ([expected_dirs] if isinstance(expected_dirs,str) else expected_dirs or []):rows.append({'check':'expected_dirs','item':d,'status':'pass' if (p/d).is_dir() else 'fail','message':'present' if (p/d).is_dir() else 'missing'})
 for f in ([expected_files] if isinstance(expected_files,str) else expected_files or []):rows.append({'check':'expected_files','item':f,'status':'pass' if (p/f).is_file() else 'fail','message':'present' if (p/f).is_file() else 'missing'})
 if expected_patterns:
  items=expected_patterns.items() if isinstance(expected_patterns,dict) else enumerate(expected_patterns)
  for name,pat in items:rows.append({'check':'expected_patterns','item':str(name),'status':'pass' if inv.file_name.str.contains(str(pat),case=False,regex=True).any() else 'fail','message':'pattern found' if inv.file_name.str.contains(str(pat),case=False,regex=True).any() else 'pattern missing'})
 for _,r in inv[inv.is_empty].iterrows():rows.append({'check':'empty_files','item':r.file_name,'status':'fail','message':'empty file'})
 if allowed_extensions:
  allowed={x.lower().lstrip('.') for x in allowed_extensions}
  for ext in sorted(set(inv.extension)-allowed):rows.append({'check':'unexpected_extensions','item':ext,'status':'warn','message':'unexpected extension'})
 if require_sidecars:
  for _,r in inv[(inv.extension!='json')&(~inv.has_sidecar)].iterrows():rows.append({'check':'sidecars','item':r.file_name,'status':'warn','message':'sidecar missing'})
 checks=pd.DataFrame(rows,columns=['check','item','status','message']);nf=int((checks.status=='fail').sum()) if len(checks) else 0;nw=int((checks.status=='warn').sum()) if len(checks) else 0
 return {'root':str(p.resolve()),'inventory':inv,'checks':checks,'summary':pd.DataFrame([{'n_files':len(inv),'n_pass':int((checks.status=='pass').sum()) if len(checks) else 0,'n_warn':nw,'n_fail':nf,'audit_pass':nf==0}]),'parameters':{'expected_dirs':expected_dirs,'expected_files':expected_files,'expected_patterns':expected_patterns,'allowed_extensions':allowed_extensions,'require_sidecars':require_sidecars}}

def create_gazepoint_sidecar_template(dataset_id=None,export_type=None,include_optional=True,custom_fields=None):
 if isinstance(dataset_id,(list,tuple)) or isinstance(export_type,(list,tuple)):raise ValueError('`dataset_id` and `export_type` must each be a single value.')
 if not isinstance(include_optional,bool):raise ValueError('`include_optional` must be TRUE or FALSE.')
 required=[('dataset_id','Dataset identifier'),('export_type','Gazepoint export type'),('participant_id','Participant identifier'),('session_id','Session identifier'),('sampling_rate_hz','Sampling rate'),('time_unit','Time unit'),('device','Device'),('software_version','Software version'),('created_at','Creation timestamp')]
 optional=[('condition','Condition'),('task','Task'),('screen_width_px','Screen width'),('screen_height_px','Screen height'),('notes','Notes')]
 rows=[{'field':f,'description':d,'required':True,'value':dataset_id if f=='dataset_id' else (export_type if f=='export_type' else ''),'notes':''} for f,d in required]
 if include_optional:rows += [{'field':f,'description':d,'required':False,'value':'','notes':''} for f,d in optional]
 if custom_fields is not None:
  req={'field','description','required','value','notes'}
  if not isinstance(custom_fields,pd.DataFrame) or not req<=set(custom_fields):raise ValueError('`custom_fields` is missing required columns.')
  rows += custom_fields[list(req)].to_dict('records')
 return pd.DataFrame(rows)
