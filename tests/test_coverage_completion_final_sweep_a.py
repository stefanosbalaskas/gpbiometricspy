from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from gpbiometricspy import _helpers as h
from gpbiometricspy import advanced_nonlinear as an
from gpbiometricspy import event_frontdoor as ef
from gpbiometricspy import frontdoor as fd
from gpbiometricspy import governance_core as gc
from gpbiometricspy import governance_extra as ge
from gpbiometricspy import pupil_gaze as pg
from gpbiometricspy import pupil_qc as pq
from gpbiometricspy import qc_windows_standardization as qws
from gpbiometricspy import reports as rp
from gpbiometricspy import schema_io as sio
from gpbiometricspy import scientific_qc as sq
from gpbiometricspy import signal_quality as sg


def test_helpers_remaining_branches():
    with pytest.raises(ValueError):
        h.guess_col(pd.DataFrame({'x':[1]}), ['missing'], 'thing', True)
    assert np.allclose(h.time_seconds([0, 10, 20]), [0, .01, .02])


def test_advanced_nonlinear_remaining_internals(monkeypatch):
    with pytest.raises(TypeError):
        an._numeric_col(pd.DataFrame({'x':['a','b']}), 'x')
    assert np.isnan(an._sample_entropy([1,2,3], m=2, r=.2))
    assert np.isnan(an._approx_entropy([1,2,3], m=2, r=.2))
    assert np.isnan(an._dfa_alpha(np.arange(10.0)))
    # Constant signal yields too few positive fluctuation scales.
    assert np.isnan(an._dfa_alpha(np.ones(64)))
    assert an._coarse(np.arange(2.0), 10).size == 0
    assert an._runs(np.array([])) == ([], [])
    # No eligible diagonal line when min_line_length is above every line.
    out=an.extract_gazepoint_hrv_rqa(pd.DataFrame({'IBI':np.arange(800, 820, dtype=float)}), min_line_length=1000)
    assert np.isnan(out['features'].iloc[0]['diagonal_entropy'])
    # Closely spaced later peak replaces weaker prior selected peak.
    x=np.array([0,2,0,3,0],float); t=np.array([0,.1,.2,.3,.4])
    assert an._find_peaks(x,t,min_dist=.5)==[3]


def test_pupil_guess_blink_impute_and_fixation_branches():
    df=pd.DataFrame({'LPD':[3.,0.,4.], 'RPD':[3.,0.,5.], 'LPV':[1,0,1], 'RPV':[1,0,1], 'TIME':[0.,.1,.2]})
    assert pg._guess_pupil_cols(df)==['LPD','RPD']
    with pytest.raises(ValueError): pg._guess_pupil_cols(pd.DataFrame({'x':[1.]}))
    with pytest.raises(ValueError): pg.detect_gazepoint_pupil_blinks(df, combine='bad')
    with pytest.raises(ValueError): pg.detect_gazepoint_pupil_blinks(df, return_='bad')
    with pytest.raises(TypeError): pg.detect_gazepoint_pupil_blinks(df, nonsense=True)
    flags=pg.detect_gazepoint_pupil_blinks(df, return_='flags')
    assert flags.tolist()==[False,True,False]
    assert pg.detect_gazepoint_pupil_blinks(df, return_='onsets').tolist()==[.1]
    # Grouped interval insertion branch.
    g=df.assign(group=['a','a','a'])
    z=pg.detect_gazepoint_pupil_blinks(g, group_cols='group')
    assert z.loc[0,'group']=='a'
    for method in ['linear','locf','nocb','nearest','constant']:
        y=pg._impute([1,np.nan,3],method=method)
        assert np.isfinite(y).all()
    assert np.isnan(pg._impute([1,np.nan,np.nan,4],max_gap=1)[1:3]).all()
    assert np.isnan(pg._impute([np.nan,np.nan],method='constant')).all()
    with pytest.raises(ValueError): pg._impute([1,np.nan,2],method='x')
    cleaned=pg.clean_gazepoint_pupil_signal(df, method='locf', keep_flags=False)
    assert 'LPD_clean' in cleaned and 'LPD_was_blink' not in cleaned
    fix=pd.DataFrame({'duration':[100,200], 'x':[np.nan,np.nan], 'y':[np.nan,np.nan]})
    sm=pg.summarize_gazepoint_fixations(fix,duration_unit='milliseconds')
    assert np.isnan(sm.iloc[0].x_dispersion)


def test_pupil_qc_remaining_branches():
    df=pd.DataFrame({'left_pupil':[3.,0.,9.], 'right_pupil':[3.,3.,3.]})
    assert pq._pupil_cols(df)==['left_pupil','right_pupil']
    with pytest.raises(ValueError): pq._pupil_cols(pd.DataFrame({'x':[1.]}))
    out=pq.detect_gazepoint_blinks(df,pupil_cols=['left_pupil'],min_pupil=1,max_pupil=8,change_threshold=2,extend_samples=1,mask=False)
    assert out['data']['left_pupil_blink_flag'].all()


def test_schema_io_remaining_branches():
    assert sio._make_unique(['a','a','a'])==['a','a_1','a_2']
    df=pd.DataFrame([[1,2]],columns=[' GSR ','GSR'])
    out=sio.standardise_gazepoint_biometric_names(df)
    assert len(set(out.columns))==2
    with pytest.raises(TypeError): sio.detect_gazepoint_time_columns('bad')
    tc=sio.detect_gazepoint_time_columns(pd.DataFrame({'TRIAL_TIME':[1,2], 'foo_time_bar':[1,2]}))
    assert {'trial_or_media_time','candidate_time'} <= set(tc.role)
    # Generic timebase auto seconds/milliseconds and empty-interval branches.
    sec=sio.detect_gazepoint_biometric_timebase(pd.DataFrame({'abc_time':[0,.1,.2]}), time_col='abc_time')
    assert sec['overview'].iloc[0]['unit']=='seconds'
    ms=sio.detect_gazepoint_biometric_timebase(pd.DataFrame({'abc_time':[0,10,20]}), time_col='abc_time')
    assert ms['overview'].iloc[0]['unit']=='milliseconds'
    one=sio.detect_gazepoint_biometric_timebase(pd.DataFrame({'abc_time':[1]}), time_col='abc_time')
    assert one['interval_summary'].iloc[0].n_intervals==0


def test_scientific_qc_remaining_branches():
    df=pd.DataFrame({'IBI':[800.,900.]})
    with pytest.raises(ValueError): sq._ibi_col(df,'bad')
    assert sq._ibi_col(df,'IBI')=='IBI'
    with pytest.raises(ValueError): sq.classify_gazepoint_scr_intervals(pd.DataFrame({'lat':[1.]}),latency_col='bad')
    out=sq.classify_gazepoint_scr_intervals(pd.DataFrame({'lat':[2.,5.,8.]}),latency_col='lat')
    assert out['scr_interval'].tolist()==['FIR','SIR','TIR']
    art=sq.flag_kleckner_eda_artifacts(pd.DataFrame({'GSR_US':[1.,1000.,1.]}),transition_padding=1,max_us=100)
    assert art.filter(like='transition').to_numpy().any()
    no=sq.convert_gazepoint_gsr_to_conductance(pd.DataFrame({'x':[1.,2.]}))
    assert no.attrs['gsr_conversion_summary'].iloc[0].status=='no_resistance_source_detected'
    direct=sq.convert_gazepoint_gsr_to_conductance(pd.DataFrame({'GSR_US':[1.,np.inf]}),gsr_col='GSR_US',input_unit='microsiemens',overwrite=True)
    assert direct.attrs['gsr_conversion_summary'].iloc[0].n_invalid==1
    tonic=sq.summarise_gazepoint_gsr_tonic_phasic(pd.DataFrame({'GSR_US':[np.nan,np.nan,np.nan]}),window_n=3)
    assert tonic['summary'].iloc[0].n_phasic_peaks==0


def test_signal_quality_remaining_rule_and_plot_branches():
    q=pd.DataFrame({'participant':['p1','p2'],'prop_missing':[.1,.2], 'quality_label':['pass','review'], 'group':['a','b']})
    with pytest.raises(ValueError): sg.classify_gazepoint_signal_quality(q,rules={'':1})
    out=sg.classify_gazepoint_signal_quality(q,rules={'n_samples_review_below':None,'prop_missing_review_at_or_above':.15})
    assert out.quality_label.tolist()==['pass','review']
    f=sg.plot_gazepoint_signal_quality(q,metric='quality_label',x='participant'); plt.close(f)
    f=sg.plot_gazepoint_signal_quality(q,metric='prop_missing',x=None,colour='group'); plt.close(f)


def test_qc_windows_coerce_paths(tmp_path):
    df=pd.DataFrame({'x':[1,2]}); assert qws._coerce(df).equals(df)
    p=tmp_path/'x.csv'; df.to_csv(p,index=False); assert qws._coerce(str(p)).equals(df)
    with pytest.raises(TypeError): qws._coerce(123)


def test_reports_remaining_warning_and_sections():
    assert rp._warning_lines(None)==[]
    assert rp._warning_lines(['a','b'])==['a','b']
    assert len(rp._warning_lines(pd.DataFrame({'warning':['x',None]})))==3
    got=rp._collect_warnings(a={'warnings':['w1']},b={'warnings':pd.DataFrame({'warning':['w2']})})
    assert got==['a: w1','b: w2']
    txt=rp.create_gazepoint_methods_section(validation={'issues':pd.DataFrame({'issue':['x']})})
    assert isinstance(str(txt),str)
    sec=rp.create_gazepoint_audit_report_section(decision_log={'decisions':pd.DataFrame({'decision':['d']})},include_warnings=False)
    assert isinstance(str(sec),str)


def test_governance_extra_remaining(monkeypatch):
    assert ge._evidence_info(None)[2] is False
    assert ge._evidence_info(pd.DataFrame({'x':[1]}))[2] is True
    assert ge._evidence_info({'a':1})[2] is True
    assert ge._evidence_info('abc')[2] is True
    ck=ge.create_gazepoint_preregistration_checklist(include_optional=False)
    out=ge.audit_gazepoint_preregistration_consistency(ck,evidence={})
    assert not out['item_results'].empty
    assert ge._vtuple(None) is None
    assert ge._vtuple('1.2')==(1,2)
    assert ge._vtuple('bad') is None
    manifest=ge.gazepoint_interoperability_manifest(include_support=False).iloc[[0]].copy()
    r=ge.audit_gazepoint_interoperability_versions(manifest,include_python=False,strict=False)
    assert not r['results'].empty
    bad=manifest.copy(); bad.loc[bad.index[0],'dependency_type']='weird'
    with pytest.raises(ValueError): ge.audit_gazepoint_interoperability_versions(bad)


def test_governance_core_remaining(tmp_path):
    assert gc._valstr(None)==''
    assert gc._valstr(np.nan)=='nan'
    assert gc._valstr(['a','b'])=='start=a; end=b'
    pm=gc.create_gazepoint_pipeline_map(steps=pd.DataFrame({'step_id':['a','b']}),edges=pd.DataFrame({'from':['a'],'to':['b']}),include_default=False)
    assert len(pm['nodes'])==2
    assert gc._audit_rows(pd.DataFrame({'x':[1]}),'a',include_summary=True)
    with pytest.raises(ValueError): gc.create_gazepoint_audit_index(audits=[pd.DataFrame({'x':[1]})],audit_ids=['a','b'])
    idx=gc.create_gazepoint_audit_index(audits={'x':pd.DataFrame({'a':[1]})},include_summary_rows=True)
    assert not idx.empty
    d=tmp_path/'exports'; d.mkdir(); pd.DataFrame({'GSR':[1]}).to_csv(d/'p_all_gaze.csv',index=False)
    inv=gc.summarize_gazepoint_export_inventory(d)
    assert not inv.empty


def test_event_frontdoor_remaining_branches():
    df=pd.DataFrame({'x':[1]})
    assert ef._guess(df,['no'],'x',False) is None
    with pytest.raises(ValueError): ef._guess(df,['no'],'x',True)
    with pytest.raises(TypeError): ef._standard_events('bad')
    ev=ef._standard_events(pd.DataFrame({'time':[1.,2.]}),event_time_col='time')
    assert 'event_id' in ev
    data=pd.DataFrame({'TIME':[0.,1.,2.,3.], 'GSR_US':[0.,.1,.2,.1]})
    ep=ef.epoch_gazepoint_scr(data,pd.DataFrame({'event_time':[1.]}),pre=1,post=1,time_col='TIME',signal_col='GSR_US',event_time_col='event_time')
    assert not ep.empty
    rr=ef.flag_gazepoint_rr_outliers([800,900,5000],method='zscore',return_='data')
    assert len(rr)==3
    eng=ef.compute_gazepoint_engagement_index([10,60],return_='summary')
    assert not eng.empty
    det=ef.detrend_gazepoint_signal(pd.DataFrame({'TIME':[0.,1.,2.],'x':[1.,2.,4.]}),signal_col='x',time_col='TIME',method='constant',preserve_mean=True)
    assert 'x_detrended' in det


def test_frontdoor_remaining_paths(tmp_path):
    # Missing/unknown columns path.
    chk=fd.check_gazepoint_biometric_columns(pd.DataFrame({'x':[1]})); assert not chk.present.any()
    active=fd.detect_active_biometric_channels(pd.DataFrame({'GSR_US':[0.,1.], 'GSRV':[0,1]})); assert active.loc[0,'active']
    assert fd._source_type('x_fixations.csv')=='fixations'
    assert fd._source_type('x_data_summary.csv')=='data_summary'
    assert fd._source_type('x.csv')=='other'
    # Folder importer skipping file with no known biometric columns.
    pd.DataFrame({'x':[1]}).to_csv(tmp_path/'bad.csv',index=False)
    pd.DataFrame({'GSR':[1.,2.]}).to_csv(tmp_path/'good_all_gaze.csv',index=False)
    out=fd.import_gazepoint_biometric_folder(tmp_path,include_other_csv=True)
    assert set(out.source_file)=={'good_all_gaze.csv'}
    p=tmp_path/'single.csv'; pd.DataFrame({'GSR':[1.]}).to_csv(p,index=False)
    assert isinstance(fd._coerce(str(p)),pd.DataFrame)
    with pytest.raises(TypeError): fd._coerce(3)
    val=fd.validate_gazepoint_biometrics(pd.DataFrame({'foo':[1]}),require_active_signal=True)
    assert {'no_known_biometric_columns','no_time_columns','no_active_biometric_signal'} <= set(val['issues'].issue)
    with pytest.raises(TypeError): fd.audit_gazepoint_biometric_missingness(pd.DataFrame({'GSR':[1.]}),columns=3)
