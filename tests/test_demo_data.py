import gpbiometricspy as gp


def test_packaged_kiosk_demo_complete():
    overview = gp.kiosk_demo_overview().iloc[0]
    assert int(overview["participants"]) == 36
    assert int(overview["total_rows"]) == 69120
    assert len(gp.kiosk_demo_files()) == 36

    dat = gp.load_kiosk_demo()
    assert len(dat) == 69120
    assert dat["participant_id"].nunique() == 36
    assert dat["MEDIA_ID"].nunique() == 4
    for col in ["GSR", "GSR_US", "HR", "IBI", "HRP", "LPD", "RPD", "AOI", "TTL0"]:
        assert col in dat.columns
    assert dat.attrs["synthetic"] is True


def test_packaged_kiosk_demo_subset():
    dat = gp.load_kiosk_demo(participants=["synthetic_kiosk_p001"])
    assert len(dat) == 1920
    assert dat["participant_id"].unique().tolist() == ["synthetic_kiosk_p001"]
