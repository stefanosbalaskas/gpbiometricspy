# Citation and archival

`gpbiometricspy` is archived through Zenodo.

<div class="gp-version-note">
<strong>Current citation state:</strong> Python release <code>0.1.8</code> is being frozen on <strong>2026-10-04</strong> from qualified source <code>a75eb1d73791213e6e830ff94975f632455632e2</code>. The software concept DOI remains <strong>10.5281/zenodo.22150872</strong>. A 0.1.8 version DOI will be recorded only after Zenodo genuinely ingests an immutable <code>v0.1.8</code> GitHub release.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used.

- **0.1.8 version DOI:** pending genuine Zenodo ingestion; no DOI is invented before minting.
- **0.1.7 version DOI:** still pending independent Zenodo verification.
- **0.1.6 version DOI:** still pending independent Zenodo verification.
- **0.1.5 version DOI:** **[10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)**
- **0.1.4 version DOI:** **[10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)**
- **0.1.3 version DOI:** **[10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)**
- **0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**

Before `v0.1.8` is actually created, cite the latest public stable release used in the analysis together with the concept DOI. After publication, cite the immutable `v0.1.8` release together with version `0.1.8` until a genuine version DOI is independently verified.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control. The 0.1.8 stable-freeze metadata is pinned to version `0.1.8` and release date `2026-10-04`; its DOI field is deliberately absent before Zenodo minting.

## Published gpbiometrics paper

The peer-reviewed paper describing the original R package is:

> Balaskas, S. **gpbiometrics: An R Package for Reproducible Analysis and Reporting of Gazepoint Biometrics Exports.** *Signals* **2026**, *7*, 86. [https://doi.org/10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

This article documents the R `gpbiometrics` package that provides the scientific and software lineage for `gpbiometricspy`. When an analysis uses the Python package, cite the relevant `gpbiometricspy` software version as well; the R-package article is a related publication rather than a substitute for the Python software citation.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies the 0.1.8 stable-freeze identity and date 2026-10-04; the version DOI is intentionally absent until genuine Zenodo minting.
- `.zenodo.json` identifies software version 0.1.8 and preserves the R-reference provenance relationship.
- `pyproject.toml` retains the software concept DOI and independently verified historical DOI links; no 0.1.7 or 0.1.8 version DOI is invented.
- README and documentation retain prior verified version DOIs for reproducible citation.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
