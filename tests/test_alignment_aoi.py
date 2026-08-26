import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_align_linear_and_offset():
    ref=pd.DataFrame({'time_s':np.arange(11.),'GSR':np.arange(11.)})
    tar=pd.DataFrame({'time_s':.2+1.01*np.arange(11.),'PPG':np.arange(11.)})
    re=pd.DataFrame({'event_id':['A','B','C'],'event_time':[1,5,9]})
    te=pd.DataFrame({'event_id':['A','B','C'],'event_time':.2+1.01*np.array([1,5,9])})
    out=gp.align_gazepoint_streams_by_events(ref,tar,re,te,event_id_col='event_id')
    d=out['diagnostics'].iloc[0]
    assert d.slope_target_per_reference==pytest.approx(1.01,abs=1e-8)
    assert d.intercept_s==pytest.approx(.2,abs=1e-8)
    assert 'target_time_aligned_s' in out['target_aligned']
    off=gp.align_gazepoint_streams_by_events(pd.DataFrame({'time_s':np.arange(6.)}),pd.DataFrame({'time_s':.5+np.arange(6.)}),[1],[1.5])
    assert off['diagnostics'].iloc[0].method=='offset' and off['diagnostics'].iloc[0].intercept_s==pytest.approx(.5)


def test_aoi_timecourse_labels_and_rectangles():
    dat=pd.DataFrame({'participant':'P01','trial':'T1','time_s':np.arange(0,1,.1),'AOI':['left','left','center','center','left','right','right','right','center','center']})
    out=gp.build_gazepoint_aoi_timecourse(dat,group_cols=['participant','trial'],bin_width_s=.5)
    assert {'left','center','right'}.issubset(set(out.AOI)) and {'bin_start_s','aoi_prop'}.issubset(out.columns) and (out.aoi_prop>0).any()
    gaze=pd.DataFrame({'time_s':np.arange(0,.5,.1),'gaze_x':[.1,.2,.8,.9,.5],'gaze_y':[.5]*5})
    defs=pd.DataFrame({'AOI':['left','right'],'xmin':[0,.7],'xmax':[.3,1],'ymin':[0,0],'ymax':[1,1]})
    r=gp.build_gazepoint_aoi_timecourse(gaze,aoi_definitions=defs,bin_width_s=.5)
    assert {'left','right'}.issubset(set(r.AOI))


def test_eventlocked_dataframe_and_streams():
    t=np.arange(0,5.0001,.1)
    dat=pd.DataFrame({'time_s':t,'GSR':1+np.exp(-((t-2)**2)/.1),'pupil_left':3+.2*np.exp(-((t-2.2)**2)/.2)})
    ev=pd.DataFrame({'event_id':['E1'],'event_time':[2]})
    out=gp.summarize_gazepoint_eventlocked_multimodal(dat,ev,signal_cols=['GSR','pupil_left'],pre_s=1,post_s=1,summary_window_s=(0,1))
    assert out['summary'].signal.nunique()==2 and (out['summary'].n_samples>0).all() and len(out['samples'])>0
    t2=np.arange(0,4.0001,.1); streams={'physiology':pd.DataFrame({'time_s':t2,'GSR':np.sin(t2)}),'eye':pd.DataFrame({'time_s':t2,'pupil_left':3+np.cos(t2)/10})}
    ev2=pd.DataFrame({'event_id':['E1','E2'],'event_time':[1,3]})
    o2=gp.summarize_gazepoint_eventlocked_multimodal(streams,ev2,signal_cols={'physiology':'GSR','eye':'pupil_left'},pre_s=.5,post_s=.5)
    assert {'physiology','eye'}.issubset(set(o2['summary'].modality)) and o2['summary'].event_id.nunique()==2


def test_quality_dashboard_exports(tmp_path):
    audit={'dimensions':{'n_rows':11,'n_cols':3},'warnings':[], 'duplicate_rows':{'n_duplicate_rows':0}, 'modalities':pd.DataFrame({'modality':['time','eda','ppg'],'present':[True]*3})}
    missing=pd.DataFrame({'signal':['GSR','PPG'],'missing_prop':[2/11,0.]})
    dash=gp.create_gazepoint_quality_dashboard(audit=audit,missingness=missing,output_dir=tmp_path)
    assert bool(dash['overview'].iloc[0].has_audit)
    assert (tmp_path/'quality_dashboard_overview.csv').exists() and (tmp_path/'quality_dashboard_missingness.csv').exists()
