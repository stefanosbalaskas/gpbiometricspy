# Citation and archival

`gpbiometricspy` is archived through the Zenodo GitHub integration.

<div class="gp-version-note">
<strong>Current citation state:</strong> stable Python release <code>0.1.2</code>; development branch <code>0.1.3.dev0</code>; Zenodo version and concept DOI registered.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used:

- **0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)**

Zenodo recommends the version DOI when citing a specific research artifact version. The concept DOI resolves to the latest version and is appropriate when referring to the evolving software family.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control; the file records the 0.1.2 version DOI.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies the latest stable Python software version and its version DOI.
- `.zenodo.json` provides Zenodo-specific archival metadata and the R-reference provenance relationship.
- README and documentation use the Python concept DOI badge for the evolving software family.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
