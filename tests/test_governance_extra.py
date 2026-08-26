from pathlib import Path
import pandas as pd, numpy as np, pytest
import gpbiometricspy as gp

def test_prereg_checklist_audit_summary():
 c=gp.create_gazepoint_preregistration_checklist('study-001',True);assert len(c)==14 and c.required.sum()==10 and 'analysis_manifest' in set(c.item_id)
 req=gp.create_gazepoint_preregistration_checklist('study-002',False);assert len(req)==10 and req.required.all()
 custom=gp.create_gazepoint_preregistration_checklist('x',False,pd.DataFrame([{'domain':'device_sync','item_id':'ttl_sync_plan','item':'TTL plan','required':True,'evidence_key':'sync','required_fields':'ttl_column,rule'}]));assert 'ttl_sync_plan' in set(custom.item_id)
 evidence={'design':pd.DataFrame({'condition':['A'],'participant':['P1'],'trial':[1]}),'sampling':pd.DataFrame({'sample_size':[40],'inclusion_criteria':['valid']}),'outcomes':pd.DataFrame({'outcome':['eda'],'role':['primary']})}
 a=gp.audit_gazepoint_preregistration_consistency(req,evidence);assert len(a['item_results'])==10 and a['item_results'].query("item_id=='design_conditions'").iloc[0].audit_status=='complete_required';assert a['item_results'].query("item_id=='preprocessing_plan'").iloc[0].audit_status=='missing_required'
 s=gp.summarize_gazepoint_preregistration_readiness(pd.DataFrame({'domain':['design','design','qc'],'item_id':['a','b','c'],'required':[True,True,False],'audit_status':['complete_required','missing_required','missing_optional'],'audit_pass':[True,False,False]}),by='domain');d=s.query("domain=='design'").iloc[0];assert d.n_required==2 and d.n_required_complete==1 and d.readiness_score==.5 and d.readiness_label=='partly_complete'

def test_prereg_validation():
 with pytest.raises(ValueError):gp.create_gazepoint_preregistration_checklist(['a','b'])
 with pytest.raises(ValueError):gp.create_gazepoint_preregistration_checklist(custom_items=pd.DataFrame({'domain':['x']}))
 with pytest.raises(ValueError):gp.audit_gazepoint_preregistration_consistency(pd.DataFrame({'x':[1]}),{})
 with pytest.raises(ValueError):gp.summarize_gazepoint_preregistration_readiness(pd.DataFrame({'x':[1]}))

def test_interoperability_manifest_and_audit(tmp_path):
 m=gp.gazepoint_interoperability_manifest();assert len(m.target)==len(set(m.target));assert {'eyetrackingR','PupillometryR','gazeR','MNE-Python','pylsl','BioSPPy','HeartPy','pyHRV','BIDS','NumPy','pandas'}<=set(m.target);assert set(m.dependency_type)<={'r_package','python_module','standard'}
 a=gp.audit_gazepoint_interoperability_versions(include_python=False);assert set(a)=={'results','summary','session','manifest'};py=a['results'].dependency_type=='python_module';assert (a['results'].loc[py,'status']=='not_checked').all();assert a['results'].loc[py,'needs_review'].all()
 files=gp.write_gazepoint_interoperability_audit(a,tmp_path);assert len(files)==4 and all(Path(f).exists() for f in files.values());assert {'target','dependency','installed_version','runtime_version','operating_system','status','pass','message','timestamp_utc'}<=set(pd.read_csv(files['results']).columns)
 with pytest.raises(FileExistsError):gp.write_gazepoint_interoperability_audit(a,tmp_path)

def test_interop_missing_bridge_and_optional():
 m=pd.DataFrame([{'target':'missing-bridge','ecosystem':'Python','dependency':'numpy','dependency_type':'python_module','minimum_tested_version':'1.0.0','version_policy':'floor','test_group':'unit','bridge_functions':'definitely_missing_gpbiometrics_bridge','optional':False}]);a=gp.audit_gazepoint_interoperability_versions(m,include_python=True);assert a['results'].iloc[0].status=='missing_bridge' and not a['results'].iloc[0]['pass']
 m2=m.copy();m2.loc[0,['target','dependency','bridge_functions','optional']]=['missing-optional','definitely_missing_python_distribution','',True];b=gp.audit_gazepoint_interoperability_versions(m2,True,True);assert b['results'].iloc[0].status=='missing_dependency' and b['results'].iloc[0]['pass'] and b['results'].iloc[0].needs_review
