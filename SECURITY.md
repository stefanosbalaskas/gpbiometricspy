# Security and private-data guidance

Do not commit private participant exports, direct identifiers, credentials, device serials, private smoke-test outputs, or institutional data-access tokens to this repository.

The installable package contains synthetic public demo data only. Real-data validation is designed for local or approved private execution with input/output paths outside Git. `scripts/validate_real_data.py` produces aggregate QC/readiness outputs and can create plots/reports in an external directory, but users remain responsible for institutional governance, consent, de-identification and retention rules.

Public bug reports should use synthetic or minimized examples. Never attach identifiable participant physiology or gaze traces to an issue.

Code scanning is performed with CodeQL and dependency updates are monitored by Dependabot. Report software vulnerabilities through GitHub private security reporting when available rather than opening a public issue containing exploit details or sensitive data.
