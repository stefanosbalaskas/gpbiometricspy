from pathlib import Path
import numpy as np
import pandas as pd
import pytest

import gpbiometricspy.data_io_cleaning as m


def test_delimiter_type_unique_session_helpers(tmp_path):
    empty=tmp_path/'empty.csv';empty.write_text('')
    assert m._guess_delimiter(empty)==','
    assert m._detect_type(Path('x_fixations.csv'))=='fixations'
    assert m._detect_type(Path('x_summary.csv'))=='summary'
    assert m._detect_type(Path('x_ttl.csv'))=='markers'
    assert m._detect_type(Path('x_other.csv'))=='unknown'
    assert m._make_unique(['x','x','x','x_1'])==['x','x_1','x_2','x_1_1']
    with pytest.raises(ValueError,match='session_match'):m._session_keep([],session_match='bad')
    fs=[Path('ABC_file.csv'),Path('xyz_ABC.csv')]
    assert m._session_keep(fs,None)==[True,True]
    assert m._session_keep(fs,'ABC','regex')==[True,True]
    assert m._session_keep(fs,'ABC','contains')==[True,True]


def test_import_more_validation_recursive_and_names(tmp_path):
    with pytest.raises(ValueError,match='Supply'):m.import_gazepoint_data(None)
    with pytest.raises(ValueError,match='Invalid.*pattern'):m.import_gazepoint_data(tmp_path,pattern='[')
    (tmp_path/'A_fixations.csv').write_text('x,y\n1,2\n')
    with pytest.raises(ValueError,match='matched.*session'):m.import_gazepoint_data(tmp_path,session='ZZZ')
    sub=tmp_path/'sub';sub.mkdir();(sub/'A_event.csv').write_text('x\tvalue\n1\t2\n')
    out=m.import_gazepoint_data(tmp_path,recursive=True,add_file_info=False)
    assert len(out)==2 and all('gp_source_file' not in d for d in out.values())


def test_allowed_missing_and_internal_imputation_edges(monkeypatch):
    assert not m._allowed_missing([False,False],1).any()
    assert m._allowed_missing([True,True],np.inf).all()
    # non-numeric original triggers pd.to_numeric fallback
    out,flag=m._impute_vector(np.array(['1',None,'3'],dtype=object),method='linear')
    assert out.tolist()==[1,2,3]
    # malformed time gets replaced by row index
    out,_=m._impute_vector([1,np.nan,3],time=['bad','bad','bad'])
    assert out[1]==2
    # no allowed gaps returns immediately
    out,flag=m._impute_vector([1,np.nan,3],max_gap=0)
    assert np.isnan(out[1]) and not flag.any()
    # all-missing constant path
    out,flag=m._impute_vector([np.nan,np.nan],method='constant',constant_value=7)
    assert out.tolist()==[7,7] and flag.all()
    # exactly one observed value in linear path
    out,_=m._impute_vector([np.nan,2,np.nan],method='linear')
    assert out.tolist()==[2,2,2]
    # nearest right-only and left-only branches
    assert m._impute_vector([np.nan,2,3],method='nearest')[0][0]==2
    assert m._impute_vector([1,2,np.nan],method='nearest')[0][-1]==2
    with pytest.raises(ValueError,match='method'):m._impute_vector([1,np.nan,2],method='bad')

    # Defensive nearest branch where observed index discovery unexpectedly returns empty.
    real=m.np.flatnonzero; calls={'n':0}
    def fake(x):
        calls['n']+=1
        if calls['n']==1:return np.array([],dtype=int)
        return real(x)
    monkeypatch.setattr(m.np,'flatnonzero',fake)
    z,_=m._impute_vector([1,np.nan,2],method='nearest')
    assert np.isnan(z[1])


def test_public_imputation_remaining_routes_and_validation():
    s=pd.Series([1.,np.nan,3.],name='x',index=[4,5,6])
    so=m.impute_gazepoint_missing(s)
    assert so.index.tolist()==[4,5,6] and so.iloc[1]==2
    with pytest.raises(ValueError,match='method'):m.impute_gazepoint_missing([1,np.nan],method='bad')
    with pytest.raises(ValueError,match='max_gap'):m.impute_gazepoint_missing([1,np.nan],max_gap='bad')
    with pytest.raises(TypeError,match='numeric vector'):m.impute_gazepoint_missing(np.ones((2,2)))
    with pytest.raises(TypeError,match='numeric vector'):m.impute_gazepoint_missing(object())
    with pytest.raises(ValueError,match='grouping'):m.impute_gazepoint_missing(pd.DataFrame({'x':[1,np.nan]}),group_cols='g')
    with pytest.raises(ValueError,match='No columns'):m.impute_gazepoint_missing(pd.DataFrame({'label':['a','b']}))
    with pytest.raises(ValueError,match='Missing columns'):m.impute_gazepoint_missing(pd.DataFrame({'x':[1,2]}),cols='y')
    d=pd.DataFrame({'x':[1,np.inf,3]})
    no=m.impute_gazepoint_missing(d,cols='x',treat_infinite_as_missing=False,add_flags=False)
    assert np.isinf(no.x.iloc[1]) and 'x_was_imputed' not in no

def test_impute_non_numeric_coercion_and_cols_sequence_branch():
    out,_=m._impute_vector(np.array(['1','bad','3'],dtype=object),method='linear')
    assert out.tolist()==[1,2,3]
    d=pd.DataFrame({'x':[1.,np.nan,3.]})
    out2=m.impute_gazepoint_missing(d,cols=['x'])
    assert out2.x.iloc[1]==2
