from pathlib import Path
import numpy as np, pandas as pd, pytest
import matplotlib.pyplot as plt
import gpbiometricspy as gp

def pkg(tmp_path,complete=True):
 p=tmp_path/'pkg';(p/'R').mkdir(parents=True);(p/'man').mkdir();(p/'tests/testthat').mkdir(parents=True);(p/'docs/reference').mkdir(parents=True);(p/'docs/articles').mkdir(parents=True)
 (p/'DESCRIPTION').write_text('Package: demoPkg\nTitle: Demo Package\nVersion: 0.0.1\nDescription: Demo\nLicense: MIT\n');(p/'NAMESPACE').write_text('export(foo)\nexport(bar)\n');(p/'R/functions.R').write_text('foo <- function() 1\nbar <- function() 2\n');(p/'_pkgdown.yml').write_text('template:\n');(p/'tests/testthat/test.R').write_text('foo();bar()');(p/'docs/articles/index.html').write_text('article');(p/'man/foo.Rd').write_text('foo');(p/'docs/reference/foo.html').write_text('foo')
 if complete:(p/'man/bar.Rd').write_text('bar');(p/'docs/reference/bar.html').write_text('bar')
 return p

def test_release_readiness_complete_and_incomplete(tmp_path):
 p=pkg(tmp_path,True);a=gp.audit_gazepoint_release_readiness(p,expected_exports=['foo','bar'],roadmap_terms=['foo','bar']);assert a['overview'].iloc[0].n_fail==0 and a['overview'].iloc[0].release_ready;assert set(a['exports'])=={'foo','bar'}
 p2=pkg(tmp_path/'x',False);b=gp.audit_gazepoint_release_readiness(p2,expected_exports=['foo','bar','missing_export'],roadmap_terms=['foo','missing_roadmap_term']);assert not b['overview'].iloc[0].release_ready and b['overview'].iloc[0].needs_review;assert ((b['checks'].check=='expected_exports')&(b['checks'].status=='fail')).any();assert ((b['checks'].check=='export_manual_pages')&(b['checks'].status=='warn')).any()
 c=gp.audit_gazepoint_release_readiness(p2,expected_exports=['foo','bar'],require_pkgdown=False);assert c['checks'].query("check=='export_reference_pages'").iloc[0].status=='not_checked'

def test_feature_coverage_and_checklist(tmp_path):
 ex=['add_gazepoint_decision','smooth_gazepoint_pupil','detect_gazepoint_pupil_blinks','plot_gazepoint_aoi_biometrics','export_gazepoint_pipeline_dot'];c=gp.summarize_gazepoint_feature_coverage(tmp_path,exports=ex);row=c.query("domain=='pupil_gaze'").iloc[0];assert row.n_exports==3 and 'add_gazepoint_decision' not in (row.examples or '')
 custom=gp.summarize_gazepoint_feature_coverage(tmp_path,exports=['alpha_import','beta_report','gamma_report'],patterns={'import':'import','report':'report'});assert custom.set_index('domain').loc['report','n_exports']==2
 empty=gp.create_gazepoint_release_checklist(include_optional=False);assert len(empty)==11 and (empty.status=='not_checked').all()
 with pytest.raises(ValueError):gp.summarize_gazepoint_feature_coverage('',exports=[])

def make_profile_folder(path):
 path.mkdir(parents=True,exist_ok=True);n=10;d=pd.DataFrame({'CNT':range(1,n+1),'TIME':np.linspace(0,.15,n),'TTL0':[0,0,1]+[0]*7,'AOI':['button']*5+['text']*5,'FPOGX':np.linspace(.1,.9,n),'FPOGY':np.linspace(.2,.8,n),'LPMM':np.linspace(2.9,3.1,n),'GSR_US':[0,0]+list(np.linspace(.1,.8,8)),'HR':[70]*n,'IBI':[850]*n,'HRP':np.sin(np.linspace(0,2*np.pi,n)),'DIAL':np.linspace(0,1,n)});d.to_csv(path/'p1.csv',index=False);d.assign(GSR_US=0,AOI='menu').to_csv(path/'p2.csv',index=False)

def test_profile_roles_compare_write_plot(tmp_path):
 a=tmp_path/'a';make_profile_folder(a);p=gp.profile_gazepoint_export_folder(a);o=p['overview'].iloc[0];assert o.n_files==2 and o.n_readable_files==2 and o.any_time_columns and o.any_ttl_columns and o.any_aoi_columns and o.any_signal_columns
 roles=set(p['columns'].role);assert {'time','ttl_event','aoi','gaze','pupil','eda_gsr','heart_rate','ibi_rr','ppg_pulse','engagement_dial'}<=roles
 b=tmp_path/'b';b.mkdir();pd.DataFrame({'CNT':range(5),'DIAL':np.linspace(0,1,5)}).to_csv(b/'b.csv',index=False);p2=gp.profile_gazepoint_export_folder(b);cmp=gp.compare_gazepoint_export_profiles(p,p2,labels=['full','dial']);assert cmp['overview'].profile.nunique()==2 and len(cmp['column_presence'])>0
 out=gp.write_gazepoint_export_profile(p,tmp_path/'out',prefix='test',overwrite=True);assert len(out)==5 and all(Path(x).exists() for x in out.file)
 for typ in ['files','roles','missingness','activity']:
  f=gp.plot_gazepoint_export_profile(p,typ);assert hasattr(f,'savefig');plt.close(f)

def test_profile_empty_and_validation(tmp_path):
 e=tmp_path/'empty';e.mkdir();p=gp.profile_gazepoint_export_folder(e);assert p['overview'].iloc[0].n_files==0 and 'no_matching_files' in set(p['warnings'].issue)
 with pytest.raises(ValueError):gp.profile_gazepoint_export_folder(tmp_path/'nope')
 with pytest.raises(ValueError):gp.profile_gazepoint_export_folder(e,max_files=0)
