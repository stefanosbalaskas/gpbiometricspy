# Citation and archival

`gpbiometricspy` is archived through the Zenodo GitHub integration.

<div class="gp-version-note">
<strong>Current citation state:</strong> stable Python release <code>0.1.5</code> (2026-09-08). Its version-specific Zenodo DOI will be added only after Zenodo ingests the immutable <code>v0.1.5</code> GitHub release; the software concept DOI remains the identifier for the evolving record.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used. During the pre-ingestion window for 0.1.5, use the release/tag metadata and update the citation with the minted 0.1.5 version DOI once Zenodo publishes it.

- **0.1.5 version DOI:** pending Zenodo ingestion — not invented in release metadata
- **Previous 0.1.4 version DOI:** **[10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)**
- **Earlier 0.1.3 version DOI:** **[10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)**
- **Earlier 0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**

Zenodo recommends the version DOI when citing a specific research artifact version. The concept DOI identifies the evolving software family.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control. The 0.1.5 stable freeze records the version and release date but intentionally omits a version DOI until Zenodo mints one.

## Published gpbiometrics paper

The peer-reviewed paper describing the original R package is:

> Balaskas, S. **gpbiometrics: An R Package for Reproducible Analysis and Reporting of Gazepoint Biometrics Exports.** *Signals* **2026**, *7*, 86. [https://doi.org/10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

This article documents the R `gpbiometrics` package that provides the scientific and software lineage for `gpbiometricspy`. When an analysis uses the Python package, cite the relevant `gpbiometricspy` software version as well; the R-package article is a related publication rather than a substitute for the Python software citation.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies stable Python release 0.1.5 and release date 2026-09-08; its DOI is intentionally absent before Zenodo ingestion.
- `.zenodo.json` identifies archival software version 0.1.5 and preserves the R-reference provenance relationship.
- README and documentation use the Python concept DOI for the evolving software family while retaining earlier version DOIs for reproducible citation.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
