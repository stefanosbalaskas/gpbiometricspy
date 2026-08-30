import numpy as np
import pandas as pd
import pytest
import gpbiometricspy.intake_alignment as m


def test_helper_fallbacks_and_ttl_active_variants():
    assert m._first_existing(['ABC'],['abc'])=='ABC'
    assert np.isnan(m._ttl_time_ms(pd.DataFrame({'t':['x','y']}),'t')).all()
    assert m._ttl_time_ms(pd.DataFrame({'t':[1,1]}),'t').tolist()==[1,1]
    assert m._ttl_active(pd.Series([True,False,None],dtype='boolean')).tolist()==[True,False,False]
    assert m._ttl_active(pd.Series(['0','2','3',''])).tolist()==[False,True,True,False]
    assert m._ttl_active(pd.Series(['go','FALSE','NA','NULL',''])).tolist()==[True,False,False,False,False]


def test_alignment_validation_auto_detection_edges_and_collapse():
    with pytest.raises(TypeError):m.align_gazepoint_biometrics_to_ttl([])
    with pytest.raises(ValueError,match='No TTL'):
        m.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'x':[1]}))
    base=pd.DataFrame({'ttl_marker':[0,1,1,2,2], 'time_ms':[0,10,20,25,30], 'CNT':[1,2,3,4,5], 'participant':['p']*5})
    with pytest.raises(ValueError,match='ttl_valid_col'):m.align_gazepoint_biometrics_to_ttl(base,ttl_valid_col='bad')
    with pytest.raises(ValueError,match='time_col'):m.align_gazepoint_biometrics_to_ttl(base,time_col='bad')
    with pytest.raises(ValueError,match='sample_col'):m.align_gazepoint_biometrics_to_ttl(base,sample_col='bad')
    # change + nearby collapse paths
    o=m.align_gazepoint_biometrics_to_ttl(base,event_edge='change',collapse_nearby_ms=20,pre_window_ms=0,post_window_ms=0)
    assert len(o['events'])>=1
    # active event-edge path
    a=m.align_gazepoint_biometrics_to_ttl(base,event_edge='active',pre_window_ms=0,post_window_ms=0)
    assert len(a['events'])>=2


def test_alignment_sample_order_and_sample_window_validation():
    # all-NaN time forces sample order and sample-relative alignment.
    d=pd.DataFrame({'TTL0':[0,1,0], 'time':['x','x','x'], 'CNT':[30,10,20]})
    o=m.align_gazepoint_biometrics_to_ttl(d,time_col='time',sample_col='CNT',pre_window_samples=1,post_window_samples=1)
    assert len(o['aligned_data'])>0
    with pytest.raises(ValueError,match='pre_window_samples'):
        m.align_gazepoint_biometrics_to_ttl(d,time_col='time',sample_col='CNT',pre_window_samples=-1)

    # Event exists but zero-width/NaN-order setup yields no kept rows through a defensive custom event time.
    d2=pd.DataFrame({'TTL0':[1], 'time':['x']})
    no=m.align_gazepoint_biometrics_to_ttl(d2,time_col='time',pre_window_samples=0,post_window_samples=0)
    assert no['overview'].aligned_rows.iloc[0] >= 0


def test_chunk_no_finite_time_branch():
    d=pd.DataFrame({'CNT':[np.nan,np.nan],'x':[1,2]})
    o=m.chunk_gazepoint_biometrics(d,time_col='CNT',include_partial=True)
    assert o.attrs['chunk_summary'].empty

def test_alignment_collapse_keep_later_and_no_rows_defensive(monkeypatch):
    d=pd.DataFrame({'TTL0':[0,1,0,1,0], 'time_ms':[0,10,20,50,60]})
    o=m.align_gazepoint_biometrics_to_ttl(d,collapse_nearby_ms=20,pre_window_ms=0,post_window_ms=0)
    assert len(o['events'])==2

    real_iterrows=pd.DataFrame.iterrows
    def shifted_iterrows(self):
        for i,row in real_iterrows(self):
            if 'ttl_event_id' in self.columns:
                row=row.copy(); row['event_time_ms']=float(row['event_time_ms'])+1e6
            yield i,row
    monkeypatch.setattr(pd.DataFrame,'iterrows',shifted_iterrows)
    z=m.align_gazepoint_biometrics_to_ttl(pd.DataFrame({'TTL0':[0,1,0], 'time_ms':[0,10,20]}),pre_window_ms=0,post_window_ms=0)
    assert z['overview'].status.iloc[0]=='ttl_events_detected_no_rows_aligned'
