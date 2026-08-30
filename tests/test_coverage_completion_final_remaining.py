from pathlib import Path
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.final_remaining as m


def test_helpers_and_aoi_context_branches(tmp_path):
    with pytest.raises(TypeError):
        m._df([])
    with pytest.raises(ValueError):
        m._time_ms([0, 1], 'samples')
    assert np.allclose(m._time_ms([0, 1], 'samples', 2), [0, 500])
    assert np.allclose(m._time_ms([0, 1], 'seconds'), [0, 1000])
    assert np.allclose(m._time_ms([0, 10], 'milliseconds'), [0, 10])
    assert np.allclose(m._time_ms([0, 1000], 'microseconds'), [0, 1])
    assert np.allclose(m._time_ms([0, 10], 'auto'), [0, 10])
    assert np.allclose(m._time_ms([0, 0], 'auto'), [0, 0])

    gaze = pd.DataFrame({'x':[0.5, 0.5], 'y':[0.5, 0.5], 'scene':['A','B']})
    aois = pd.DataFrame({
        'aoi':['wrong','right'], 'xmin':[0,0], 'xmax':[1,1], 'ymin':[0,0], 'ymax':[1,1],
        'scene':['B','A'], 'priority':[1,2]
    })
    out = m.assign_gazepoint_aoi(gaze, aois, x_col='x', y_col='y', data_match_cols='scene', aoi_match_cols='scene', priority_col='priority')
    assert out.AOI.tolist() == ['right','wrong']

    overlap = pd.DataFrame({'aoi':['A','B'], 'xmin':[0,.2], 'xmax':[1,.8], 'ymin':[0,.2], 'ymax':[1,.8]})
    out2 = m.assign_gazepoint_aoi(pd.DataFrame({'x':[.5], 'y':[.5]}), overlap, x_col='x', y_col='y', overlap='unknown')
    assert out2.AOI.iloc[0] == 'A'


def test_gaze_engine_validation_groups_validity_and_short_runs():
    with pytest.raises(ValueError):
        m._gaze_event_engine(pd.DataFrame({'time':[0,1], 'x':[0,1], 'y':[0,1]}), velocity_threshold=0)
    with pytest.raises(ValueError):
        m._gaze_event_engine(pd.DataFrame({'time':['a','b'], 'x':[0,1], 'y':[0,1]}), time_col='time', x_col='x', y_col='y', velocity_threshold=1)
    with pytest.raises(ValueError):
        m._gaze_event_engine(pd.DataFrame({'time':[0,1], 'x':[0,1], 'y':[0,1]}), time_col='time', x_col='x', y_col='y', group_cols='missing', velocity_threshold=1)
    with pytest.raises(ValueError):
        m._gaze_event_engine(pd.DataFrame({'time':[0,1], 'x':[0,1], 'y':[0,1], 'gaze_class':['x','x']}), time_col='time', x_col='x', y_col='y', velocity_threshold=1)

    df = pd.DataFrame({
        'g':['a']*4 + ['b']*4,
        'time':[0,.1,.2,.3, 0,.1,.2,.3],
        'x':[0,.01,.02,.03, 0, 2, 4, 6],
        'y':[0]*8,
        'valid':[1,0,1,1, 1,1,1,1],
    })
    out=m._gaze_event_engine(df,time_col='time',x_col='x',y_col='y',group_cols='g',valid_col='valid',velocity_threshold=5,min_fixation_duration_ms=500,min_saccade_duration_ms=500,max_gap_ms=200)
    assert len(out['summary']) == 2
    assert (out['samples'].gaze_class == 'unclassified').any()


def test_export_bids_missing_pupil_and_adapter_time_paths(tmp_path):
    gaze=pd.DataFrame({'CNT':[0,1,2], 'x':[.1,.2,.3], 'y':[.2,.3,.4]})
    out=m.export_gazepoint_to_bids(gaze,tmp_path/'b','01','t',timestamp_col='CNT',x_col='x',y_col='y',timestamp_units='samples',sampling_rate_hz=10,dry_run=True)
    assert out['settings']['timestamp_units']=='samples'

    # Adapter: CNT/sample path plus re-zero, and irregular path.
    df=pd.DataFrame({'participant':['p']*3,'trial':['t']*3,'CNT':[5,6,7],'gaze_x':[.1,.2,.3],'gaze_y':[.1,.2,.3]})
    e=m.prepare_gazepoint_eyetrackingr_input(df,sampling_rate_hz=10,rezero_time=True)
    assert e['data'].Time_ms.tolist()==[0,100,200]

    irr=pd.DataFrame({'participant':['p']*3,'trial':['t']*3,'time_s':[0,.1,.25],'gaze_x':[.1,.2,.3],'gaze_y':[.1,.2,.3]})
    with pytest.raises(ValueError,match='Irregular'):
        m.prepare_gazepoint_eyetrackingr_input(irr)


def test_adapter_extra_validity_overlap_and_masking():
    df=pd.DataFrame({
        'participant':['p']*3,'trial':['t']*3,'time_s':[0,.1,.2],
        'gaze_x':[.1,np.nan,.3],'gaze_y':[.2,.2,.2],
        'valid':[1,0,np.nan], 'TrackLoss':[False,False,True],
        'A':[True,True,False], 'B':[True,False,False], 'item':[1,2,3]
    })
    with pytest.raises(ValueError,match='More than one AOI'):
        m.prepare_gazepoint_eyetrackingr_input(df,aoi_cols=['A','B'])
    e=m.prepare_gazepoint_eyetrackingr_input(df,aoi_cols=['A','B'],allow_aoi_overlap=True,validity_col='valid',trackloss_col='TrackLoss',item_cols='item')
    assert e['row_audit'].invalid_validity.any() and e['row_audit'].missing_validity_value.any()

    gd=pd.DataFrame({
        'participant':['p']*2,'trial':['t']*2,'time_s':[0,.1],
        'gaze_x':[.1,-1], 'gaze_y':[.2,.3], 'pupil':[3,-9],
        'valid':[1,0], 'blink':[False,True], 'extra':['a','b']
    })
    g=m.prepare_gazepoint_gazer_input(gd, validity_col='valid', blink_col='blink', invalid_coordinate_values=[-1], invalid_pupil_values=[-9], mask_invalid=True, other_cols='extra')
    assert pd.isna(g['data'].loc[1,'x']) and pd.isna(g['data'].loc[1,'pupil'])
    assert g['row_audit'].invalid_validity_count.iloc[1] > 0

    pdx=pd.DataFrame({'participant':['p','p'],'trial':['t','t'],'condition':['a','b'],'time_s':[0,.1],'pupil_left':[3,3.1],'pupil_right':[3,3.1]})
    with pytest.raises(ValueError,match='Condition must be constant'):
        m.prepare_gazepoint_pupillometryr_input(pdx)


def test_preprocess_dict_clean_filter_success_and_fallback(monkeypatch):
    import gpbiometricspy.pupil_gaze as pg
    import gpbiometricspy.data_io_cleaning as dio

    calls=[]
    monkeypatch.setattr(dio,'impute_gazepoint_missing',lambda df,**kw: df.fillna(0))
    monkeypatch.setattr(pg,'clean_gazepoint_pupil_signal',lambda df,**kw: calls.append('clean') or df.assign(pupil=df['pupil'].fillna(1)))
    monkeypatch.setattr(pg,'filter_gazepoint_gaze',lambda df,**kw: calls.append('filter') or df.assign(gaze_valid=True))
    d={'a':pd.DataFrame({'pupil':[1,np.nan], 'gaze_x':[.2,.3], 'gaze_y':[.2,.3]}), 'meta':'x'}
    out=m.preprocess_gazepoint_all(d)
    assert out['meta']=='x' and {'clean','filter'} <= set(calls)

    monkeypatch.setattr(pg,'clean_gazepoint_pupil_signal',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('x')))
    monkeypatch.setattr(pg,'filter_gazepoint_gaze',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('x')))
    x=pd.DataFrame({'pupil':[1,2], 'gaze_x':[.2,2], 'gaze_y':[.2,.3]})
    o=m.preprocess_gazepoint_all(x,impute_missing=False)
    assert o.gaze_valid.tolist()==[True,False]


def test_svm_model_predict_variants_and_point_process_derivative(monkeypatch):
    feat=pd.DataFrame({'segment_id':[1,2],'mean_signal':[1.,10.],'sd_signal':[.1,.2],'min_signal':[.8,9.8],'max_signal':[1.2,10.2],'slope':[0.,0.],'detail_energy':[0.,0.],'n_samples':[5,5],'group_id':['a','a']}); feat.attrs['class']=['gazepoint_artifact_svm_features','data.frame']
    class Model:
        def predict_proba(self, X):
            return np.c_[1-np.array([.2,.9]), np.array([.2,.9])]
    out=m.flag_gazepoint_artifacts_svm(feat,model=Model(),probability_threshold=.5)
    assert out.artifact_svm.tolist()==[False,True]

    class Predict:
        def predict(self, X):
            return np.array([0,1])
    out2=m.flag_gazepoint_artifacts_svm(feat,model=Predict())
    assert out2.artifact_svm.tolist()==[False,True]

    # derivative event detection path, including MAD==0/std fallback and refractory filtering
    d=pd.DataFrame({'time':[0,1,2,3,4,5], 'GSR_US':[0,0,0,10,10,20]})
    pp=m.model_gazepoint_eda_point_process(d,eda_col='GSR_US',time_col='time',derivative_mad_multiplier=.1,min_event_distance_s=2)
    assert 'process_summary' in pp


def test_real_data_smoke_error_stop_write_and_privacy(tmp_path):
    root=tmp_path/'root'; (root/'d').mkdir(parents=True); (root/'d'/'a.csv').write_text('x\n1\n')
    def bad(**kw): raise RuntimeError('boom')
    r=m.run_gazepoint_real_data_smoke(root,workflow_runner=bad,summary_runner=lambda x:x,diagnostic_runner=lambda x,**k:x)
    assert r['results'].smoke_status.iloc[0]=='fail' and r['conditions'].condition_class.iloc[0]=='RuntimeError'
    with pytest.raises(RuntimeError,match='boom'):
        m.run_gazepoint_real_data_smoke(root,workflow_runner=bad,summary_runner=lambda x:x,diagnostic_runner=lambda x,**k:x,stop_on_error=True)
    with pytest.raises(ValueError,match='output_dir'):
        m.run_gazepoint_real_data_smoke(root,workflow_runner=lambda **k:{},summary_runner=lambda x:{},diagnostic_runner=lambda x,**k:{},write_results=True)
    ok=m.run_gazepoint_real_data_smoke(root,workflow_runner=lambda **k:{},summary_runner=lambda x:{},diagnostic_runner=lambda x,**k:{},write_results=True,output_dir=tmp_path/'out')
    assert len(ok['written_files'])==4

    unsafe={'results':pd.DataFrame({'x':['C:/Users/me/private']})}
    a=m.audit_gazepoint_smoke_privacy(unsafe,private_values='private')
    assert (a.status=='fail').any()

def test_final_remaining_last_branches(tmp_path):
    # Successful grouped fixation executes per-event group metadata construction.
    d=pd.DataFrame({'g':['a']*4,'time':[0,.1,.2,.3],'x':[0,.01,.02,.03],'y':[0,0,0,0]})
    ev=m._gaze_event_engine(d,time_col='time',x_col='x',y_col='y',group_cols='g',velocity_threshold=10,min_fixation_duration_ms=100,max_gap_ms=200)
    assert ev['fixations'].iloc[0].g == 'a'

    gaze=pd.DataFrame({'time':[0,.1], 'x':[.1,.2], 'y':[.2,.3], 'extra':['a','b']})
    with pytest.raises(ValueError,match='Additional column'):
        m.export_gazepoint_to_bids(gaze,tmp_path/'bad','1','t',timestamp_col='time',x_col='x',y_col='y',additional_cols='missing',dry_run=True)
    b=m.export_gazepoint_to_bids(gaze,tmp_path/'ok','1','t',timestamp_col='time',x_col='x',y_col='y',additional_cols='extra',dry_run=True)
    assert 'extra' in b['data']

    p=pd.DataFrame({'participant':['p']*2,'trial':['t']*2,'time_s':[0,.1], 'pupil_left':[3,3], 'pupil_right':[3,3], 'valid':[1,0], 'blink':[False,True]})
    po=m.prepare_gazepoint_pupillometryr_input(p,validity_cols='valid',blink_cols='blink',mask_invalid=True)
    assert po['row_audit'].invalid_validity_count.iloc[1] == 1
    assert po['row_audit'].blink_count.iloc[1] == 1

    feat=pd.DataFrame({'mean_signal':[1.,2.]}); feat.attrs['class']=['gazepoint_artifact_svm_features']
    with pytest.raises(TypeError,match='Unsupported model'):
        m.flag_gazepoint_artifacts_svm(feat,model=object())
    labels=m.flag_gazepoint_artifacts_svm(feat,model=lambda X:np.array(['good','artifact'],dtype=object))
    assert labels.artifact_svm.tolist()==[False,True]

    # Recursive privacy flattener: list/tuple and scalar leaves.
    a=m.audit_gazepoint_smoke_privacy({'x':[('safe',123)]})
    assert len(a)==4
