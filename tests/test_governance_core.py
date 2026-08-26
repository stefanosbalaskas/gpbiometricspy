from pathlib import Path
import pandas as pd, pytest
import gpbiometricspy as gp

def test_decision_log_roundtrip(tmp_path):
 l=gp.create_gazepoint_analysis_decision_log('study_001','analyst','Demo');assert len(l)==0 and l.attrs['study_id']=='study_001'
 l=gp.add_gazepoint_decision(l,'quality_control','channel','retained','GSR','passed','audit','min_active_prop',.8,timestamp='2026-01-01 10:00:00 UTC')
 l=gp.add_gazepoint_decision(l,'preprocessing','signal','baseline_corrected','pupil','baseline','baseline_correct_gazepoint_pupil','baseline_window',{'start':-1000,'end':0},timestamp='2026-01-01 10:05:00 UTC')
 assert l.decision_id.tolist()==[1,2] and l.value.tolist()==['0.8','start=-1000; end=0'] and l.attrs['analyst']=='analyst'
 s=gp.summarise_gazepoint_decision_log(l);assert s['overview'].iloc[0].n_decisions==2 and s['by_stage'].n.sum()==2
 out=gp.write_gazepoint_decision_log(l,tmp_path/'log.csv',tmp_path/'summary.txt',overwrite=True);assert len(out)==2 and all(Path(x).exists() for x in out.file)
 with pytest.raises(TypeError):gp.add_gazepoint_decision(pd.DataFrame(),'qc','trial','excluded')

def test_pipeline_audit_and_dot(tmp_path):
 p=gp.create_gazepoint_pipeline_map(pipeline_id='demo');assert len(p['nodes'])==10 and len(p['edges'])==9 and p['nodes'].iloc[0].step_id=='import' and p['nodes'].iloc[-1].step_id=='reporting'
 a=gp.audit_gazepoint_pipeline_steps(p);assert len(a['checks'])==5 and a['summary'].iloc[0].audit_pass
 st=pd.DataFrame({'step_id':['report','import','qc','extra_step'],'label':['Report','Import','QC','Extra'],'expected_order':[4,1,2,3],'required':True});c=gp.create_gazepoint_pipeline_map(st,include_default=False);au=gp.audit_gazepoint_pipeline_steps(c,['import','qc','analysis','report'],['import','qc','analysis','report'],False);assert not au['summary'].iloc[0].audit_pass and 'analysis' in set(au['checks'].query("status=='fail'").item)
 x=pd.DataFrame({'step_id':['1 import','qc-step','report'],'label':['Import "raw" files','QC','Report'],'description':['Read\nfiles','Check quality','Write report']});px=gp.create_gazepoint_pipeline_map(x,include_default=False);dot=gp.export_gazepoint_pipeline_dot(px,include_descriptions=True);assert 'digraph gazepoint_pipeline' in dot and 'n_1_import' in dot and 'qc_step' in dot and '\\"raw\\"' in dot
 f=tmp_path/'p.dot';gp.export_gazepoint_pipeline_dot(px,f,graph_name='my graph',rankdir='TB');assert f.exists() and 'digraph my_graph' in f.read_text()

def test_audit_index_summary_markdown(tmp_path):
 pa=gp.audit_gazepoint_pipeline_steps(gp.create_gazepoint_pipeline_map());manual=pd.DataFrame({'check':['metadata','qc','sidecars'],'item':['columns','missingness','json'],'status':['pass','warn','fail'],'message':['ok','review','missing'],'domain':['metadata','qc','metadata']});idx=gp.create_gazepoint_audit_index({'pipeline':pa,'manual':manual,'inventory':{'summary':pd.DataFrame([{'n_pass':3,'n_warn':1,'n_fail':0,'audit_pass':True}])}})
 assert len(idx)==9 and (idx.audit_id=='pipeline').sum()==5 and {'pass','warn','fail','not_checked'}<=set(idx.status)
 s=gp.summarize_gazepoint_audit_trail(idx);assert s.iloc[0].n_records==9 and s.iloc[0].n_fail>=1 and not s.iloc[0].audit_pass
 md=gp.export_gazepoint_audit_trail_markdown(idx,title='Demo audit trail',max_details=2);assert '# Demo audit trail' in md and '## Details' in md and 'truncated to 2 rows' in md

def test_dataset_inventory_audit_sidecar(tmp_path):
 root=tmp_path/'ds';(root/'sub-P01').mkdir(parents=True);(root/'sub-P02').mkdir();(root/'metadata').mkdir();pd.DataFrame({'time':[1,2,3]}).to_csv(root/'sub-P01/P01_all_gaze.csv',index=False);(root/'sub-P01/P01_all_gaze.json').write_text('{}');pd.DataFrame({'fixation':[1,2]}).to_csv(root/'sub-P01/P01_fixations.csv',index=False);(root/'sub-P02/P02_all_gaze.csv').touch();(root/'sub-P02/notes.tmp').write_text('bad')
 inv=gp.summarize_gazepoint_export_inventory(root);assert len(inv)==5 and inv.query("file_name=='P01_all_gaze.csv'").iloc[0].has_sidecar and inv.query("file_name=='P02_all_gaze.csv'").iloc[0].is_empty
 a=gp.audit_gazepoint_dataset_structure(root,expected_dirs=['sub-P01','sub-P02','metadata','missing_dir'],expected_files=['sub-P01/P01_all_gaze.csv','metadata/dataset_description.json'],expected_patterns={'all_gaze':'all_gaze','fixation':'fixation','summary':'summary'},allowed_extensions=['csv','json'],require_sidecars=True);assert a['summary'].iloc[0].n_fail==4 and a['summary'].iloc[0].n_warn==4
 sc=gp.create_gazepoint_sidecar_template('demo','all_gaze',True,pd.DataFrame([{'field':'calibration_notes','description':'notes','required':False,'value':'','notes':''}]));assert (sc.required).sum()==9 and 'calibration_notes' in set(sc.field)
