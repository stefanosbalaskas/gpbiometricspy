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
