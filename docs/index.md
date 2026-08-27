# gpbiometricspy

`gpbiometricspy` is the Python port of **gpbiometrics 2.0.0**, a Gazepoint-native toolkit for biometric and multimodal eye-tracking research.


## Install

```bash
python -m pip install gpbiometricspy
```

The public package is distributed on [PyPI](https://pypi.org/project/gpbiometricspy/) and requires Python 3.11 or newer.

## Frozen parity contract

- 406 R exports → 406 Python implementations
- frozen R source, Rd help, tests and 26 article sources retained under `reference/`
- synthetic kiosk demo included in the installable package
- test coverage gated at 90% or higher
- conservative physiological interpretation preserved

## Main workflow

```text
Gazepoint exports
  → import/schema audit
  → signal validity + timing/TTL QC
  → EDA / PPG / IBI / pupil / gaze preprocessing
  → event/AOI/multimodal alignment
  → feature extraction + model-ready tables
  → plots, reports, reproducibility and interoperability outputs
```

Start with [Getting started](getting-started.md), explore the [406-function API](api/reference.md), or browse the [26 article companions](articles/index.md).
