# Citation and archival

`gpbiometricspy` is archived through Zenodo.

<div class="gp-version-note">
<strong>Current citation state:</strong> stable Python release <code>0.1.6</code> was frozen on <strong>2026-09-11</strong>. The software concept DOI remains <strong>10.5281/zenodo.22150872</strong>. The 0.1.6 version DOI will be recorded only after Zenodo ingests the immutable <code>v0.1.6</code> GitHub release.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used.

- **0.1.6 version DOI:** pending Zenodo ingestion; no DOI is invented before minting.
- **Previous 0.1.5 version DOI:** **[10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)**
- **Earlier 0.1.4 version DOI:** **[10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)**
- **Earlier 0.1.3 version DOI:** **[10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)**
- **Earlier 0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**

Until Zenodo mints the 0.1.6 version DOI, cite the immutable GitHub release together with the version number. After ingestion, the genuine Zenodo version DOI can be added in a post-release metadata closeout without altering the immutable PyPI/GitHub artifacts.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control. The stable release record is pinned to version `0.1.6` and release date `2026-09-11`; its DOI field is deliberately absent before Zenodo minting.

## Published gpbiometrics paper

The peer-reviewed paper describing the original R package is:

> Balaskas, S. **gpbiometrics: An R Package for Reproducible Analysis and Reporting of Gazepoint Biometrics Exports.** *Signals* **2026**, *7*, 86. [https://doi.org/10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

This article documents the R `gpbiometrics` package that provides the scientific and software lineage for `gpbiometricspy`. When an analysis uses the Python package, cite the relevant `gpbiometricspy` software version as well; the R-package article is a related publication rather than a substitute for the Python software citation.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies stable Python release 0.1.6 and release date 2026-09-11; the version DOI is intentionally absent until Zenodo minting.
- `.zenodo.json` identifies software version 0.1.6 and preserves the R-reference provenance relationship.
- `pyproject.toml` exposes the software concept DOI, previous 0.1.5 version DOI, and R-reference DOI in distinct URL roles; `VersionDOI` will be added only after the genuine 0.1.6 DOI exists.
- README and documentation retain prior version DOIs for reproducible citation.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
