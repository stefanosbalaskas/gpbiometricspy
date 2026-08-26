import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_extract_ttl_changes_initial_nonzero_groups_validity_and_empty():
    dat=pd.DataFrame({'source_participant':['User 1']*4,'MEDIA_ID':[1]*4,'CNT':[1,2,3,4],
                      'TTL0':[1007,1007,1008,1008],'TTLV':[1,1,1,1]})
    out=gp.extract_gazepoint_ttl_events(dat,group_columns=['source_participant','MEDIA_ID'])
    assert len(out)==2
    assert out.ttl_channel.tolist()==['TTL0','TTL0']
    assert out.ttl_value.tolist()==[1007,1008]
    assert out.CNT.tolist()==[1,3]
    assert out.row_index.tolist()==[1,3]
    no_initial=gp.extract_gazepoint_ttl_events(dat,include_initial=False)
    assert len(no_initial)==1 and no_initial.iloc[0].ttl_value==1008 and no_initial.iloc[0].previous_ttl_value==1007
    nz=gp.extract_gazepoint_ttl_events(pd.DataFrame({'CNT':[1,2,3,4],'TTL0':[0,1007,0,1008],'TTLV':[1]*4}),mode='nonzero')
    assert nz.CNT.tolist()==[2,4]
    grouped=pd.DataFrame({'source_participant':['U1','U1','U2','U2'],'CNT':[1,2,1,2],'TTL0':[1007,1008,1007,1008],'TTLV':[1]*4})
    gout=gp.extract_gazepoint_ttl_events(grouped,group_columns='source_participant',include_initial=False)
    assert len(gout)==2 and gout.ttl_value.tolist()==[1008,1008]
    invalid=pd.DataFrame({'CNT':[1,2,3,4],'TTL0':[1007,1008,1009,1010],'TTLV':[0,0,1,1]})
    kept=gp.extract_gazepoint_ttl_events(invalid)
    assert kept.ttl_value.tolist()==[1009,1010]
    allrows=gp.extract_gazepoint_ttl_events(invalid,require_validity=False)
    assert allrows.ttl_value.tolist()==[1007,1008,1009,1010]
    empty=gp.extract_gazepoint_ttl_events(pd.DataFrame({'source_participant':['U1','U1'],'CNT':[1,2],'TTL0':[0,0],'TTLV':[1,1]}),group_columns='source_participant',mode='nonzero')
    assert empty.empty and {'source_participant','ttl_channel'}.issubset(empty.columns)
    with pytest.raises(ValueError,match='No TTL columns'):
        gp.extract_gazepoint_ttl_events(pd.DataFrame({'CNT':[1,2],'GSR_US':[1.1,1.2]}))


def test_ttl_alignment_standard_raw_user_validity_and_sample_fallback():
    dat=pd.DataFrame({'participant':'P1','trial':1,'time_ms':np.arange(0,1000,100),
                      'ttl_marker':[0,0,1,1,0,0,1,0,0,0],'ttl_validity_flag':1,
                      'GSR_US':np.linspace(1,2,10)})
    res=gp.align_gazepoint_biometrics_to_ttl(dat,time_col='time_ms',group_cols=['participant','trial'],pre_window_ms=100,post_window_ms=200)
    assert res['overview'].iloc[0].status=='ttl_events_aligned'
    assert len(res['events'])==2
    assert res['aligned_data'].ttl_event_id.unique().tolist()==['ttl_event_1','ttl_event_2']
    assert 0 in res['aligned_data'].event_relative_sample_index.tolist()
    assert {'pre_event','event','post_event'}.issubset(set(res['aligned_data'].event_window_position))

    raw=pd.DataFrame({'subject':'S1','MEDIA_ID':'M1','time_ms':np.arange(0,1000,100),
                      'TTL0':[0,0,1,1,0,0,0,0,0,0],'TTL1':[0,0,0,0,0,0,1,0,0,0],
                      'TTLV':1,'HR':np.arange(70,80)})
    r=gp.align_gazepoint_biometrics_to_ttl(raw,time_col='time_ms',pre_window_ms=100,post_window_ms=100)
    assert len(r['events'])==2 and {'TTL0','TTL1'}.issubset(set(r['events'].event_ttl_column))
    assert r['settings']['ttl_valid_col']=='TTLV'

    user=pd.DataFrame({'participant':np.repeat(['P1','P2'],5),'trial':1,'time_ms':np.tile(np.arange(0,500,100),2),
                       'marker':[0,'start',0,0,0,0,'start',0,0,0],'GSR_US':np.linspace(1,2,10)})
    u=gp.align_gazepoint_biometrics_to_ttl(user,event_col='marker',event_value='start',time_col='time_ms',group_cols=['participant','trial'],pre_window_ms=100,post_window_ms=100)
    assert len(u['events'])==2 and sorted(u['events'].participant.unique())==['P1','P2']
    assert u['settings']['event_source']=='user_event_col'

    bad=pd.DataFrame({'time_ms':np.arange(0,500,100),'TTL0':[0,1,0,0,0],'TTLV':[1,0,1,1,1],'GSR_US':np.linspace(1,1.4,5)})
    b=gp.align_gazepoint_biometrics_to_ttl(bad,time_col='time_ms',pre_window_ms=100,post_window_ms=100)
    assert b['overview'].iloc[0].status=='no_ttl_events_detected' and b['events'].empty and b['aligned_data'].empty

    nt=pd.DataFrame({'participant':'P1','marker':[0,1,0,0,0],'HR':[70,72,73,74,75]})
    n=gp.align_gazepoint_biometrics_to_ttl(nt,event_col='marker',group_cols='participant',pre_window_samples=1,post_window_samples=1)
    assert n['aligned_data'].event_relative_sample_index.tolist()==[-1,0,1]
    assert n['aligned_data'].event_relative_time_ms.isna().all()


def test_sync_exact_join_master_and_errors():
    bio=pd.DataFrame({'USER':['U1','U1','U2'],'MEDIA_ID':[1,2,1],'CNT':[10,20,10],
                      'GSR_US':[2.0,2.2,1.5],'GSRV':[1,1,1],'HR':[75,76,80],'HRV':[1,1,1],
                      'DIAL':[.1,.2,.3],'DIALV':[1,1,1]})
    gaze=pd.DataFrame({'USER':['U1','U2'],'MEDIA_ID':[1,1],'CNT':[10,10],'BPOGX':[.5,.6],'BPOGY':[.4,.3]})
    out=gp.sync_gazepoint_biometrics_with_gaze(bio,gaze,by=['USER','MEDIA_ID','CNT'])
    assert len(out)==2 and {'GSR_US','HR','DIAL','BPOGX'}.issubset(out.columns)
    summary=out.attrs['sync_summary'].iloc[0]
    assert summary.n_gaze_rows==2 and summary.n_biometric_rows==3 and summary.n_output_rows==2

    gaze2=pd.DataFrame({'USER':['U1','U1'],'MEDIA_ID':[1,1],'CNT':[10,11],'BPOGX':[.5,.6]})
    left=gp.sync_gazepoint_biometrics_with_gaze(bio.iloc[[0]],gaze2,by=['USER','MEDIA_ID','CNT'],all_x=True)
    assert len(left)==2 and left.GSR_US.isna().sum()==1

    master=pd.DataFrame({'USER':['U1'],'MEDIA_ID':[1],'dwell_time':[1200]})
    joined=gp.join_gazepoint_biometrics_to_master(master,bio.iloc[[0]],by=['USER','MEDIA_ID'])
    assert {'dwell_time','GSR_US','HR'}.issubset(joined.columns)
    with pytest.raises(ValueError,match='biometrics'):
        gp.sync_gazepoint_biometrics_with_gaze(pd.DataFrame({'USER':['U1'],'GSR_US':[2.]}),pd.DataFrame({'USER':['U1'],'MEDIA_ID':[1]}),by=['USER','MEDIA_ID'])
    with pytest.raises(ValueError,match='gaze'):
        gp.sync_gazepoint_biometrics_with_gaze(pd.DataFrame({'USER':['U1'],'MEDIA_ID':[1],'GSR_US':[2.]}),pd.DataFrame({'USER':['U1'],'BPOGX':[.5]}),by=['USER','MEDIA_ID'])


def test_chunk_fixed_analysis_episodes_and_validation():
    dat=pd.DataFrame({'participant':np.repeat(['p1','p2'],121),'CNT':np.tile(np.arange(121,dtype=float),2),'GSR_US':np.random.default_rng(1).normal(size=242)})
    out=gp.chunk_gazepoint_biometrics(dat,time_col='CNT',group_cols='participant',chunk_seconds=60,include_partial=True)
    assert {'chunk_id','episode_id','chunk_complete'}.issubset(out.columns)
    assert len(out.attrs['chunk_summary'])>=4
    assert out.attrs['chunk_overview'].iloc[0].status=='biometric_chunks_created'
    assert out.attrs['class'][0]=='gazepoint_biometric_chunks'
    with pytest.raises(ValueError,match='positive'):
        gp.chunk_gazepoint_biometrics(dat,chunk_seconds=0)
    with pytest.raises(ValueError,match='Missing'):
        gp.chunk_gazepoint_biometrics(dat,group_cols='missing')


def test_intake_alignment_edge_paths(tmp_path):
    # CSV coercion, absent validity, explicit-column validation and mode validation.
    csv=tmp_path/'ttl.csv'
    pd.DataFrame({'CNT':[1,2],'TTL0':[1,2]}).to_csv(csv,index=False)
    no_valid=gp.extract_gazepoint_ttl_events(csv,require_validity=False)
    assert no_valid.ttl_value.tolist()==[1,2]
    assert no_valid.ttl_validity.isna().all()
    with pytest.raises(ValueError,match='mode'):
        gp.extract_gazepoint_ttl_events(pd.DataFrame({'TTL0':[1]}),mode='bad')
    with pytest.raises(ValueError,match='ttl_columns'):
        gp.extract_gazepoint_ttl_events(pd.DataFrame({'TTL0':[1]}),ttl_columns='TTL1')
    with pytest.raises(ValueError,match='group_columns'):
        gp.extract_gazepoint_ttl_events(pd.DataFrame({'TTL0':[1]}),group_columns='who')
    with pytest.raises(TypeError,match='data frame or CSV'):
        gp.extract_gazepoint_ttl_events([1,2,3])

    empty=gp.align_gazepoint_biometrics_to_ttl(pd.DataFrame(columns=['TTL0']))
    assert empty['overview'].iloc[0].status=='empty_input'
    with pytest.raises(ValueError,match='event_edge'):
        gp.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'TTL0':[1]}),event_edge='bad')
    with pytest.raises(ValueError,match='pre_window_ms'):
        gp.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'TTL0':[1]}),pre_window_ms=-1)
    with pytest.raises(ValueError,match='event_col'):
        gp.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'TTL0':[1]}),event_col='missing')
    with pytest.raises(ValueError,match='ttl_cols'):
        gp.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'TTL0':[1]}),ttl_cols=['TTL1'])
    with pytest.raises(ValueError,match='group_cols'):
        gp.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'TTL0':[1]}),group_cols=['missing'])

    with pytest.raises(TypeError,match='gaze'):
        gp.sync_gazepoint_biometrics_with_gaze(pd.DataFrame({'id':[1]}),[1],by='id')
    with pytest.raises(ValueError,match='non-empty'):
        gp.sync_gazepoint_biometrics_with_gaze(pd.DataFrame({'id':[1]}),pd.DataFrame({'id':[1]}),by=[])

    raw=pd.DataFrame({'CNT':[0.,20.,40.],'GSR_US':[1.,2.,3.]})
    partial=gp.chunk_gazepoint_biometrics(raw,chunk_seconds=60,include_partial=False)
    assert partial.chunk_id.isna().all() and not partial.chunk_complete.any()
    ungrouped=gp.chunk_gazepoint_biometrics(raw,chunk_seconds=60,include_partial=True)
    assert ungrouped.attrs['chunk_overview'].iloc[0].group_count==1
    with pytest.raises(TypeError,match='data frame'):
        gp.chunk_gazepoint_biometrics([])
    with pytest.raises(ValueError,match='not found'):
        gp.chunk_gazepoint_biometrics(raw,time_col='missing')
    with pytest.raises(TypeError,match='numeric'):
        gp.chunk_gazepoint_biometrics(pd.DataFrame({'CNT':['a','b']}))
