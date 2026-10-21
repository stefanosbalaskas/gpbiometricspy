# From cleaner signals to scientifically better measurements

![Rendered synthetic plot](../assets/october-2026-plot.svg)

**Research implementation, 21 October 2026 — not a validated device benchmark or released API.**

![Three independent validation levels](../assets/october-2026-physiology.svg)

The two experimental helpers under `research/october_2026/physiological_validation.py` distinguish measurement-level validity from participant-level inferential stability. The original illustration represents three deliberately separate estimands. None is interchangeable with the others.

## Reproducible example

~~~python
import numpy as np
import pandas as pd
from research.october_2026.physiological_validation import baseline_stability_audit, preprocessing_to_inference_audit

baseline = pd.DataFrame({
    "participant_id": ["P1"] * 8 + ["P2"] * 8,
    "time_s": list(range(8)) * 2,
    "value": list(np.linspace(1.0, 1.2, 8)) + [1.1] * 8,
})
print(baseline_stability_audit(baseline).to_string(index=False))
~~~

An observed baseline is not necessarily a stable baseline. Slopes, early/late changes and missingness describe the actual reference interval; no fixed stability cutoff is imposed.

## Participant-level difference plot

The following code draws an **original synthetic demonstration**, not empirical EDA outcomes:

~~~python
import matplotlib.pyplot as plt
participants = ["P1", "P2", "P3"]
raw_error = [0.50, 0.58, 0.46]
processed_error = [0.20, 0.30, 0.29]
fig, ax = plt.subplots(figsize=(6, 3))
for i, participant in enumerate(participants):
    ax.plot([0, 1], [raw_error[i], processed_error[i]], marker="o", label=participant)
ax.set_xticks([0, 1], ["Raw", "Processed"])
ax.set_ylabel("Synthetic waveform absolute error")
ax.legend(title="Independent unit")
fig.tight_layout()
~~~

The complete matched three-layer input requires signal reference, binary event labels on a common grid and separately estimated participant effects. Changes are bootstrapped by participant, not by time sample. Event-label error is not event-onset precision; scientific equivalence requires additional evidence.

## Qualification checklist

- Reproduce known-truth waveform and event recovery independently.
- Evaluate event onset and SCR amplitude with an expert reference set.
- Check bias, construct responsiveness and condition effects before and after preprocessing.
- Quantify participant-level uncertainty and negative outcomes.
- Validate stabilization procedures by modality; a cardiovascular protocol is not automatically an EDA or pupil standard.

**Status:** implementation and synthetic unit tests submitted for review; externally benchmarked clinical or scientific validity is not claimed.


## External classifier validation and sensor ablations

The complementary experimental module `research/october_2026/external_validation.py` checks explicit participant- and dataset-identity disjointness. It reports locked-threshold precision, recall, F1, balanced accuracy, average precision, external class prevalence, and whole-participant bootstrap intervals. It consumes supplied frozen predictions; it cannot prove that the model or threshold really was frozen.

~~~python
import pandas as pd
from research.october_2026.external_validation import (
    external_classifier_validation, modality_ablation_audit,
)
rows = pd.DataFrame({
    "participant_id": ["A", "A", "B", "B", "C", "C"],
    "dataset_id": ["external"] * 6,
    "outcome": [0, 1] * 3,
    "probability": [.1, .9] * 3,
    "full_probability": [.1, .9] * 3,
    "ablated_probability": [.1, .4] * 3,
})
external = external_classifier_validation(
    rows, training_participants=["development_subject"],
    training_datasets=["development"], locked_threshold=0.5,
)
ablation = modality_ablation_audit(rows)
print(external["metrics"], ablation["delta_balanced_accuracy"])
~~~

![Synthetic modality-ablation metric comparison](../assets/october-2026-modality-ablation.svg)

Both the external classifier and ablation checks are **descriptive research diagnostics**. A statistically meaningful between-modality difference requires prespecified endpoints, valid independent participant units, adequate sample size and external domain evidence. The example is synthetic and establishes no sensor complementarity.


## Clock synchronization versus event timing

The experimental `synchronization_validation.py` reports participant/session-specific affine or offset clock mapping from matched anchors **and separately** evaluates events that were not used as anchors. Low anchor residuals are not sufficient evidence of low event error.

![Independent validation of clock versus event timing](../assets/october-2026-clock.svg)

~~~python
import pandas as pd
from research.october_2026.synchronization_validation import audit_clock_and_event_alignment
anchors = pd.DataFrame({
    "participant_id": ["P"]*4, "session_id":["S"]*4,
    "device_time_s":[1,2,3,4], "reference_time_s":[1.1,2.1,3.1,4.1],
})
events = pd.DataFrame({
    "participant_id":["P"]*2, "session_id":["S"]*2,
    "device_event_time_s":[1.5,3.5], "reference_event_time_s":[1.6,3.6],
})
audit = audit_clock_and_event_alignment(anchors, events, fit="affine")
print(audit["clock_fits"], audit["independent_event_errors"])
~~~

The illustration depicts synthetic clocks. Anchor/event independence must be verified from acquisition metadata in empirical use. Even a near-zero affine residual is not a hardware latency certificate.


## EDABE external evidence intake (not yet executed on the original dataset)

The EDABE benchmark documentation provides raw electrodermal signals, human-edited reference signals and **artifact** labels. Those labels are not independently annotated skin-conductance responses. The research-only `edabe_reference.py` adapter requires original export column names, recording IDs, explicit participant-disjoint train/test labels, and matching timestamps before computing waveform error and artifact-label recall.

**Primary source:** [EDABE dataset record](https://zenodo.org/records/7248135); [EDABE v2 and research use conditions](https://data.mendeley.com/datasets/w8fxrg4pv5/2); [FairEDA public reproducibility materials](https://github.com/rtb-1005/FairEDA). Dataset access/reuse conditions remain the researcher's responsibility. This repository includes only synthetic fixtures, not copyrighted or restricted underlying recordings.

![Synthetic EDABE waveform comparison](../assets/october-2026-edabe-waveform.svg)

~~~python
import pandas as pd
from research.october_2026.edabe_reference import audit_edabe_reference_export
rows = []
for subject, split in [("synthetic-train", "train"), ("synthetic-test", "test")]:
    for time, raw, reference, clean, artifact in [
        (0,1,1,1,0), (1,2,1,1,1), (2,1,1,1,0), (3,2,1,1,1)
    ]:
        rows.append(dict(participant_id=subject, recording_id="trial",
            benchmark_split=split, time=time, rawdata=raw,
            cleandata=reference, signal_automatic=clean,
            binarytarget=artifact, predArtifacts=artifact,
            postProcessedPredArtifacts=artifact))
summary = audit_edabe_reference_export(pd.DataFrame(rows))
print(summary["recording_metrics"])
~~~

**Pending:** obtain properly licensed genuine EDABE data, confirm supplied participant split against the source manifest, compare all algorithms under identical contamination strata, and test SCR/inferential outcomes against separate expert event or experimental references. These results have **not** been computed here.

## AICOS-HAR cross-device validation pathway

[AICOS-HAR v1](https://zenodo.org/records/19452049) contains inertial recordings across devices and placements. A legitimate external HAR evaluation requires sensor/site/device metadata, prespecified activities, leave-device/placement-out splits and provenance-constrained thresholds. This is a proposed **external validation exercise**, not an integration already run and not evidence of eye-tracking or EDA validity. The dataset is approximately 2.5 GB and must be obtained subject to its reuse conditions.


### Baseline-window and device-strata sensitivity

The module now exposes `baseline_window_sensitivity()`, which preserves **every prespecified window**, including those with insufficient valid observations, rather than selecting the window that favors the desired effect. `external_device_placement_strata()` analogously retains all device-by-body-placement cells, records class prevalence and participant counts, and refuses to manufacture performance metrics for cells with inadequate independent evidence. These are validation-design helpers, not results from AICOS-HAR or a recommendation for universal baseline durations.

## Publication and qualification status (21 October 2026)

This page and its original synthetic figures are merged into the GitHub documentation source. The worked research modules are under `research/october_2026/` and **are not automatically included in installed PyPI wheels or exported as stable package APIs**. Their empirical accuracy, device transfer and inferential calibration are not implied by a green CI test or a successful website build.

The explicit outstanding scientific acceptance criteria and eligible real-data benchmarks are tracked in [research-to-release issue #176](https://github.com/stefanosbalaskas/gpbiometricspy/issues/176). This source-only research contribution is separate from the existing stable package version, and a new maintenance release must not claim these experiments as installed features.
