import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.october_2026.edabe_reference import (  # noqa: E402
    audit_edabe_reference_export,
)


def _fixture():
    return pd.DataFrame({
        "participant_id":["a"]*4+["b"]*4,
        "recording_id":["s"]*8,"benchmark_split":["train"]*4+["test"]*4,
        "time":[0,1,2,3]*2,
        "rawdata":[1,2,1,2]*2,
        "cleandata":[1,1,1,1]*2,
        "signal_automatic":[1,1,1,1]*2,
        "binarytarget":[0,1,0,1]*2,
        "predArtifacts":[0,1,0,1]*2,
        "postProcessedPredArtifacts":[0,1,0,1]*2,
    })


def test_edabe_reference_not_scr_outcome():
    a=audit_edabe_reference_export(_fixture())
    assert len(a["recording_metrics"])==2
    assert (a["recording_metrics"].automatic_expert_mae==0).all()
    assert (a["recording_metrics"].artifact_recall==1).all()
    assert a["reference_kind"]=="human_edited_eda_signal_and_artifact_annotations"


def test_edabe_refuses_shared_participants():
    d=_fixture()
    d.loc[d.benchmark_split=="test","participant_id"]="a"
    with pytest.raises(ValueError,match="leakage"):
        audit_edabe_reference_export(d)


def test_edabe_refuses_nonmonotonic_time():
    d=_fixture()
    d.loc[3,"time"]=1
    with pytest.raises(ValueError,match="strictly increasing"):
        audit_edabe_reference_export(d)
