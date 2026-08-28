# Citation and archival

`gpbiometricspy` is configured for software citation through GitHub and for archival through the Zenodo GitHub integration.

<div class="gp-version-note">
<strong>Current citation state:</strong> Python release <code>0.1.2</code>; Zenodo integration enabled; first Python DOI pending automatic ingestion of <code>v0.1.2</code>.
</div>

## Cite the Python software

GitHub reads the repository's [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) and exposes a **Cite this repository** control. Cite the exact Python version used in an analysis.

`0.1.2` is the first `gpbiometricspy` release prepared after the Zenodo GitHub integration was enabled. Its GitHub release is therefore eligible for automatic Zenodo ingestion and DOI registration. The DOI is recorded here only after Zenodo has actually minted it.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0** and is archived independently at DOI **[10.5281/zenodo.21434608](https://doi.org/10.5281/zenodo.21434608)**.

That DOI identifies the R reference package. It is recorded in `.zenodo.json` with the relation `isDerivedFrom` so the eventual Python Zenodo record retains explicit provenance without conflating the two software objects.

## Metadata files

- `CITATION.cff` provides GitHub/Citation File Format metadata, including author ORCID and affiliation.
- `.zenodo.json` provides Zenodo-specific archival metadata and the related identifier linking to the frozen R reference DOI.
- Once Zenodo mints the first Python DOI, the README, documentation and citation metadata should be updated with the Python **concept DOI** and the release-specific **version DOI**.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
