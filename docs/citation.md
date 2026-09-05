# Citation and archival

`gpbiometricspy` is archived through the Zenodo GitHub integration.

<div class="gp-version-note">
<strong>Current citation state:</strong> stable Python release <code>0.1.3</code> (2026-09-05); its version-specific Zenodo DOI will be added after Zenodo ingests the GitHub release; the software concept DOI is already registered.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used:

- **0.1.3 version DOI:** pending Zenodo ingestion of the `v0.1.3` GitHub release
- **Previous 0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**

Zenodo recommends the version DOI when citing a specific research artifact version. The concept DOI resolves to the latest version and is appropriate when referring to the evolving software family.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control; the release freeze records 0.1.3 identity and date, and its version DOI will be added after Zenodo mints it.

## Published gpbiometrics paper

The peer-reviewed paper describing the original R package is:

> Balaskas, S. **gpbiometrics: An R Package for Reproducible Analysis and Reporting of Gazepoint Biometrics Exports.** *Signals* **2026**, *7*, 86. [https://doi.org/10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

This article documents the R `gpbiometrics` package that provides the scientific and software lineage for `gpbiometricspy`. When an analysis uses the Python package, cite the relevant `gpbiometricspy` software version as well; the R-package article is a related publication rather than a substitute for the Python software citation.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies the latest stable Python software version and release date, and records the published R-package paper as a related reference; the 0.1.3 version DOI is added after Zenodo ingestion.
- `.zenodo.json` provides Zenodo-specific archival metadata and the R-reference provenance relationship.
- README and documentation use the Python concept DOI badge for the evolving software family.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
