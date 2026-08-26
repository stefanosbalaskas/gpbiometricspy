# Release checklist

- [ ] Exact R export audit reports 406/406 implemented and 0 pending.
- [ ] `compileall` passes.
- [ ] Full pytest suite passes with coverage ≥90%.
- [ ] Every frozen export remains directly referenced by a Python test.
- [ ] Synthetic kiosk demo loads 69,120 rows / 36 participants.
- [ ] Generated API reference contains 406 function entries.
- [ ] Article migration catalog contains 26 companions.
- [ ] Ruff passes in CI.
- [ ] MkDocs strict build passes in CI.
- [ ] Wheel and sdist build successfully.
- [ ] Twine metadata check passes in CI.
- [ ] Fresh wheel install smoke passes.
- [ ] Fresh sdist install smoke passes.
- [ ] Changelog, citation and version metadata are synchronized.
- [ ] Git tag and GitHub release are created from the validated commit.
- [ ] PyPI publication is performed only after the release candidate gates pass.
