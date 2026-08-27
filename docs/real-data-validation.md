# Private real-data validation

Real Gazepoint exports may contain participant data and must not be committed to this public repository.

Use the validator locally with data and output directories outside the repository:

```bash
python scripts/validate_real_data.py /secure/path/gazepoint_exports --output /secure/path/gpbiometricspy-validation
```

For a single CSV file the validator conditionally runs import/schema audit, active-channel detection, readiness, EDA quality/decomposition/SCR detection, PPG peak detection and measures, HRV extraction, pupil cleaning, gaze validation, TTL extraction, multimodal plotting, and aggregate report-bundle generation when the corresponding channels are present. Missing channels are recorded as review/skip states instead of being fabricated. For a directory it runs the package real-data smoke workflow, writes external aggregate reports, and applies the smoke-privacy audit.

The GitHub `private-real-data-validation` workflow intentionally does **not** accept/upload private data on public runners; it documents the safe execution model and compile-checks the CLI.
