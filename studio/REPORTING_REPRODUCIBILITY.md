# Reporting, reproducibility, and project recipes

`gpbiometricspy Studio` treats reporting as part of the scientific workflow rather than as a screenshot/export afterthought. The **Reporting & Reproducibility** workspace composes the public `gpbiometricspy` reporting API, Studio provenance, and a privacy-preserving project recipe.

## Design rule

The scientific package remains authoritative. Studio delegates reporting calculations and templates to public package functions, including:

- `create_gazepoint_biometrics_checklist()`;
- `create_gazepoint_biometrics_methods_text()`;
- `create_gazepoint_biometrics_report()`;
- `create_gazepoint_analysis_manifest()`;
- `create_gazepoint_methods_section()`;
- `create_gazepoint_qc_supplement()`;
- `create_gazepoint_reproducibility_statement()`;
- `export_gazepoint_biometrics_report_bundle()`.

Studio adds only application-level concerns: session provenance, analysis/result inventories, dataset identity, project-recipe serialization, guarded restore, and replay orchestration.

## Reporting workflow

After loading data and running the desired Studio workflows:

1. open **Reporting & Reproducibility**;
2. provide an optional report title/subtitle;
3. choose **Build Report Artifacts**;
4. review the package-native methods text, reproducibility statement, QC/reporting supplement, analysis inventory, result-table catalogue, provenance, and annotations;
5. inspect the reproducibility manifest and replay summary;
6. download individual artifacts or the complete report bundle.

The generated bundle includes report-ready tables and text, a Studio manifest, a project recipe, and a Python replay script. The loaded raw biometric table is intentionally not bundled.

## Dataset fingerprint

Studio computes a deterministic SHA-256 fingerprint from:

- row count;
- ordered column names;
- dtypes;
- pandas row/value hashes, including the index.

The fingerprint identifies the exact in-memory dataset used by the session without serializing its raw values into the project recipe. A changed value, schema, dtype, row order, or index produces a different identity.

## Project recipe: metadata, not data

A Studio project recipe is JSON with schema identifier:

```text
gpbiometricspy-studio-project-recipe
```

The current recipe records:

- schema version and creation time;
- installed `gpbiometricspy` and Python versions;
- dataset SHA-256, dimensions, column names, and dtypes;
- expert annotations;
- Studio provenance and recorded workflow parameters;
- analysis inventory;
- result-table descriptors such as table path, row count, and column count.

It deliberately does **not** include:

- raw biometric rows;
- cached processed sample streams;
- cached analysis-result tables;
- matplotlib figure binaries;
- silently copied external event logs or secondary streams.

The JSON carries explicit `raw_data_included = false` and `analysis_outputs_included = false` flags. Studio refuses recipes that do not satisfy the expected recipe contract.

## Restoring a project

Restoration is intentionally conservative:

1. load the separately managed source Gazepoint dataset into Studio;
2. upload the project-recipe JSON;
3. choose **Validate Recipe**;
4. Studio verifies the recipe schema, privacy flags, source-data presence, and exact dataset SHA-256;
5. only after all checks pass can **Restore Metadata** be used.

A fingerprint mismatch blocks restoration. Studio restores annotations and provenance metadata but intentionally clears cached analysis outputs. Analyses must be recomputed from the source data and recorded parameters.

This avoids a dangerous ambiguity in which a saved GUI project appears reproducible while actually containing stale intermediate results from a different dataset or software state.

## Replay script

The generated Python replay script:

- imports the source file through `gp.import_gazepoint_biometrics()`;
- recomputes the dataset fingerprint and stops on mismatch;
- reconstructs recorded Studio analysis calls using the saved parameter sets;
- reuses prior analysis outputs where a later Studio workflow depends on them;
- creates a package-native reporting checklist and methods text at the end.

External dependencies are not fabricated. If Events & Alignment used an external event log, secondary stream, or another file not embedded in the recipe, the generated script marks that dependency and requires it to be supplied explicitly.

The replay script is an auditable starting point, not a substitute for reviewing the experimental design, acquisition protocol, exclusions, statistical assumptions, or environment differences.

## Downloads

The workspace currently offers:

- `gpbiometricspy_studio_report_bundle.zip`;
- `gpbiometricspy_studio_report.md`;
- `gpbiometricspy_studio_methods.txt`;
- `gpbiometricspy_studio_reproducibility.txt`;
- `gpbiometricspy_studio_manifest.json`;
- `gpbiometricspy_studio_project_recipe.json`;
- `gpbiometricspy_studio_replay.py`.

The report bundle is built in a temporary directory and returned as an in-memory ZIP. Studio does not intentionally write uploaded raw data into application assets or the repository.

## Interpretation guardrail

Reporting does not change the meaning of the measurements. Derived biometric, gaze, pupil, event-locked, and statistical outputs remain measurement and workflow products. They do not by themselves establish emotion, stress, trust, cognition, preference, health status, diagnosis, mechanism, causal response, or precise temporal onset.
