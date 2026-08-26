import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def _write(path, text):
    path.write_text(text, encoding='utf-8')


def test_column_inventory_and_active_channels():
    dat=pd.DataFrame({'TIME':[.01,.02],'GSR':[500000,510000],'GSR_US':[2.,1.96],'GSRV':[1,1],
                      'HR':[75,76],'HRV':[1,1],'HRP':[.1,.2],'IBI':[.8,.79],'DIAL':[.2,.4],'DIALV':[1,1]})
    cols=gp.check_gazepoint_biometric_columns(dat)
    for c in ['GSR_US','HR','IBI','DIAL']:
        assert bool(cols.loc[cols.column==c,'present'].iloc[0])
    active=gp.detect_active_biometric_channels(dat)
    assert active.set_index('signal').loc['gsr_eda','active']
    assert active.set_index('signal').loc['heart_rate','active']
    assert active.set_index('signal').loc['engagement_dial','active']
    gsr=active.set_index('signal').loc['gsr_eda']
    assert gsr.summary_column=='GSR_US' and gsr.min_value==pytest.approx(1.96) and gsr.max_value==pytest.approx(2.0)
    inactive=gp.detect_active_biometric_channels(pd.DataFrame({'GSR_US':[0,0,0],'GSRV':[0,0,0],'HR':[0,0,0],'HRV':[0,0,0],'DIAL':[0,0,0],'DIALV':[0,0,0]}))
    assert not inactive.loc[inactive.signal.isin(['gsr_eda','heart_rate','engagement_dial']),'active'].any()


def test_import_single_file_drops_trailing_empty_and_attaches_metadata(tmp_path):
    file=tmp_path/'User 0_all_gaze.csv'
    _write(file,'TIME,GSR_US,GSRV,HR,HRV,DIAL,DIALV,\n0.01,2.0,1,75,1,0.1,1,\n0.02,2.1,1,76,1,0.2,1,\n')
    dat=gp.import_gazepoint_biometrics(file)
    assert {'GSR_US','HR','DIAL'}.issubset(dat.columns)
    assert not any(str(c).lower().startswith('unnamed:') for c in dat.columns)
    assert isinstance(dat.attrs['biometric_columns'],pd.DataFrame)
    assert dat.attrs['class'][0]=='gazepoint_biometrics'
    with pytest.raises(FileNotFoundError,match='does not exist'):
        gp.import_gazepoint_biometrics(tmp_path/'missing.csv')
    with pytest.raises(ValueError,match='non-empty'):
        gp.import_gazepoint_biometrics('')


def test_folder_import_combines_gaze_and_fixations_and_skips_summary(tmp_path):
    gaze=tmp_path/'User 0_all_gaze.csv'; fix=tmp_path/'User 0_fixations.csv'; summary=tmp_path/'Data_Summary_export_test.csv'
    _write(gaze,'TIME,GSR_US,GSRV,HR,HRV,DIAL,DIALV,\n0.01,2.0,1,75,1,0.1,1,\n0.02,2.1,1,76,1,0.2,1,\n')
    _write(fix,'TIME,FPOGX,FPOGY,FPOGS,FPOGD,FPOGID,GSR_US,GSRV,HR,HRV,DIAL,DIALV,\n0.03,0.5,0.6,0.01,0.20,1,2.2,1,77,1,0.3,1,\n0.04,0.6,0.7,0.03,0.30,2,2.3,1,78,1,0.4,1,\n')
    _write(summary,'Gazepoint Analysis,v7.2.0\nProcessed on,example\nAOI Summary\n')
    dat=gp.import_gazepoint_biometric_folder(tmp_path)
    assert len(dat)==4
    assert {'source_file','source_type','source_participant','GSR_US','HR','DIAL'}.issubset(dat.columns)
    assert not dat.source_file.str.contains('Data_Summary').any()
    assert {'all_gaze','fixations'}.issubset(set(dat.source_type))
    assert 'User 0' in set(dat.source_participant)
    active=dat.attrs['active_channels'].set_index('signal')
    assert active.loc['gsr_eda','active'] and active.loc['heart_rate','active'] and active.loc['engagement_dial','active']
    assert dat.attrs['class'][0]=='gazepoint_biometrics_folder'

    with pytest.raises(FileNotFoundError,match='Folder does not exist'):
        gp.import_gazepoint_biometric_folder(tmp_path/'missing')
    empty=tmp_path/'empty'; empty.mkdir()
    with pytest.raises(ValueError,match='No CSV'):
        gp.import_gazepoint_biometric_folder(empty)
    nonbio=tmp_path/'nonbio'; nonbio.mkdir(); _write(nonbio/'P1_all_gaze.csv','TIME,X,Y,\n0.01,1,2,\n0.02,3,4,\n')
    with pytest.raises(ValueError,match='none contained known'):
        gp.import_gazepoint_biometric_folder(nonbio)


def test_validation_and_missingness():
    active=pd.DataFrame({'TIME':[.01,.02,.03],'GSR_US':[2.,2.1,2.2],'GSRV':[1,1,1],
                         'HR':[75,76,77],'HRV':[1,1,1],'DIAL':[.1,.2,.3],'DIALV':[1,1,1]})
    val=gp.validate_gazepoint_biometrics(active,require_active_signal=True)
    assert val['overview'].iloc[0].n_rows==3 and val['overview'].iloc[0].active_signal_count==3
    assert val['issues'].empty and val['class'][0]=='gazepoint_biometrics_validation'
    inactive=active.copy()
    for c in ['GSR_US','GSRV','HR','HRV','DIAL','DIALV']: inactive[c]=0
    v2=gp.validate_gazepoint_biometrics(inactive,require_active_signal=True)
    assert 'no_active_biometric_signal' in set(v2['issues'].issue)
    unknown=gp.validate_gazepoint_biometrics(pd.DataFrame({'TIME':[.01,.02],'X':[1,2],'Y':[3,4]}))
    assert 'no_known_biometric_columns' in set(unknown['issues'].issue)

    dat=pd.DataFrame({'GSR_US':[2.,np.nan,0.],'GSRV':[1,0,0],'HR':[75,np.nan,0.],'HRV':[1,0,0],'DIAL':[.1,np.nan,0.],'DIALV':[1,0,0]})
    audit=gp.audit_gazepoint_biometric_missingness(dat)
    gsr=audit.set_index('column').loc['GSR_US']
    assert gsr.n_rows==3 and gsr.missing_rows==1 and gsr.zero_rows==1
    empty=gp.audit_gazepoint_biometric_missingness(pd.DataFrame({'X':[1,2],'Y':[3,4]}))
    assert empty.empty
