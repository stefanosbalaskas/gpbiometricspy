from __future__ import annotations

import os
from pathlib import Path
import subprocess
import textwrap

import pytest


INSTALLED_ARTIFACT_KIND = os.environ.get("GPBIOMETRICSPY_INSTALLED_ARTIFACT_KIND")
INSTALLED_PYTHON = os.environ.get("GPBIOMETRICSPY_INSTALLED_PYTHON")

pytestmark = pytest.mark.skipif(
    not INSTALLED_PYTHON,
    reason="installed-distribution Python is not configured",
)


def test_installed_dual_resource_replay_requires_each_secondary_resource(
    tmp_path: Path,
) -> None:
    assert INSTALLED_ARTIFACT_KIND in {"wheel", "sdist"}
    assert INSTALLED_PYTHON is not None

    probe_path = tmp_path / f"installed-{INSTALLED_ARTIFACT_KIND}-missing-resource-probe.py"
    probe = textwrap.dedent(
        """
        from __future__ import annotations

        import os
        from pathlib import Path
        import subprocess
        import sys

        import gpbiometricspy as gp
        import numpy as np

        from studio.event_alignment_services import (
            REPLAY_EVENT_LOG_ENV,
            REPLAY_TARGET_STREAM_ENV,
            run_event_alignment,
        )
        from studio.reporting_services import workflow_replay_script
        from studio.state import ProjectState


        TMP_PATH = Path(__TMP_PATH__)
        participant_files = [Path(path) for path in gp.kiosk_demo_files()]
        assert len(participant_files) >= 2
        reference_path = participant_files[0]
        target_path = participant_files[1]

        reference = gp.import_gazepoint_biometrics(reference_path)
        target = gp.import_gazepoint_biometrics(target_path)
        ttl = reference["TTL0"].to_numpy(dtype=float)
        valid = reference["TTLV"].to_numpy(dtype=float)
        time = reference["TIME"].to_numpy(dtype=float)
        active = np.isfinite(ttl) & (ttl != 0) & np.isfinite(valid) & (valid == 1)
        rising = active & ~np.concatenate(([False], active[:-1]))
        event_times = time[rising & np.isfinite(time)]
        assert len(event_times) >= 2
        participant_id = str(reference["participant_id"].iloc[0])

        event_path = TMP_PATH / "installed-missing-resource-events.csv"
        event_path.write_text(
            "trial,onset,condition,participant_id\\n"
            f"E1,{float(event_times[0])},stimulus,{participant_id}\\n"
            f"E2,{float(event_times[1])},stimulus,{participant_id}\\n",
            encoding="utf-8",
        )
        events = gp.import_gazepoint_event_log(event_path)

        recorded = run_event_alignment(
            reference,
            source_mode="event_log",
            time_col="TIME",
            validity_col="TTLV",
            group_col="participant_id",
            external_events=events,
            pre_s=1.0,
            post_s=5.0,
            summary_cols=["GSR_US"],
            target_stream=target,
            target_time_col="TIME",
            target_ttl_col="TTL0",
            target_validity_col="TTLV",
            target_group_col="participant_id",
            stream_method="linear",
        )
        parameters = recorded["parameters"]
        assert parameters["external_events_sha256"]
        assert parameters["target_stream_used"] is True
        assert parameters["target_stream_sha256"]

        validation = gp.validate_gazepoint_biometrics(reference, require_active_signal=False)
        state = ProjectState().with_dataset(
            reference,
            source_name="packaged_participant.csv",
            validation=validation,
            operation="load_upload",
        )
        state = state.with_analysis(
            "event_alignment",
            {"parameters": parameters},
            parameters=parameters,
        )
        replay_text = workflow_replay_script(state)
        assert "external_events_sha256" in replay_text
        assert "target_stream_sha256" in replay_text
        assert str(event_path) not in replay_text
        assert event_path.name not in replay_text
        assert str(target_path) not in replay_text
        assert target_path.name not in replay_text

        placeholder = 'DATA_PATH = Path("PATH/TO/SOURCE_DATA.csv")'
        assert placeholder in replay_text
        replay_path = TMP_PATH / "installed-dual-resource-replay.py"
        replay_path.write_text(
            replay_text.replace(
                placeholder,
                f"DATA_PATH = Path({str(reference_path)!r})",
                1,
            ),
            encoding="utf-8",
        )

        clean_env = os.environ.copy()
        clean_env.pop(REPLAY_EVENT_LOG_ENV, None)
        clean_env.pop(REPLAY_TARGET_STREAM_ENV, None)

        missing_both = subprocess.run(
            [sys.executable, str(replay_path)],
            cwd=TMP_PATH,
            env=clean_env,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        assert missing_both.returncode != 0
        missing_both_output = f"{missing_both.stdout}\\n{missing_both.stderr}"
        assert "Recorded event-log replay requires the separately managed event log" in missing_both_output

        target_only_env = clean_env.copy()
        target_only_env[REPLAY_TARGET_STREAM_ENV] = str(target_path)
        missing_event = subprocess.run(
            [sys.executable, str(replay_path)],
            cwd=TMP_PATH,
            env=target_only_env,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        assert missing_event.returncode != 0
        missing_event_output = f"{missing_event.stdout}\\n{missing_event.stderr}"
        assert "Recorded event-log replay requires the separately managed event log" in missing_event_output

        event_only_env = clean_env.copy()
        event_only_env[REPLAY_EVENT_LOG_ENV] = str(event_path)
        missing_target = subprocess.run(
            [sys.executable, str(replay_path)],
            cwd=TMP_PATH,
            env=event_only_env,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        assert missing_target.returncode != 0
        missing_target_output = f"{missing_target.stdout}\\n{missing_target.stderr}"
        assert "Recorded cross-stream replay requires the separately managed target stream" in missing_target_output

        exact_env = clean_env.copy()
        exact_env[REPLAY_EVENT_LOG_ENV] = str(event_path)
        exact_env[REPLAY_TARGET_STREAM_ENV] = str(target_path)
        exact = subprocess.run(
            [sys.executable, str(replay_path)],
            cwd=TMP_PATH,
            env=exact_env,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        assert exact.returncode == 0, (
            "Installed exact-resource replay failed.\\n"
            f"stdout:\\n{exact.stdout}\\n"
            f"stderr:\\n{exact.stderr}"
        )
        assert exact.stdout.strip()
        print("installed missing-secondary-resource replay guards passed")
        """
    ).replace("__TMP_PATH__", repr(str(tmp_path)))
    probe_path.write_text(probe, encoding="utf-8")

    result = subprocess.run(
        [INSTALLED_PYTHON, str(probe_path)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    assert result.returncode == 0, (
        "Installed missing-resource replay probe failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "installed missing-secondary-resource replay guards passed" in result.stdout
