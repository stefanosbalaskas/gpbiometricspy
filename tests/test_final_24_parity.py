from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import gpbiometricspy as gp


def test_aoi_assignment_rectangle_polygon_and_overlap():
    gaze=pd.DataFrame({'gaze_x':[.1,.5,.9,np.nan],'gaze_y':[.5,.5,.5,.5]})
    aois=pd.DataFrame({'aoi':['left','right'],'xmin':[0,.6],'xmax':[.4,1],'ymin':[0,0],'ymax':[1,1]})
    out=gp.assign_gazepoint_aoi(gaze,aois,x_col='gaze_x',y_col='gaze_y')
    assert out.attrs['class'][0]=='gazepoint_aoi_assignment'
    assert out['AOI'].tolist()[:3]==['left',np.nan,'right'] or (out.AOI.iloc[0]=='left' and pd.isna(out.AOI.iloc[1]) and out.AOI.iloc[2]=='right')
    assert out.aoi_match_count.tolist()==[1,0,1,0]
    assert out.aoi_assignment_status.tolist()==['matched','unmatched','matched','invalid_coordinate']
    log=out.attrs['aoi_assignment_log'];assert log['overview'].iloc[0].n_assigned==2

    overlap=pd.DataFrame({'aoi':['large','small'],'xmin':[0,.25],'xmax':[1,.75],'ymin':[0,.25],'ymax':[1,.75],'priority':[2,1]})
    p=gp.assign_gazepoint_aoi(pd.DataFrame({'gaze_x':[.5],'gaze_y':[.5]}),overlap,priority_col='priority',overlap='priority')
    assert p.AOI.iloc[0]=='small' and bool(p.aoi_ambiguous.iloc[0])
    all_=gp.assign_gazepoint_aoi(pd.DataFrame({'gaze_x':[.5],'gaze_y':[.5]}),overlap,overlap='all')
    assert all_.AOI.iloc[0]=='large|small'
    with pytest.raises(ValueError,match='Multiple AOIs'):
        gp.assign_gazepoint_aoi(pd.DataFrame({'gaze_x':[.5],'gaze_y':[.5]}),overlap,overlap='error')

    poly=pd.DataFrame({'aoi_id':['s']*4,'aoi':['square']*4,'vertex_x':[0,1,1,0],'vertex_y':[0,0,1,1]})
    pin=gp.assign_gazepoint_aoi(pd.DataFrame({'mean_x':[.5,1.5,0],'mean_y':[.5,.5,.5]}),poly,format='polygon',aoi_id_col='aoi_id',boundary='inside')
    assert pin.AOI.iloc[0]=='square' and pd.isna(pin.AOI.iloc[1]) and pin.AOI.iloc[2]=='square'
    pout=gp.assign_gazepoint_aoi(pd.DataFrame({'mean_x':[0],'mean_y':[.5]}),poly,format='polygon',aoi_id_col='aoi_id',boundary='outside')
    assert pd.isna(pout.AOI.iloc[0])


def test_bids_layout_prereg_and_bids_export(tmp_path):
    missing=gp.check_gazepoint_bids(tmp_path/'missing')
    assert (missing['checks'].check=='root_directory').any() and not bool(missing['summary'].iloc[0].layout_ready)
    root=tmp_path/'bids';(root/'sub-001'/'gazepoint').mkdir(parents=True)
    (root/'dataset_description.json').write_text('{"Name":"Synthetic"}')
    (root/'participants.tsv').write_text('participant_id\nsub-001\n')
    pd.DataFrame({'time':[1,2,3],'pupil':[2.1,2.2,2.3]}).to_csv(root/'sub-001'/'gazepoint'/'sub-001_task-demo_all_gaze.csv',index=False)
    audit=gp.check_gazepoint_bids(root);assert audit['summary'].iloc[0].n_fail==0
    txt=gp.create_gazepoint_preregistration_template('Test study','within_participant_z','kleckner_style')
    assert 'Test study' in txt and 'z =' in txt and 'Kleckner-style' in txt and ('will not' in txt or 'does not' in txt)

    gaze=pd.DataFrame({'TIME':[0,.1,.2,.3],'BPOGX':[.4,.5,.6,.5],'BPOGY':[.5,.4,.5,.6]})
    preview=gp.export_gazepoint_to_bids(gaze,tmp_path/'out','01','viewing',dataset_name='Viewing',dry_run=True,screen_distance_m=.6,screen_origin=['top','left'],screen_resolution_px=[1920,1080],screen_size_m=[.53,.3])
    assert preview['class'][0]=='gazepoint_bids_export' and not (tmp_path/'out').exists() and preview['audit']['ready_to_write']
    assert list(preview['data'].columns)==['timestamp','x_coordinate','y_coordinate']
    assert any(str(p).endswith('sub-01_task-viewing_recording-eye1_physio.tsv.gz') for p in preview['files'].path)

    gaze['PUPIL']=[3,3.1,3.2,3.1]
    written=gp.export_gazepoint_to_bids(gaze,tmp_path/'out2','01','viewing',dataset_name='Viewing',pupil_units='mm')
    assert all(Path(p).exists() for p in written['files'].path)
    side=json.loads(Path(written['files'].loc[written['files'].role=='physio_json','path'].iloc[0]).read_text())
    assert side['Columns']==['timestamp','x_coordinate','y_coordinate','pupil_size'] and side['PhysioType']=='eyetrack'


def test_trial_regressors_gaze_events_and_saccades():
    dat=pd.DataFrame({'time_s':np.arange(0,11),'GSR':np.linspace(0,1,11),'PPG':np.linspace(10,20,11)})
    design=pd.DataFrame({'trial':['T1','T2'],'onset':[2,7],'condition':['A','B']})
    out=gp.create_gazepoint_trial_regressors(dat,design,pre=1,post=2,event_time_col='onset',event_id_col='trial')
    assert len(out)==2 and {'trial_id','event_time','GSR_mean','PPG_mean','n_samples'}.issubset(out.columns)
    vec=gp.create_gazepoint_trial_regressors(pd.DataFrame({'time_s':range(11),'signal':range(11)}),[2,5],pre=0,post=1,signal_cols='signal')
    assert len(vec)==2 and 'signal_mean' in vec

    gaze=pd.DataFrame({'time_s':np.arange(0,1,.1),'gaze_x':[0,.01,.02,.03,1,1.01,1.02,1.03,1.04,1.05],'gaze_y':0})
    ev=gp.detect_gazepoint_fixations(gaze,time_col='time_s',x_col='gaze_x',y_col='gaze_y',velocity_threshold=2,min_fixation_duration_ms=100,min_saccade_duration_ms=50)
    assert ev['samples'].gaze_class.tolist()==['fixation','fixation','fixation','saccade','saccade','fixation','fixation','fixation','fixation','fixation']
    assert len(ev['fixations'])==2 and len(ev['saccades'])==1
    sac=ev['saccades'].iloc[0];assert sac.start_time==pytest.approx(.3) and sac.end_time==pytest.approx(.4) and sac.amplitude==pytest.approx(.97) and sac.peak_velocity==pytest.approx(9.7)
    s=gp.detect_gazepoint_saccades(gaze,time_col='time_s',x_col='gaze_x',y_col='gaze_y',velocity_threshold=2,min_fixation_duration_ms=100,min_saccade_duration_ms=50)
    assert len(s)==1 and s.attrs['class'][0]=='gazepoint_detected_saccades'


def test_adapters_cover_eyetrackingr_gazer_and_pupillometryr():
    data=pd.DataFrame({'participant':['P01']*5,'trial':['T01']*5,'time_s':[0,.1,.2,.3,.4],'gaze_x':[.2,.5,.8,np.nan,.4],'gaze_y':[.5,.5,.5,np.nan,.6],'AOI':['left','center','right',None,'outside']})
    e=gp.prepare_gazepoint_eyetrackingr_input(data)
    assert e['class'][0]=='gazepoint_eyetrackingr_input' and list(e['data'].columns[:4])==['ParticipantName','Trial','Time_ms','TrackLoss']
    assert e['data'].Time_ms.tolist()==[0,100,200,300,400] and bool(e['data'].TrackLoss.iloc[3]) and bool(e['row_audit'].non_aoi_look.iloc[4])

    gdat=pd.DataFrame({'participant':['P01']*4,'trial':['T01']*4,'time_s':[0,.1,.2,.3],'gaze_x':[.2,.4,.6,np.nan],'gaze_y':[.5,.5,.5,np.nan],'pupil':[3,3.1,3.2,np.nan]})
    g=gp.prepare_gazepoint_gazer_input(gdat)
    assert g['class'][0]=='gazepoint_gazer_input' and list(g['data'].columns[:6])==['subject','trial','time','x','y','pupil']
    assert g['data'].time.tolist()==[0,100,200,300] and g['row_audit'].finite_gaze_pair_count.tolist()==[1,1,1,0]

    pdat=pd.DataFrame({'participant':['P01']*4,'trial':['T01']*4,'condition':['target']*4,'time_s':[0,.1,.2,.3],'pupil_left':[3.1,3.2,np.nan,3.4],'pupil_right':[3,3.1,np.nan,3.3]})
    p=gp.prepare_gazepoint_pupillometryr_input(pdat)
    assert p['class'][0]=='gazepoint_pupillometryr_input' and list(p['data'].columns[:4])==['Subject','Trial','Time','Condition']
    assert {'Pupil_Left','Pupil_Right','Pupil_Mean'}.issubset(p['data'].columns) and p['data'].Pupil_Mean.iloc[0]==pytest.approx(3.05) and pd.isna(p['data'].Pupil_Mean.iloc[2])


def test_svm_autoencoder_and_point_process_bridges():
    dat=pd.DataFrame({'participant':'p1','time':np.arange(20),'GSR_US':np.r_[np.ones(10),np.ones(10)*10]})
    feat=gp.prepare_gazepoint_artifact_svm_features(dat,eda_col='GSR_US',time_col='time',group_cols='participant',segment_seconds=5,sampling_rate=1)
    assert feat.attrs['class'][0]=='gazepoint_artifact_svm_features' and 'detail_energy' in feat
    flags=gp.flag_gazepoint_artifacts_svm(feat,model=lambda newdata:(newdata.mean_signal>5).astype(float))
    assert flags.attrs['class'][0]=='gazepoint_artifact_svm_flags' and flags.artifact_svm.fillna(False).any()
    no=gp.flag_gazepoint_artifacts_svm(dat,eda_col='GSR_US',time_col='time',segment_seconds=5,sampling_rate=1)
    assert no.attrs['svm_artifact_overview'].iloc[0].status=='svm_features_prepared_no_model_supplied'

    rng=np.random.default_rng(1);d=pd.DataFrame({'participant':'p1','time':np.arange(32),'GSR_US':np.sin(np.linspace(0,2*np.pi,32))+rng.normal(0,.1,32),'HRP':np.sin(np.linspace(0,4*np.pi,32))+rng.normal(0,.1,32)})
    ae=gp.denoise_gazepoint_eda_autoencoder(d,group_cols='participant',model=lambda x:x*.5,window_samples=16)
    pp=gp.denoise_gazepoint_ppg_autoencoder(d,group_cols='participant',model=lambda x:x*.5,window_samples=16)
    assert 'GSR_US_autoencoder_denoised' in ae and 'HRP_autoencoder_denoised' in pp and ae.attrs['autoencoder_denoising_overview'].iloc[0].status=='autoencoder_reconstruction_complete'

    time=np.arange(0,60.5,.5);events=np.zeros(len(time),int);events[np.isin(time,[10,20,35,50])]=1
    eda=gp.model_gazepoint_eda_point_process(pd.DataFrame({'participant':'p1','time':time,'GSR_US':1+rng.normal(0,.005,len(time)),'event':events}),eda_col='GSR_US',time_col='time',group_cols='participant',event_indicator_col='event')
    assert len(eda['event_table'])==4 and 'inverse_gaussian_mu' in eda['process_summary']
    hr=gp.model_gazepoint_hr_point_process(pd.DataFrame({'participant':'p1','IBI':.8+rng.normal(0,.02,30)}),group_cols='participant')
    assert len(hr['beat_table'])>0 and 'inverse_gaussian_lambda' in hr['process_summary']


def test_pipeline_preprocess_quality_and_shiny_guardrails(tmp_path):
    x=pd.DataFrame({'participant_id':['P01','P01','P02','P02'],'session':['S1','S1','S1','S2'],'missing_rate':[.1,.2,.05,.4],'quality_index':[.9,.8,.95,.5],'qc_status':['accept','accept','accept','review'],'failed_rules':['','','','high_missingness'],'excluded':[False,False,False,True],'audit_notes':['','','','Sparse signal']})
    d=gp.pipeline_comparison_dashboard(x)
    assert d['class'][0]=='gazepoint_pipeline_comparison_dashboard' and d['overall'].iloc[0].n_groups==3 and d['overall'].iloc[0].n_issue_groups==1 and len(d['issues'])==1

    pre=gp.preprocess_gazepoint_all(pd.DataFrame({'time_s':range(5),'GSR':[1,np.nan,3,4,5]}),clean_pupil=False,filter_gaze=False,verbose=False)
    assert not pre.GSR.isna().any() and 'GSR_was_imputed' in pre and 'impute_missing' in set(pre.attrs['preprocessing_log'].step)
    q=gp.report_gazepoint_data_quality(pd.DataFrame({'time_s':range(5),'GSR':[1,np.nan,3,4,100],'label':list('abcde')}),output_dir=tmp_path/'quality',formats=['html','csv','pdf'])
    assert Path(q['paths']['html']).exists() and Path(q['paths']['missingness_csv']).exists() and Path(q['paths']['pdf']).stat().st_size>0
    with pytest.raises(RuntimeError,match='shiny'):
        gp.run_gpbiometrics_shiny()
    with pytest.raises(RuntimeError,match='shiny'):
        gp.run_gpbiometrics_shiny_annotator()


def test_smoke_privacy_writer_and_runner(tmp_path):
    safe={'results':pd.DataFrame({'dataset_id':['smoke_001'],'smoke_status':['pass']}),'conditions':pd.DataFrame(columns=['dataset_id','stage','condition_type','condition_class','message']),'session':pd.DataFrame({'python_version':['3.x']}),'settings':pd.DataFrame({'private_data_retained':[False]})}
    aud=gp.audit_gazepoint_smoke_privacy(safe);assert (aud.status=='pass').all()
    unsafe={**safe,'results':safe['results'].assign(participant_id='P001')};ua=gp.audit_gazepoint_smoke_privacy(unsafe);assert ua.loc[ua.check=='no_forbidden_columns','status'].iloc[0]=='fail'
    files=gp.write_gazepoint_real_data_smoke(safe,tmp_path/'smoke');assert len(files)==4 and all(Path(p).exists() for p in files.values())
    with pytest.raises(FileExistsError,match='Refusing to overwrite'):gp.write_gazepoint_real_data_smoke(safe,tmp_path/'smoke')

    root=tmp_path/'datasets';(root/'one').mkdir(parents=True);pd.DataFrame({'x':[1]}).to_csv(root/'one'/'a.csv',index=False)
    wf=lambda path,**kw:{'path':path}; sm=lambda w:{'ok':True}; dg=lambda w,**kw:{'ok':True}
    r=gp.run_gazepoint_real_data_smoke(root,workflow_runner=wf,summary_runner=sm,diagnostic_runner=dg)
    assert len(r['results'])==1 and r['results'].iloc[0].smoke_status=='pass'
