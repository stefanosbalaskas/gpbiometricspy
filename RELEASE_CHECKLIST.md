# Release checklist

## 0.1.0 — completed

- [x] Exact R export audit reports 406/406 implemented and 0 pending.
- [x] `compileall` passes.
- [x] Full pytest suite passes with coverage ≥90%.
- [x] Every frozen export remains directly referenced by a Python test.
- [x] Synthetic kiosk demo loads 69,120 rows / 36 participants.
- [x] Generated API reference contains 406 function entries.
- [x] Article migration catalog contains 26 companions.
- [x] Ruff passes in CI.
- [x] MkDocs strict build passes in CI.
- [x] Wheel and sdist build successfully.
- [x] Twine metadata check passes in CI.
- [x] Fresh wheel/public-PyPI install smoke passes.
- [x] Stable wheel/sdist hashes match between GitHub Release and PyPI.
- [x] Changelog, citation and version metadata were synchronized for the stable release.
- [x] Annotated `v0.1.0` tag and non-prerelease GitHub release were created from the validated commit.
- [x] PyPI publication occurred only after release gates passed.
- [x] GitHub Pages is enabled from `gh-pages` `/` with HTTPS.

## 0.1.1 — stable release gates

- [x] Core tests, exact export audit and coverage remain green (211 tests; 406/406 exports; 0 pending; coverage >=90%).
- [x] R/Python golden-fixture workflow passes.
- [x] Optional-backend floor/current interoperability workflow passes 14/14.
- [x] All 26 executable tutorial companions pass.
- [x] Privacy-safe representative real-data harness passes without committing participant data.
- [x] CodeQL, Dependabot configuration and repository security automation are present/green.
- [x] Stable release notes distinguish validation/documentation changes from semantic API changes.
- [x] Release workflow verifies the exact validated commit before creating the GitHub Release.
- [x] Release workflow explicitly dispatches protected PyPI Trusted Publishing after GitHub Release creation.
- [ ] Optional additional evidence: validate against an approved genuine participant Gazepoint export locally or on an approved private runner. This is not a public-release blocker and is not claimed by the package.
## 0.1.2 — Zenodo-backed release preparation

- [x] Zenodo GitHub integration is enabled for `stefanosbalaskas/gpbiometricspy`.
- [x] `CITATION.cff` contains ORCID, affiliation, abstract and software keywords.
- [x] `.zenodo.json` declares software/open/MIT metadata and links the frozen R reference DOI `10.5281/zenodo.21434608` as `isDerivedFrom`.
- [x] README/site distinguish stable `0.1.1`, development `0.1.2.dev0`, R-reference DOI and future Python DOI.
- [x] Release workflow validates archival metadata before building a stable release.
- [ ] Promote `0.1.2.dev0` to stable `0.1.2` only after the development tranche is intentionally frozen.
- [ ] Create annotated `v0.1.2` only from the exact fully validated stable commit.
- [ ] Wait for Zenodo to ingest the GitHub release and confirm the software record is published.
- [ ] Record the Zenodo **version DOI** for `v0.1.2` and the software **concept DOI**.
- [ ] Add the Python concept DOI badge/link to README and documentation; add the release DOI to release-specific citation metadata where appropriate.
- [ ] Verify the Zenodo record preserves the R-reference `isDerivedFrom` relation without presenting the R DOI as the Python DOI.
- [ ] Verify Software Heritage archival status once Zenodo reports it under external resources.
