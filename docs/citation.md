# Citation and archival

`gpbiometricspy` is archived through Zenodo.

<div class="gp-version-note">
<strong>Current citation state:</strong> stable Python release <code>0.1.5</code> (2026-09-08) is archived at Zenodo DOI <strong>10.5281/zenodo.22672823</strong>. Live repository development proceeds as <code>0.1.6.dev0</code>, while the software concept DOI remains the identifier for the evolving record.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used.

- **0.1.5 version DOI:** **[10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)**
- **Previous 0.1.4 version DOI:** **[10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)**
- **Earlier 0.1.3 version DOI:** **[10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)**
- **Earlier 0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**

Zenodo recommends the version DOI when citing a specific research artifact version. The concept DOI identifies the evolving software family.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control. The stable 0.1.5 citation record is pinned to version `0.1.5`, release date `2026-09-08`, and DOI `10.5281/zenodo.22672823`.

## Published gpbiometrics paper

The peer-reviewed paper describing the original R package is:

> Balaskas, S. **gpbiometrics: An R Package for Reproducible Analysis and Reporting of Gazepoint Biometrics Exports.** *Signals* **2026**, *7*, 86. [https://doi.org/10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

This article documents the R `gpbiometrics` package that provides the scientific and software lineage for `gpbiometricspy`. When an analysis uses the Python package, cite the relevant `gpbiometricspy` software version as well; the R-package article is a related publication rather than a substitute for the Python software citation.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies stable Python release 0.1.5, release date 2026-09-08, and version DOI `10.5281/zenodo.22672823`.
- `.zenodo.json` preserves the R-reference provenance relationship and, on live development, tracks version `0.1.6.dev0` separately from the stable CFF citation record.
- `pyproject.toml` exposes the software concept DOI, current 0.1.5 version DOI, previous 0.1.4 version DOI, and R-reference DOI in distinct URL roles.
- README and documentation use the Python concept DOI for the evolving software family while retaining version DOIs for reproducible citation.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
