from pathlib import Path
import builtins
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.remaining_core as m


def test_coerce_groups_and_artifact_validation(tmp_path):
    p=tmp_path/'d.csv';pd.DataFrame({'x':[1,2]}).to_csv(p,index=False)
    assert m._coerce_df(p).x.tolist()==[1,2]
    assert m._coerce_df({'data':pd.DataFrame({'x':[3]})}).x.iloc[0]==3
    with pytest.raises(TypeError):m._coerce_df([])
    with pytest.raises(ValueError,match='group_cols'):m._resolve_groups(pd.DataFrame({'x':[1]}),'missing')
    assert m._group_ids(pd.DataFrame({'x':[1,2]}),[]).tolist()==['all','all']

    with pytest.raises(ValueError,match='at least one row'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[]}), 'x')
    with pytest.raises(ValueError,match='signal_cols'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1]}), [])
    with pytest.raises(ValueError,match='Unsupported'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1]}),'x',artifact='bad')
    with pytest.raises(ValueError,match='artifact_length'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1]}),'x',artifact_length=0)
    with pytest.raises(ValueError,match='magnitude'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1]}),'x',magnitude=np.inf)
    with pytest.raises(TypeError,match='suffix'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1]}),'x',suffix=1)
    with pytest.raises(TypeError,match='overwrite'):m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1]}),'x',overwrite='yes')
    # constant signal uses scale fallback
    o=m.simulate_gazepoint_artifact(pd.DataFrame({'x':[1.,1.,1.]}),'x',artifact='spike',seed=1)
    assert np.isfinite(o['data'].x_artifact).all()


def test_manifest_empty_validation_and_json(tmp_path, monkeypatch):
    man=m.generate_gazepoint_manifest(include_session_info=True)
    txt=m._manifest_text(man)
    assert 'input: none supplied' in txt and 'parameters: none supplied' in txt
    with pytest.raises(TypeError,match='input_paths'):m.generate_gazepoint_manifest(input_paths=1)
    with pytest.raises(TypeError,match='outputs'):m.generate_gazepoint_manifest(outputs=1)
    with pytest.raises(TypeError,match='notes'):m.generate_gazepoint_manifest(notes=1)
    with pytest.raises(TypeError,match='write_path'):m.generate_gazepoint_manifest(write_path=1)
    with pytest.raises(TypeError,match='include_session_info'):m.generate_gazepoint_manifest(include_session_info='yes')
    j=tmp_path/'m.json';m.generate_gazepoint_manifest(write_path=j);assert 'input_files' in j.read_text()


def test_named_dictionary_file_missing_and_validation(tmp_path):
    s=pd.Series({'x':'mm'})
    assert m._named_lookup(['x'],s)==['mm']
    d=pd.DataFrame({'column':['x']})
    assert m._append_missing_required(d,[],None,None) is d
    with pytest.raises(TypeError,match='data'):m.create_gazepoint_dictionary(data=[])
    with pytest.raises(TypeError,match='file_paths'):m.create_gazepoint_dictionary(file_paths=1)
    missing=tmp_path/'none.csv'
    out=m.create_gazepoint_dictionary(file_paths=missing,required_cols='req')
    assert (out.column=='req').any()


def test_anonymize_and_baseline_smoothing_validation():
    d=pd.DataFrame({'id':['a'],'x':[1.]})
    with pytest.raises(ValueError,match='at least one'):m.anonymize_gazepoint_data(d,[])
    with pytest.raises(TypeError,match='prefix'):m.anonymize_gazepoint_data(d,'id',prefix=1)
    with pytest.raises(ValueError,match='width'):m.anonymize_gazepoint_data(d,'id',width=0)
    with pytest.raises(TypeError,match='keep_mapping'):m.anonymize_gazepoint_data(d,'id',keep_mapping='yes')

    br=np.array([True])
    with pytest.raises(ValueError,match='value_column'):m._baseline_correct(d,br,'missing',None,None,'y','mean',True)
    with pytest.raises(ValueError,match='baseline_rows'):m._baseline_correct(d,[1],'x',None,None,'y','mean',True)
    with pytest.raises(ValueError,match='summary'):m._baseline_correct(d,br,'x',None,None,'y','bad',True)
    with pytest.raises(ValueError,match='group_columns'):m._baseline_correct(d,br,'x',None,'g','y','mean',True)
    with pytest.raises(ValueError,match='could not be determined'):m.baseline_correct_gazepoint_gsr(pd.DataFrame({'x':[1]}),br)
    with pytest.raises(ValueError,match='non-empty'):m.smooth_gazepoint_biometrics(d,'')
    with pytest.raises(ValueError,match='not found'):m.smooth_gazepoint_biometrics(d,'bad')


def test_unit_and_positive_scalar_branches():
    with pytest.raises(ValueError,match='unit'):m._detect_unit([1],'bad')
    assert m._detect_unit([1],'seconds')=='seconds'
    assert m._detect_unit([np.nan,0],'auto')=='ms'
    with pytest.raises(ValueError,match='positive finite'):m._positive_scalar(0,'x')

def test_manifest_version_import_fallback(monkeypatch):
    real_import=builtins.__import__
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if '__version__' in tuple(fromlist or ()):
            raise ImportError('forced version lookup failure')
        return real_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(builtins,'__import__',fake_import)
    out=m.generate_gazepoint_manifest(include_session_info=False)
    assert out['package_version']=='0.1.3'
