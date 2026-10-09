# Experimental physiological measurement-validation protocol

**Research status:** module-scoped development utility, not part of the frozen gpbiometrics R parity surface and not a stable published guarantee.

The 18 September methods briefing distinguished *construct responsiveness* from *convergent reference-device agreement*. These are not interchangeable. The 12 and 24 September briefings additionally distinguished hardware-native sampling from SDK-provided and observed rates.

```python
from gpbiometricspy.methods_briefing_validation import (
    summarize_acquisition_rate_lineage,
    validate_biosignal_measurement,
)

rates = summarize_acquisition_rate_lineage(
    timestamps_s,
    device_native_rate_hz=120, sdk_declared_rate_hz=90,
    analysis_stream_rate_hz=90,
)
evidence = validate_biosignal_measurement(
    paired_data, reference_col="reference_eda",
    candidate_col="wearable_eda",
    participant_col="participant_id", phase_col="phase",
)
```

## Three scientifically separate outputs

1. **Paired agreement** is summarized from participant × phase means (paired rows only). Mean bias and descriptive Bland–Altman limits are *not* confidence limits for repeated-measures agreement or a test of equivalence.
2. **Construct responsiveness** is the within-participant perturbation minus baseline change, separately for reference and candidate.
3. **Recovery** is recovery-phase minus perturbation-phase change for each device. A missing phase leaves that participant out of that specific contrast; paired sample losses are counted.

No stress detection, sensor validity verdict, causal effect, equivalence test, or external generalization follows automatically. For publication, use a preregistered protocol with participant-level uncertainty and appropriately modelled repeated agreement.

The rate-lineage helper makes no claim to read device firmware. The device-native and SDK rates are **user-declared metadata**; timestamp-derived rates are observed evidence. They must not be silently conflated.

See [timebase certification](timebase-provenance.md) and [grouped ordinal boosting](grouped-ordinal-boosting.md).
