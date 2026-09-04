from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import gpbiometricspy as gp

try:
    from studio.services import analysis_group_column_choices
except ModuleNotFoundError:  # Direct execution from inside studio/.
    from services import analysis_group_column_choices

AOI_UPLOAD_SUFFIXES = {".csv", ".txt"}
MAX_AOI_UPLOAD_BYTES = 5 * 1024 * 1024


def gaze_x_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["FPOGX", "BPOGX", "GPOGX", "LPOGX", "RPOGX", "POGX", "gaze_x", "x", "X", "CX"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def gaze_y_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["FPOGY", "BPOGY", "GPOGY", "LPOGY", "RPOGY", "POGY", "gaze_y", "y", "Y", "CY"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def gaze_time_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["time_s", "time_ms", "TIME", "CNT", "TIME_TICK", "time", "timestamp", "MSTIMER"]
    return [c for c in preferred if c in data.columns and pd.api.types.is_numeric_dtype(data[c])]


def gaze_validity_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = [
        "FPOGV",
        "BPOGV",
        "GPOGV",
        "LPOGV",
        "RPOGV",
        "POGV",
        "gaze_valid",
        "validity",
        "valid",
        "LVALID",
        "RVALID",
    ]
    return [c for c in preferred if c in data.columns]


def gaze_trial_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["trial_id", "trial", "TRIAL", "stimulus_id", "stimulus", "MEDIA_ID", "MEDIA_NAME", "screen"]
    return [c for c in preferred if c in data.columns]


def aoi_column_choices(data: pd.DataFrame | None) -> list[str]:
    if data is None:
        return []
    preferred = ["AOI", "aoi", "aoi_name", "AOI_NAME", "area_of_interest", "interest_area", "IA_LABEL"]
    return [c for c in preferred if c in data.columns]


def _group_cols(group_col: str | None, trial_col: str | None) -> list[str]:
    return list(dict.fromkeys(c for c in [group_col, trial_col] if c))


def _coordinate_mode(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    requested: str,
    screen_width_px: float | None,
    screen_height_px: float | None,
) -> str:
    if requested != "auto":
        return requested
    x = pd.to_numeric(data[x_col], errors="coerce").to_numpy(float)
    y = pd.to_numeric(data[y_col], errors="coerce").to_numpy(float)
    finite = np.r_[x[np.isfinite(x)], y[np.isfinite(y)]]
    if finite.size and float(np.nanmin(finite)) >= -0.1 and float(np.nanmax(finite)) <= 1.5:
        return "normalized"
    if screen_width_px and screen_height_px:
        return "pixels"
    return "native"


def _screen_bounds(
    mode: str,
    screen_width_px: float | None,
    screen_height_px: float | None,
) -> tuple[float, float, float, float] | None:
    if mode == "normalized":
        return (0.0, 1.0, 0.0, 1.0)
    if mode == "pixels" and screen_width_px and screen_height_px:
        return (0.0, float(screen_width_px), 0.0, float(screen_height_px))
    return None


def recommended_velocity_threshold(mode: str) -> float:
    """Operational Studio starting point; researchers must verify protocol-specific thresholds."""
    if mode == "normalized":
        return 2.0
    if mode == "pixels":
        return 1000.0
    return 2.0


def validate_aoi_definitions(definitions: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(definitions, pd.DataFrame) or definitions.empty:
        raise ValueError("AOI definitions must contain at least one rectangular AOI.")
    out = definitions.copy()
    label = next((c for c in ["aoi", "AOI", "aoi_label", "label", "name"] if c in out.columns), None)
    if label is None:
        raise ValueError("AOI definitions require a label column named aoi, AOI, aoi_label, label, or name.")
    required = ["xmin", "xmax", "ymin", "ymax"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError("Rectangular AOI definitions are missing: " + ", ".join(missing))
    for column in required:
        out[column] = pd.to_numeric(out[column], errors="coerce")
        if out[column].isna().any():
            raise ValueError(f"AOI column `{column}` must contain finite numeric coordinates.")
    if (out["xmin"] >= out["xmax"]).any() or (out["ymin"] >= out["ymax"]).any():
        raise ValueError("Every AOI must satisfy xmin < xmax and ymin < ymax.")
    out["aoi"] = out[label].astype(str)
    if (out["aoi"].str.strip() == "").any():
        raise ValueError("AOI labels cannot be empty.")
    columns = ["aoi", "xmin", "xmax", "ymin", "ymax"]
    if "priority" in out.columns:
        out["priority"] = pd.to_numeric(out["priority"], errors="coerce")
        columns.append("priority")
    return out[columns].reset_index(drop=True)


def load_aoi_definitions(file_info: list[dict[str, Any]] | None) -> tuple[pd.DataFrame, str]:
    if not file_info:
        raise ValueError("Choose an AOI definition CSV/TXT file first.")
    if len(file_info) != 1:
        raise ValueError("Upload exactly one AOI definition file.")
    info = file_info[0]
    name = str(info.get("name") or "aoi_definitions.csv")
    suffix = Path(name).suffix.lower()
    if suffix not in AOI_UPLOAD_SUFFIXES:
        raise ValueError("AOI definitions must be CSV or TXT.")
    size = info.get("size")
    if size is not None and int(size) > MAX_AOI_UPLOAD_BYTES:
        raise ValueError("The AOI definition file exceeds the 5 MB Studio limit.")
    datapath = info.get("datapath")
    if not datapath:
        raise ValueError("The AOI upload did not provide a readable temporary path.")
    if suffix == ".txt":
        definitions = pd.read_csv(datapath, sep=None, engine="python")
    else:
        definitions = pd.read_csv(datapath)
    return validate_aoi_definitions(definitions), name


def run_gaze_analysis(
    data: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    time_col: str,
    validity_col: str | None = None,
    group_col: str | None = None,
    trial_col: str | None = None,
    coordinate_system: str = "auto",
    screen_width_px: float | None = None,
    screen_height_px: float | None = None,
    expected_sampling_rate_hz: float = 60.0,
    missing_threshold: float = 0.20,
    filter_to_screen: bool = True,
    detect_events: bool = True,
    velocity_threshold: float | None = None,
    min_fixation_duration_ms: float = 100.0,
    min_saccade_duration_ms: float = 10.0,
    max_gap_ms: float = 100.0,
    existing_aoi_col: str | None = None,
    aoi_definitions: pd.DataFrame | None = None,
    aoi_overlap: str = "priority",
    aoi_boundary: str = "inside",
    min_saccade_distance: float = 0.02,
) -> dict[str, Any]:
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise ValueError("Gaze analysis requires a non-empty data frame.")
    for column, label in [(x_col, "gaze x"), (y_col, "gaze y"), (time_col, "time")]:
        if not column or column not in data.columns:
            raise ValueError(f"Selected {label} column was not found in the dataset.")
        if not pd.api.types.is_numeric_dtype(data[column]):
            raise TypeError(f"Selected {label} column must be numeric.")
    for column, label in [(validity_col, "validity"), (group_col, "group"), (trial_col, "trial"), (existing_aoi_col, "AOI")]:
        if column is not None and column not in data.columns:
            raise ValueError(f"Selected {label} column was not found in the dataset.")
    if coordinate_system not in {"auto", "normalized", "pixels"}:
        raise ValueError("Coordinate system must be auto, normalized, or pixels.")
    if expected_sampling_rate_hz <= 0:
        raise ValueError("Expected sampling rate must be positive.")
    if not 0 <= missing_threshold <= 1:
        raise ValueError("Missingness threshold must be between zero and one.")
    if min_fixation_duration_ms <= 0 or min_saccade_duration_ms <= 0 or max_gap_ms < 0:
        raise ValueError("Gaze event duration parameters must be positive, with a non-negative gap limit.")
    if min_saccade_distance < 0:
        raise ValueError("Minimum scanpath saccade distance must be non-negative.")
    if aoi_overlap not in {"priority", "smallest", "all", "error"}:
        raise ValueError("AOI overlap must be priority, smallest, all, or error.")
    if aoi_boundary not in {"inside", "outside"}:
        raise ValueError("AOI boundary rule must be inside or outside.")

    groups = _group_cols(group_col, trial_col)
    mode = _coordinate_mode(data, x_col, y_col, coordinate_system, screen_width_px, screen_height_px)
    validate_coordinate = coordinate_system if coordinate_system != "auto" else "auto"
    validation_kwargs: dict[str, Any] = {
        "time_col": time_col,
        "x_col": x_col,
        "y_col": y_col,
        "group_cols": groups or None,
        "coordinate_system": validate_coordinate,
        "expected_sampling_rate_hz": float(expected_sampling_rate_hz),
        "missing_threshold": float(missing_threshold),
    }
    if validity_col:
        validation_kwargs["validity_cols"] = [validity_col]
    if screen_width_px:
        validation_kwargs["screen_width_px"] = float(screen_width_px)
    if screen_height_px:
        validation_kwargs["screen_height_px"] = float(screen_height_px)
    if str(time_col).lower() in {"cnt", "sample", "sample_index", "index"}:
        validation_kwargs["sampling_rate_hz"] = float(expected_sampling_rate_hz)
    validation = gp.validate_gazepoint_gaze(data, **validation_kwargs)

    result: dict[str, Any] = {"validation": validation}
    working = data.copy()
    analysis_x, analysis_y = x_col, y_col
    bounds = _screen_bounds(mode, screen_width_px, screen_height_px)
    if filter_to_screen and bounds is not None:
        working = gp.filter_gazepoint_gaze(
            working,
            x_col=x_col,
            y_col=y_col,
            time_col=time_col,
            group_cols=groups or None,
            screen_bounds=bounds,
            max_velocity=np.inf,
            drop_invalid=False,
            suffix="_studio_filtered",
        )
        analysis_x = f"{x_col}_studio_filtered"
        analysis_y = f"{y_col}_studio_filtered"
        result["filtered_data"] = working.copy()

    event_result: dict[str, Any] | None = None
    if detect_events:
        threshold = float(velocity_threshold) if velocity_threshold is not None else recommended_velocity_threshold(mode)
        if threshold <= 0:
            raise ValueError("Velocity threshold must be positive.")
        time_unit = "samples" if str(time_col).lower() in {"cnt", "sample", "sample_index", "index"} else "auto"
        event_result = gp.detect_gazepoint_fixations(
            working,
            time_col=time_col,
            x_col=analysis_x,
            y_col=analysis_y,
            group_cols=groups or None,
            valid_col=validity_col,
            valid_values=(1, True),
            time_unit=time_unit,
            sampling_rate_hz=float(expected_sampling_rate_hz) if time_unit == "samples" else None,
            coordinate_unit=mode if mode in {"normalized", "pixels"} else "native",
            velocity_threshold=threshold,
            min_fixation_duration_ms=float(min_fixation_duration_ms),
            min_saccade_duration_ms=float(min_saccade_duration_ms),
            max_gap_ms=float(max_gap_ms),
        )
        result["gaze_events"] = event_result
        working = event_result["samples"].copy()
        fixations = event_result.get("fixations")
        if isinstance(fixations, pd.DataFrame) and not fixations.empty:
            result["fixation_summary"] = gp.summarize_gazepoint_fixations(
                fixations,
                duration_col="duration_ms",
                x_col="mean_x",
                y_col="mean_y",
                group_cols=groups or None,
                duration_unit="milliseconds",
            )

    aoi_col = existing_aoi_col
    definitions = validate_aoi_definitions(aoi_definitions) if aoi_definitions is not None else None
    if definitions is not None:
        priority_col = "priority" if "priority" in definitions.columns else None
        working = gp.assign_gazepoint_aoi(
            working,
            definitions,
            x_col=analysis_x,
            y_col=analysis_y,
            aoi_label_col="aoi",
            format="rectangle",
            priority_col=priority_col,
            overlap=aoi_overlap,
            boundary=aoi_boundary,
            output_col="Studio_AOI",
        )
        aoi_col = "Studio_AOI"
        result["aoi_definitions"] = definitions.copy()
        result["aoi_assignment_log"] = working.attrs.get("aoi_assignment_log")
        if event_result is not None:
            fixations = event_result.get("fixations")
            if isinstance(fixations, pd.DataFrame) and not fixations.empty:
                fixations_aoi = gp.assign_gazepoint_aoi(
                    fixations,
                    definitions,
                    x_col="mean_x",
                    y_col="mean_y",
                    aoi_label_col="aoi",
                    format="rectangle",
                    priority_col=priority_col,
                    overlap=aoi_overlap,
                    boundary=aoi_boundary,
                    output_col="Studio_AOI",
                )
                result["fixations_with_aoi"] = fixations_aoi
                result["fixations_by_aoi"] = gp.summarise_gazepoint_fixations_by_aoi(
                    fixations_aoi,
                    aoi_col="Studio_AOI",
                    group_cols=groups or None,
                    start_col="start_time",
                    duration_col="duration_ms",
                    time_unit="auto",
                    duration_unit="milliseconds",
                    sampling_rate_hz=float(expected_sampling_rate_hz),
                    include_unassigned=True,
                )

    if aoi_col and aoi_col in working.columns:
        valid_col = "gaze_valid" if "gaze_valid" in working.columns else validity_col
        result["aoi_dwell"] = gp.summarize_gazepoint_aoi_dwell(
            working,
            time_col=time_col,
            aoi_col=aoi_col,
            group_cols=groups or None,
            valid_col=valid_col,
        )

    result["scanpath"] = gp.summarize_gazepoint_scanpath_metrics(
        working,
        x_col=analysis_x,
        y_col=analysis_y,
        time_col=time_col,
        aoi_col=aoi_col if aoi_col and aoi_col in working.columns else None,
        group_cols=groups or None,
        min_saccade_distance=float(min_saccade_distance),
    )
    result["processed_data"] = working
    result["analysis_x_col"] = analysis_x
    result["analysis_y_col"] = analysis_y
    result["analysis_aoi_col"] = aoi_col
    result["coordinate_mode"] = mode
    result["screen_bounds"] = bounds
    result["parameters"] = {
        "x_col": x_col,
        "y_col": y_col,
        "time_col": time_col,
        "validity_col": validity_col,
        "group_col": group_col,
        "trial_col": trial_col,
        "coordinate_system": coordinate_system,
        "resolved_coordinate_mode": mode,
        "screen_width_px": screen_width_px,
        "screen_height_px": screen_height_px,
        "expected_sampling_rate_hz": float(expected_sampling_rate_hz),
        "missing_threshold": float(missing_threshold),
        "filter_to_screen": bool(filter_to_screen),
        "detect_events": bool(detect_events),
        "velocity_threshold": float(velocity_threshold) if velocity_threshold is not None else recommended_velocity_threshold(mode),
        "min_fixation_duration_ms": float(min_fixation_duration_ms),
        "min_saccade_duration_ms": float(min_saccade_duration_ms),
        "max_gap_ms": float(max_gap_ms),
        "existing_aoi_col": existing_aoi_col,
        "aoi_definition_rows": int(len(definitions)) if definitions is not None else 0,
        "aoi_overlap": aoi_overlap,
        "aoi_boundary": aoi_boundary,
        "min_saccade_distance": float(min_saccade_distance),
        "analysis_x_col": analysis_x,
        "analysis_y_col": analysis_y,
        "analysis_aoi_col": aoi_col,
    }
    return result


def gaze_analysis_tables(result: dict[str, Any] | None) -> dict[str, pd.DataFrame]:
    if not result:
        return {}
    tables: dict[str, pd.DataFrame] = {}
    validation = result.get("validation")
    if isinstance(validation, dict):
        for source, target in [("summary", "validation_summary"), ("groups", "validation_groups"), ("group_summary", "validation_groups"), ("issues", "validation_issues")]:
            value = validation.get(source)
            if isinstance(value, pd.DataFrame):
                tables[target] = value.copy()
    events = result.get("gaze_events")
    if isinstance(events, dict):
        for source, target in [("summary", "event_summary"), ("fixations", "fixations"), ("saccades", "saccades")]:
            value = events.get(source)
            if isinstance(value, pd.DataFrame):
                tables[target] = value.copy()
    for source, target in [
        ("fixation_summary", "fixation_summary"),
        ("fixations_by_aoi", "fixations_by_aoi"),
        ("aoi_dwell", "aoi_dwell"),
        ("scanpath", "scanpath"),
        ("aoi_definitions", "aoi_definitions"),
    ]:
        value = result.get(source)
        if isinstance(value, pd.DataFrame):
            tables[target] = value.copy()
    log = result.get("aoi_assignment_log")
    if isinstance(log, dict):
        overview = log.get("overview")
        if isinstance(overview, pd.DataFrame):
            tables["aoi_assignment_overview"] = overview.copy()
    return tables


def gaze_reproducibility_script(result: dict[str, Any] | None) -> str:
    if not result:
        return "# Run Gaze / Fixation / Saccade / AOI Analysis to generate reproducible code.\n"
    p = result.get("parameters") or {}
    groups = [c for c in [p.get("group_col"), p.get("trial_col")] if c]
    group_expr = repr(groups) if groups else "None"
    lines = [
        "import numpy as np",
        "import pandas as pd",
        "import gpbiometricspy as gp",
        "",
        'data = gp.import_gazepoint_biometrics("your_gazepoint_export.csv")',
        "",
        "validation = gp.validate_gazepoint_gaze(",
        "    data,",
        f"    time_col={p.get('time_col')!r}, x_col={p.get('x_col')!r}, y_col={p.get('y_col')!r},",
        f"    validity_cols={([p.get('validity_col')] if p.get('validity_col') else None)!r},",
        f"    group_cols={group_expr}, coordinate_system={p.get('coordinate_system')!r},",
        f"    screen_width_px={p.get('screen_width_px')!r}, screen_height_px={p.get('screen_height_px')!r},",
        f"    expected_sampling_rate_hz={p.get('expected_sampling_rate_hz')!r}, missing_threshold={p.get('missing_threshold')!r},",
        ")",
        "working = data.copy()",
    ]
    if p.get("filter_to_screen") and result.get("screen_bounds") is not None:
        lines.extend([
            "working = gp.filter_gazepoint_gaze(",
            "    working,",
            f"    x_col={p.get('x_col')!r}, y_col={p.get('y_col')!r}, time_col={p.get('time_col')!r}, group_cols={group_expr},",
            f"    screen_bounds={result.get('screen_bounds')!r}, max_velocity=np.inf, drop_invalid=False, suffix='_studio_filtered',",
            ")",
        ])
    if p.get("detect_events"):
        time_unit = "samples" if str(p.get("time_col", "")).lower() in {"cnt", "sample", "sample_index", "index"} else "auto"
        lines.extend([
            "events = gp.detect_gazepoint_fixations(",
            "    working,",
            f"    time_col={p.get('time_col')!r}, x_col={p.get('analysis_x_col')!r}, y_col={p.get('analysis_y_col')!r},",
            f"    group_cols={group_expr}, valid_col={p.get('validity_col')!r}, valid_values=(1, True),",
            f"    time_unit={time_unit!r}, sampling_rate_hz={(p.get('expected_sampling_rate_hz') if time_unit == 'samples' else None)!r},",
            f"    coordinate_unit={p.get('resolved_coordinate_mode')!r}, velocity_threshold={p.get('velocity_threshold')!r},",
            f"    min_fixation_duration_ms={p.get('min_fixation_duration_ms')!r}, min_saccade_duration_ms={p.get('min_saccade_duration_ms')!r},",
            f"    max_gap_ms={p.get('max_gap_ms')!r},",
            ")",
            "working = events['samples']",
        ])
    if p.get("aoi_definition_rows", 0):
        lines.extend([
            "aoi_definitions = pd.read_csv('your_aoi_definitions.csv')",
            "working = gp.assign_gazepoint_aoi(",
            "    working, aoi_definitions,",
            f"    x_col={p.get('analysis_x_col')!r}, y_col={p.get('analysis_y_col')!r}, aoi_label_col='aoi',",
            f"    format='rectangle', overlap={p.get('aoi_overlap')!r}, boundary={p.get('aoi_boundary')!r}, output_col='Studio_AOI',",
            ")",
        ])
    aoi_col = p.get("analysis_aoi_col")
    if aoi_col:
        lines.extend([
            "aoi_dwell = gp.summarize_gazepoint_aoi_dwell(",
            f"    working, time_col={p.get('time_col')!r}, aoi_col={aoi_col!r}, group_cols={group_expr},",
            ")",
        ])
    lines.extend([
        "scanpath = gp.summarize_gazepoint_scanpath_metrics(",
        f"    working, x_col={p.get('analysis_x_col')!r}, y_col={p.get('analysis_y_col')!r}, time_col={p.get('time_col')!r},",
        f"    aoi_col={aoi_col!r}, group_cols={group_expr}, min_saccade_distance={p.get('min_saccade_distance')!r},",
        ")",
    ])
    return "\n".join(lines) + "\n"
