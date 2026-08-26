import numpy as np
import pandas as pd
import pytest
import gpbiometricspy as gp


def test_data_summary_parses_metadata_sections_numeric_and_absent(tmp_path):
    f=tmp_path/'Data_Summary_export_test.csv'
    f.write_text('\n'.join([
      'Gazepoint Analysis,v7.2.0','Processed on,Thu Jun 11 23:50:26 2026','',
      'Note: -1 values indicate an AOI that was never viewed','AOI Summary',
      'Media ID, Media Name,AOI ID,AOI Name,Viewers (#),Ave Time Viewed (sec),',
      '0,NewMedia0,2,AOI 2,2,1.400,','1,NewMedia1,0,AOI 0,2,2.235,','',
      'AOI Statistics (for each user)',
      'Media ID, Media Name,AOI ID,AOI Name,User ID,User Name,Time Viewed (sec),Fixations (#),Ave Dial (0-1),Ave GSR (kOhm),Ave Heart Rate (BPM),Ave Interbeat Interval (s),Ave Left Pupil (mm),Ave Right Pupil (mm),',
      '0,NewMedia0,2,AOI 2,4,User 4,0.937,3,1.000,815880.062,88.442,0.678,7.041,5.707,',
      '0,NewMedia0,2,AOI 2,5,User 5,1.863,7,1.000,362668.094,87.988,0.681,4.605,5.451,'
    ]),encoding='utf-8')
    out=gp.import_gazepoint_data_summary(f)
    assert out['class'][0]=='gazepoint_data_summary'
    assert out['metadata'].iloc[0].software=='Gazepoint Analysis' and out['metadata'].iloc[0].version=='v7.2.0'
    assert len(out['aoi_summary'])==2 and len(out['aoi_statistics'])==2
    assert out['aoi_statistics'].iloc[0]['Ave Heart Rate (BPM)']==pytest.approx(88.442)
    assert out['aoi_statistics'].iloc[0]['Ave Dial (0-1)']==pytest.approx(1.0)
    assert out['aoi_summary'].iloc[0].source_file==f.name
    f2=tmp_path/'minimal.csv'; f2.write_text('Gazepoint Analysis,v7.2.0\nProcessed on,example\n',encoding='utf-8')
    m=gp.import_gazepoint_data_summary(f2)
    assert m['aoi_summary'].empty and m['aoi_statistics'].empty
    with pytest.raises(FileNotFoundError,match='File does not exist'):
        gp.import_gazepoint_data_summary(tmp_path/'missing.csv')


def test_standardise_names_mapping_snake_duplicates_and_validation():
    assert gp.standardise_gazepoint_biometric_names(['time ms','heart rate','eda uS','rr interval','engagement dial'])==['TIME_MS','HR','GSR_US','IBI','ENGAGEMENT']
    df=pd.DataFrame({'time ms':[1,2,3],'heart rate':[70,71,72]})
    renamed=gp.standardise_gazepoint_biometric_names(df)
    assert renamed.columns.tolist()==['TIME_MS','HR']
    mapping=gp.standardise_gazepoint_biometric_names(df,rename=False)
    assert mapping.original_name.tolist()==['time ms','heart rate'] and mapping.standard_name.tolist()==['TIME_MS','HR'] and mapping.changed.all()
    assert gp.standardise_gazepoint_biometric_names(['time ms','heart rate','eda uS'],style='snake')==['time_ms','hr','gsr_us']
    assert gp.standardise_gazepoint_biometric_names(['GSR','eda'])==['GSR','GSR_1']
    with pytest.raises(TypeError,match='data frame'):
        gp.standardise_gazepoint_biometric_names([1,2,3])


def test_time_column_detection_and_timebase_seconds_ms_missing():
    out=gp.detect_gazepoint_time_columns(['CNT','TIME','TIME_MS','GSR'])
    assert {'CNT','TIME','TIME_MS'}.issubset(set(out.column))
    assert {'sample_counter','timestamp'}.issubset(set(out.role))
    assert {'seconds','milliseconds'}.issubset(set(out.unit_hint))
    empty=gp.detect_gazepoint_time_columns(['GSR','HR','ENGAGEMENT'])
    assert empty.empty and empty.columns.tolist()==['column','standard_name','role','unit_hint','confidence','reason']
    sec=pd.DataFrame({'CNT':np.arange(1,7),'TIME':np.arange(6)/60,'GSR':np.arange(100,106)})
    ts=gp.detect_gazepoint_biometric_timebase(sec)
    o=ts['overview'].iloc[0]
    assert o.primary_time_column=='TIME' and o.unit=='seconds' and round(o.sampling_rate_hz)==60 and o.status=='timebase_detected'
    ms=pd.DataFrame({'TIME_MS':np.arange(6)*16.6667,'HR':[70,70,71,71,72,72]})
    tm=gp.detect_gazepoint_biometric_timebase(ms)['overview'].iloc[0]
    assert tm.primary_time_column=='TIME_MS' and tm.unit=='milliseconds' and round(tm.sampling_rate_hz)==60
    none=gp.detect_gazepoint_biometric_timebase(pd.DataFrame({'GSR':[1,2,3],'HR':[70,71,72]}))
    assert none['overview'].iloc[0].status=='no_timebase_detected' and pd.isna(none['overview'].iloc[0].primary_time_column) and none['warnings']
    with pytest.raises(TypeError,match='data frame'):
        gp.detect_gazepoint_biometric_timebase(['CNT','TIME'])


def test_schema_active_numbered_ttl_and_conservative_hrv():
    df=pd.DataFrame({'CNT':np.arange(1,7),'TIME':np.arange(6)/60,'GSR':[100,101,102,103,102,101],
                     'HR':[70,70,71,71,72,72],'HRV':[1]*6,'ENGAGEMENT':[50,51,52,53,54,55],'TTL':[0,0,1,0,1,0]})
    out=gp.detect_gazepoint_biometric_schema(df); o=out['overview'].iloc[0]
    assert o.has_gsr_eda and o.has_heart_rate and o.has_hrv_flag and o.has_engagement_dial and o.has_ttl_marker
    assert o.active_gsr_eda and o.active_heart_rate and o.active_engagement_dial and o.active_ttl_marker and o.status=='biometric_schema_detected'
    numbered=pd.DataFrame({'CNT':np.arange(1,6),'GSR':[1,1.1,1.2,1.1,1],'TTL0':[0,0,1,0,0],'TTL1':[0,1,0,0,0],'TTLV':[1]*5})
    n=gp.detect_gazepoint_biometric_schema(numbered); no=n['overview'].iloc[0]
    assert no.has_ttl_marker and no.active_ttl_marker
    rows=n['columns'][n['columns'].column.isin(['TTL0','TTL1','TTLV'])]
    assert len(rows)==3 and all(rows[rows.column.isin(['TTL0','TTL1'])].signal_group=='ttl_marker')
    assert rows.loc[rows.column=='TTLV','signal_group'].iloc[0]=='ttl_validity_flag'
    h=gp.detect_gazepoint_biometric_schema(pd.DataFrame({'CNT':[1,2,3],'TIME':[0,.016,.032],'HR':[70,71,72],'HRV':[1,1,1]}))
    hrv=h['columns'][h['columns'].standard_name=='HRV'].iloc[0]
    assert hrv.signal_group=='heart_rate_validity_flag' and 'validity/vendor flag' in hrv.interpretation_note
    assert any('Treat raw HRV columns' in note for note in h['notes'])
    with pytest.raises(TypeError,match='data frame'):
        gp.detect_gazepoint_biometric_schema(['CNT','TIME'])
