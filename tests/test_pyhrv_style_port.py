from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt
import gpbiometricspy as gp


def test_time_domain_and_utilities():
    nni=800+40*np.sin(np.linspace(0,8*np.pi,300))
    td=gp.compute_gazepoint_pyhrv_time_domain(nni,segment_seconds=60)
    assert isinstance(td,pd.DataFrame) and {'sdnn','rmssd'}<=set(td)
    assert np.isfinite(td.loc[0,'sdnn'])
    assert isinstance(gp.compute_gazepoint_pyhrv_nn50(nni),pd.DataFrame)
    assert isinstance(gp.compute_gazepoint_pyhrv_nn20(nni),pd.DataFrame)
    peaks=np.arange(0,10.0001,.8)
    nn=gp.extract_gazepoint_pyhrv_nn_intervals(peaks)
    assert len(nn)>5 and round(float(np.mean(nn)))==800
    assert np.isfinite(gp.compute_gazepoint_pyhrv_heart_rate(nn)).all()
    seg=gp.segment_gazepoint_pyhrv_nni(np.repeat(800.,300),segment_seconds=60)
    assert isinstance(seg,pd.DataFrame) and not seg.empty
    chk=gp.check_gazepoint_pyhrv_interval([800,np.nan,3000])
    assert (~chk.valid).any()
    assert np.allclose(gp.create_gazepoint_pyhrv_time_vector([800,810]),[.8,1.61])
    assert gp.compute_gazepoint_pyhrv_nnxx(nni,20).shape[0]==1


def test_frequency_nonlinear_plots_and_runner(tmp_path):
    nni=800+40*np.sin(np.linspace(0,12*np.pi,400))
    for out in [gp.compute_gazepoint_pyhrv_welch_psd(nni),gp.compute_gazepoint_pyhrv_lomb_psd(nni,n_freq=128),gp.compute_gazepoint_pyhrv_ar_psd(nni)]:
        assert isinstance(out,dict) and isinstance(out['psd'],pd.DataFrame) and isinstance(out['measures'],pd.DataFrame)
    cmp=gp.compare_gazepoint_pyhrv_psd_methods(nni,methods=['welch','lomb'])
    assert isinstance(cmp['measures'],pd.DataFrame) and len(cmp['measures'])==2
    rng=np.random.default_rng(7); x=800+30*np.sin(np.linspace(0,8*np.pi,300))+rng.normal(0,3,300)
    assert 'sd1' in gp.compute_gazepoint_pyhrv_poincare(x)
    se=gp.compute_gazepoint_pyhrv_sample_entropy(x); assert np.isnan(se) or np.isfinite(se)
    assert isinstance(gp.compute_gazepoint_pyhrv_dfa(x),pd.DataFrame)
    assert isinstance(gp.compute_gazepoint_pyhrv_nonlinear(x),pd.DataFrame)
    out=gp.run_gazepoint_pyhrv_style(nni_ms=x)
    assert isinstance(out['time_domain'],pd.DataFrame) and isinstance(out['nonlinear'],pd.DataFrame)
    p=tmp_path/'out.rds'; gp.export_gazepoint_pyhrv_results(out,p); imp=gp.import_gazepoint_pyhrv_results(p); assert isinstance(imp,dict)
    j=tmp_path/'out.json'; gp.export_gazepoint_pyhrv_results(out,j); assert isinstance(gp.import_gazepoint_pyhrv_results(j),dict)
    figs=[gp.plot_gazepoint_pyhrv_tachogram(x),gp.plot_gazepoint_pyhrv_hr_heatplot(x),gp.plot_gazepoint_pyhrv_radar_chart(pd.concat([out['time_domain'],out['frequency_domain']['measures'],out['nonlinear']],axis=1))]
    assert all(hasattr(f,'savefig') for f in figs); plt.close('all')


def test_prepare_seconds_and_grouped():
    out=gp.prepare_gazepoint_pyhrv_input([.8,.81,.79],unit='seconds')
    assert np.allclose(out['vectors']['all'],[800,810,790])
    assert np.allclose(out['intervals']['nni_ms'],[800,810,790])
    assert np.allclose(out['intervals']['interval_end_time_s'],[.8,1.61,2.4])
    assert out['settings']['resolved_unit']=='seconds'
    d=pd.DataFrame({'participant':['P01','P01','P02','P02'],'IBI_clean_ms':[800,810,900,910]})
    out=gp.prepare_gazepoint_pyhrv_input(d,group_cols='participant')
    assert list(out['vectors'])==['P01','P02']
    assert np.array_equal(out['vectors']['P01'],[800,810]) and np.array_equal(out['manifest']['included_intervals'],[2,2])
    assert list(out['manifest']['participant'])==['P01','P02']


def test_prepare_filter_repeats_units_and_files(tmp_path):
    d=pd.DataFrame({'IBI':[800,200,2500,np.nan,-10,900]})
    out=gp.prepare_gazepoint_pyhrv_input(d,unit='milliseconds',filter='plausible',min_nni_ms=300,max_nni_ms=2000)
    assert np.array_equal(out['vectors']['all'],[800,900])
    assert list(out['intervals']['interval_status'])==['plausible','below_minimum','above_maximum','missing_or_nonfinite','non_positive','plausible']
    assert out['manifest'].loc[0,'excluded_intervals']==4
    out2=gp.prepare_gazepoint_pyhrv_input([200,800,2500,np.nan,0],unit='milliseconds',filter='none')
    assert np.array_equal(out2['vectors']['all'],[200,800,2500])
    assert all(v is None for v in out2['intervals']['exclusion_reason'][:3])
    rep=pd.DataFrame({'participant':['P01']*6,'IBI_clean_ms':[800,800,800,810,810,790]})
    r=gp.prepare_gazepoint_pyhrv_input(rep,group_cols='participant',collapse_repeated_intervals=True)
    assert np.array_equal(r['vectors']['P01'],[800,810,790])
    assert list(r['intervals']['repeated_interval'])==[False,True,True,False,True,False]
    assert r['manifest'].loc[0,'excluded_repeated']==3
    g=pd.DataFrame({'participant':['P01','P01','P02','P02'],'IBI_clean_ms':[800]*4})
    rr=gp.prepare_gazepoint_pyhrv_input(g,group_cols='participant',collapse_repeated_intervals=True)
    assert np.array_equal(rr['intervals']['repeated_interval'],[False,True,False,True])
    ms=gp.prepare_gazepoint_pyhrv_input(pd.DataFrame({'RR_ms':[800,810]})); sec=gp.prepare_gazepoint_pyhrv_input(pd.DataFrame({'IBI':[.8,.81]}))
    assert ms['settings']['unit_resolution_method']=='column_name' and sec['settings']['resolved_unit']=='seconds'
    with pytest.raises(ValueError,match='ambiguous'):gp.prepare_gazepoint_pyhrv_input([20,30,40],unit='auto')
    written=gp.prepare_gazepoint_pyhrv_input(g,group_cols='participant',output_dir=tmp_path,prefix='study')
    assert len(written['files'])==3 and all(Path(p).exists() for p in written['files']['path'])
    p01=written['files'].query("file_type=='intervals' and group_id=='P01'").iloc[0]['path']; assert Path(p01).read_text().splitlines()==['800','800']


def test_prepare_overwrite_and_validation(tmp_path):
    p=tmp_path/'gazepoint_pyhrv.csv';p.write_text('existing\n')
    with pytest.raises(FileExistsError,match='already exists'):gp.prepare_gazepoint_pyhrv_input([800,810],unit='milliseconds',output_dir=tmp_path)
    assert p.read_text().strip()=='existing' and not (tmp_path/'gazepoint_pyhrv_manifest.csv').exists()
    with pytest.raises(ValueError,match='at least one interval'):gp.prepare_gazepoint_pyhrv_input([],unit='milliseconds')
    with pytest.raises(ValueError,match='numeric'):gp.prepare_gazepoint_pyhrv_input(pd.DataFrame({'IBI':['800','810']}))
    with pytest.raises(ValueError,match='not found'):gp.prepare_gazepoint_pyhrv_input(pd.DataFrame({'IBI':[800,810]}),group_cols='participant')
    with pytest.raises(ValueError,match='cannot be used'):gp.prepare_gazepoint_pyhrv_input([800,810],group_cols='participant',unit='milliseconds')
    with pytest.raises(ValueError,match='greater'):gp.prepare_gazepoint_pyhrv_input([800,810],unit='milliseconds',min_nni_ms=2000,max_nni_ms=300)
    with pytest.raises(ValueError,match='non-negative'):gp.prepare_gazepoint_pyhrv_input([800,810],unit='milliseconds',repeated_tolerance_ms=-1)
    with pytest.raises(ValueError,match='smaller than 1'):gp.segment_gazepoint_pyhrv_nni([800]*10,overlap=1)
    with pytest.raises(ValueError,match='Supply'):gp.run_gazepoint_pyhrv_style()
    with pytest.raises(FileNotFoundError):gp.import_gazepoint_pyhrv_results(tmp_path/'missing.rds')
