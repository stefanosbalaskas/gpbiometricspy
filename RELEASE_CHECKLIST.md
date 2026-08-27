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

## Next release — 0.1.1 (development starts at 0.1.1.dev0)

- [ ] Core tests, export audit, coverage, docs and package builds remain green.
- [ ] R/Python golden-fixture workflow passes.
- [ ] Optional-backend floor/current interoperability workflow passes.
- [ ] All 26 executable tutorial companions pass.
- [ ] Real-data validator is exercised on at least one private Gazepoint export profile outside Git.
- [ ] CodeQL/dependency automation is green.
- [ ] Stable release notes distinguish validation/documentation changes from semantic API changes.
