"""Presentation-only analysis presets and teaching routes for Studio.

The objects in this module document existing Studio guided defaults and workflow
boundaries. They never call scientific functions, mutate Shiny inputs, run an
analysis, or infer psychological states from biometric or gaze measurements.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisPreset:
    """Researcher-facing description of one existing Studio workflow baseline."""

    key: str
    module_key: str
    label: str
    goal: str
    guided_defaults: tuple[str, ...]
    prerequisites: tuple[str, ...]
    verify_before_inference: tuple[str, ...]
    guardrail: str
    next_step: str


@dataclass(frozen=True)
class TeachingRoute:
    """A non-executing teaching narrative across existing Studio modules."""

    key: str
    label: str
    goal: str
    route: tuple[str, ...]
    evidence_focus: str
    stop_and_check: str


_PRESETS = (
    AnalysisPreset(
        key="eda-foundations",
        module_key="eda_scr",
        label="EDA/SCR foundations",
        goal="Learn the package-backed decomposition and candidate-SCR workflow before introducing protocol-specific expert choices.",
        guided_defaults=(
            "Guided workflow mode",
            "Tonic window: 31 samples",
            "Automatic SCR threshold",
            "Minimum peak distance: 10 samples",
        ),
        prerequisites=(
            "Load a dataset with a supported EDA/GSR signal",
            "Run foundation QC and review signal quality",
            "Confirm the selected time and grouping columns match the study design",
        ),
        verify_before_inference=(
            "Event timing and analysis window are appropriate for the protocol",
            "Decomposition and SCR-threshold choices are justified or sensitivity-checked",
            "Artifacts and group structure have been reviewed",
        ),
        guardrail=(
            "EDA/SCR features quantify electrodermal signal characteristics; they do not by themselves identify emotion, stress, trust, preference, cognition, or diagnosis."
        ),
        next_step="For event-locked questions, establish Events & Alignment before combining EDA with other modalities.",
    ),
    AnalysisPreset(
        key="cardiac-foundations",
        module_key="ppg_hr_hrv",
        label="PPG / HR / HRV foundations",
        goal="Learn the supported pulse, heart-rate, IBI-quality and HRV workflow with conservative visible quality limits.",
        guided_defaults=(
            "Guided workflow mode",
            "Heart-rate bounds: 40–180 bpm",
            "RR rejection tolerance: 0.30",
            "IBI limits: 300–2000 ms; maximum jump: 500 ms",
            "No spline peak refinement or optional external-style cross-checks",
        ),
        prerequisites=(
            "Load a supported PPG waveform, heart-rate series, or genuine IBI/RR series",
            "Run foundation QC and review the available cardiac signal family",
            "Confirm sampling rate and time base",
        ),
        verify_before_inference=(
            "IBIs are genuine beat-to-beat intervals or derive from accepted pulse peaks",
            "Segment duration, stationarity and artifact handling support the intended HRV claim",
            "Frequency-domain outputs are treated cautiously for short or sparse recordings",
        ),
        guardrail=(
            "Cardiac and HRV features are physiological measurements; Studio does not convert them into direct evidence of stress, emotion, trust, preference, cognition, or diagnosis."
        ),
        next_step="Use event alignment or multimodal integration only after the cardiac signal and timing assumptions are defensible.",
    ),
    AnalysisPreset(
        key="pupil-foundations",
        module_key="pupil",
        label="Pupil preprocessing foundations",
        goal="Start with visible pupil-quality and blink-gap diagnostics before optional interpolation, smoothing, baseline correction, or event summaries.",
        guided_defaults=(
            "Guided workflow mode",
            "Minimum blink-like gap: 2 samples",
            "No interpolation",
            "No smoothing",
            "No automatic baseline correction or event-response summary",
        ),
        prerequisites=(
            "Load a supported pupil channel and time column",
            "Run foundation QC",
            "Review validity information and missing/blink-like gaps",
        ),
        verify_before_inference=(
            "Interpolation and smoothing, if enabled later, are justified by acquisition quality",
            "Baseline windows use the selected time units and precede the task event appropriately",
            "Trial/event structure matches the research design",
        ),
        guardrail=(
            "Pupil size and derived responses require contextual experimental interpretation; they are not standalone measures of cognitive load, arousal, emotion, trust, preference, or diagnosis."
        ),
        next_step="Continue to Gaze/AOI for spatial eye-movement questions, or to Events & Alignment for task-locked multimodal analysis.",
    ),
    AnalysisPreset(
        key="gaze-foundations",
        module_key="gaze",
        label="Gaze, fixation and saccade foundations",
        goal="Learn coordinate validation and package-backed fixation/saccade diagnostics before tuning acquisition-specific event thresholds or AOIs.",
        guided_defaults=(
            "Guided workflow mode with automatic coordinate-system handling",
            "Screen-bound filtering enabled",
            "Event detection enabled",
            "Minimum fixation: 100 ms; minimum saccade: 10 ms",
            "Maximum event gap: 100 ms with a coordinate-dependent velocity starting point",
        ),
        prerequisites=(
            "Load supported gaze X/Y and time columns",
            "Run foundation QC and review validity/screen-bound behavior",
            "Confirm screen geometry and coordinate units when relevant",
        ),
        verify_before_inference=(
            "Velocity and duration thresholds match the tracker, sampling rate and task",
            "AOI definitions are preregistered or otherwise justified",
            "Trial/group structure is appropriate for aggregation and inference",
        ),
        guardrail=(
            "Fixations, saccades, scanpaths and AOI dwell describe observable eye-movement behavior; they do not uniquely reveal attention, preference, emotion, trust, cognition, or diagnosis."
        ),
        next_step="Use Events & Alignment when temporal task anchors are needed before multimodal or event-locked comparison.",
    ),
    AnalysisPreset(
        key="event-alignment-foundations",
        module_key="event_alignment",
        label="Event and stream alignment foundations",
        goal="Establish an auditable event clock before extracting event windows or combining independently timed streams.",
        guided_defaults=(
            "Guided workflow mode",
            "TTL / marker column as the default reference source",
            "Pre-event window: 1.0 s; post-event window: 5.0 s",
            "TTL extraction audit: value changes; alignment edge: rising",
            "Nearby-event collapse: 0 ms; second-stream alignment off",
        ),
        prerequisites=(
            "Run foundation QC",
            "Confirm a reference time column",
            "Provide a supported TTL/marker source or an explicit external event log",
        ),
        verify_before_inference=(
            "Clock units, event edges and duplicate/collapse behavior match the acquisition protocol",
            "External event/resource identity is correct and fingerprint checks are not bypassed",
            "Any second stream has defensible shared anchors and alignment diagnostics",
        ),
        guardrail=(
            "Temporal alignment establishes comparable event coordinates; it does not make different sensors equivalent or validate downstream causal/psychological interpretations."
        ),
        next_step="Proceed to Multimodal only after the standardized event table and any required stream alignment have been reviewed.",
    ),
    AnalysisPreset(
        key="multimodal-foundations",
        module_key="multimodal",
        label="Event-linked multimodal foundations",
        goal="Combine already defensible signal streams on a shared event clock while keeping each modality's preprocessing source visible.",
        guided_defaults=(
            "Guided workflow mode",
            "Prefer prior processed Studio analyses when compatible",
            "Pre-event window: 1.0 s; post-event window: 3.0 s",
            "Baseline window: -1.0 to 0.0 s; summary window: 0.0 to 3.0 s",
            "Timeline standardisation enabled for visualization",
        ),
        prerequisites=(
            "Run foundation QC",
            "Complete Events & Alignment",
            "Select at least the defensible modalities required by the research question",
        ),
        verify_before_inference=(
            "Each modality's preprocessing, artifacts and sampling properties have been reviewed independently",
            "Baseline and summary windows are physiologically and task appropriate for each measure",
            "Standardised timeline display is not mistaken for physiological equivalence",
        ),
        guardrail=(
            "A shared event clock enables joint description and modelling; it does not imply that EDA, cardiac, pupil and gaze measures share the same response dynamics or psychological meaning."
        ),
        next_step="Use the Model workspace only when the research question and design justify a specific inferential model; otherwise continue to Reporting.",
    ),
    AnalysisPreset(
        key="model-preparation-foundations",
        module_key="statistics_modelling",
        label="Model-data preparation",
        goal="Build an auditable complete-case model table and formula specification before fitting an inferential model outside the preparation workspace.",
        guided_defaults=(
            "Guided model-preparation mode",
            "Source/outcome/design columns selected from available Studio result tables",
            "No automatic covariates, baseline correction or continuous-term scaling",
            "Minimum complete rows: 10",
        ),
        prerequisites=(
            "Complete the signal/alignment workflow that produces the intended source table",
            "Define the outcome, design predictors and participant/trial structure from the study design",
        ),
        verify_before_inference=(
            "The generated formula matches the preregistered or theoretically justified model",
            "Missingness, factor coding, random-effect structure and assumptions are evaluated in the chosen model fitter",
            "A prepared table/formula is not described as a fitted model",
        ),
        guardrail="Studio model preparation documents the design specification; it is not evidence that a model was fitted, valid, significant, or causally interpretable.",
        next_step="Fit and diagnose the intended model with an appropriate validated modelling tool, or use the supported cluster workflow only for its exact validated design.",
    ),
    AnalysisPreset(
        key="cluster-permutation-foundations",
        module_key="statistics_modelling",
        label="Cluster-permutation starter",
        goal="Learn the validated two-condition within-subject one-dimensional time-course permutation workflow with package-native design diagnostics.",
        guided_defaults=(
            "Guided cluster mode",
            "Time bin width: 0.1; within-cell aggregation: mean",
            "Diagnostic participant target: 10",
            "Permutations: 1000; cluster-forming alpha: 0.05; cluster alpha: 0.05",
            "Two-sided test; seed: 2026; threshold-sensitivity analysis off",
        ),
        prerequisites=(
            "Use a repeated-measures time-course source with participant, condition, time and numeric outcome columns",
            "Exactly two conditions must be represented on a defensible common one-dimensional time grid",
            "Package-native grid/design diagnostics must pass before permutations run",
        ),
        verify_before_inference=(
            "The within-subject sign-flip design matches the experiment",
            "Time binning/aggregation and cluster-forming threshold are justified",
            "Cluster boundaries are treated as descriptive rather than precise onset/offset estimates",
        ),
        guardrail="A significant cluster is cluster-level evidence against the tested global null; it does not validate unsupported designs or provide precise effect-onset/offset estimates.",
        next_step="Export the cluster tables, package-native statement and reproducibility script together with the design diagnostics.",
    ),
)


_TEACHING_ROUTES = (
    TeachingRoute(
        key="physiology",
        label="Physiology foundations",
        goal="Learn signal quality before derived EDA and cardiac features.",
        route=("Foundation QC", "EDA / SCR", "PPG / HR / HRV", "Reporting"),
        evidence_focus="Signal quality, decomposition/peak evidence, IBI/HRV validity and reproducible parameters.",
        stop_and_check="Do not translate physiological changes directly into stress, emotion or other psychological states.",
    ),
    TeachingRoute(
        key="eye_tracking",
        label="Eye-tracking foundations",
        goal="Separate pupil preprocessing from spatial gaze/fixation/AOI analysis.",
        route=("Foundation QC", "Pupil", "Gaze / Fixation / AOI", "Reporting"),
        evidence_focus="Validity/missingness, pupil preprocessing, coordinate quality, event detection and AOI definitions.",
        stop_and_check="Do not treat pupil or gaze metrics as unique readouts of attention, cognition, preference or emotion.",
    ),
    TeachingRoute(
        key="multimodal",
        label="Event-linked multimodal workflow",
        goal="Make timing explicit before combining heterogeneous measures.",
        route=("Foundation QC", "Events & Alignment", "Multimodal", "Reporting"),
        evidence_focus="Event identity, clock alignment, modality-specific preprocessing sources, baseline/summary windows and provenance.",
        stop_and_check="A shared clock enables comparison but does not make modalities physiologically equivalent.",
    ),
    TeachingRoute(
        key="modelling",
        label="From measurements to a defensible model",
        goal="Prepare analysis-ready tables without overclaiming what Studio has fitted or tested.",
        route=("Signal / integration workflow", "Model preparation or validated cluster permutation", "Diagnostics", "Reporting"),
        evidence_focus="Outcome/design roles, complete cases, random/group structure, common time grid and inferential assumptions.",
        stop_and_check="Use cluster permutation only for the validated two-condition within-subject one-dimensional design; model preparation is not model fitting.",
    ),
)


SUPPORTED_PRESET_MODULES = frozenset(preset.module_key for preset in _PRESETS)


def analysis_presets() -> tuple[AnalysisPreset, ...]:
    """Return all immutable Studio teaching presets."""

    return _PRESETS


def presets_for_module(module_key: str) -> tuple[AnalysisPreset, ...]:
    """Return documented presets for one Studio module key."""

    key = str(module_key or "").strip()
    matches = tuple(preset for preset in _PRESETS if preset.module_key == key)
    if not matches:
        allowed = ", ".join(sorted(SUPPORTED_PRESET_MODULES))
        raise ValueError(f"Unsupported Studio preset module {key!r}. Allowed values: {allowed}.")
    return matches


def preset_by_key(key: str) -> AnalysisPreset:
    """Resolve one preset by stable key."""

    value = str(key or "").strip()
    for preset in _PRESETS:
        if preset.key == value:
            return preset
    allowed = ", ".join(preset.key for preset in _PRESETS)
    raise ValueError(f"Unknown Studio analysis preset {value!r}. Allowed values: {allowed}.")


def teaching_routes() -> tuple[TeachingRoute, ...]:
    """Return non-executing teaching narratives for the product Home screen."""

    return _TEACHING_ROUTES
