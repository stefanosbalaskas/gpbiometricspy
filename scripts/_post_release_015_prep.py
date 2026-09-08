from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Live package / generated identity moves to the next development line.
replace_once("pyproject.toml", 'version = "0.1.5"', 'version = "0.1.6.dev0"')
replace_once(".zenodo.json", '"version": "0.1.5"', '"version": "0.1.6.dev0"')
replace_once("docs/assets/generated/manifest.json", '"package_version": "0.1.5"', '"package_version": "0.1.6.dev0"')
replace_once("src/gpbiometricspy/__init__.py", '__version__ = "0.1.5"', '__version__ = "0.1.6.dev0"')
replace_once("src/gpbiometricspy/governance_core.py", "package_version='0.1.5'", "package_version='0.1.6.dev0'")
replace_once("src/gpbiometricspy/governance_extra.py", "'gpbiometricspy_version':'0.1.5'", "'gpbiometricspy_version':'0.1.6.dev0'")
replace_once("src/gpbiometricspy/remaining_core.py", 'version = "0.1.5"', 'version = "0.1.6.dev0"')
replace_once("tests/test_coverage_completion_remaining_core.py", "assert out['package_version']=='0.1.5'", "assert out['package_version']=='0.1.6.dev0'")
replace_once("tests/test_post_release_completeness.py", "assert gp.__version__=='0.1.5'", "assert gp.__version__=='0.1.6.dev0'")
replace_once("tests/test_post_release_completeness.py", "assert manifest['package_version']=='0.1.5'", "assert manifest['package_version']=='0.1.6.dev0'")
replace_once("tests/test_post_release_completeness.py", 'assert zenodo["version"] == "0.1.5"', 'assert zenodo["version"] == "0.1.6.dev0"')

# README retains stable release identity while exposing live development/publication state.
replace_once(
    "README.md",
    "| Stable release | **0.1.5** |\n| Release date | **2026-09-08** |",
    "| Stable release | **0.1.5** |\n| Development head | **0.1.6.dev0** |\n| Release date | **2026-09-08** |",
)
replace_once(
    "README.md",
    "`gpbiometricspy 0.1.5` is the current stable release source. Its version-specific Zenodo DOI will be recorded only after Zenodo ingests the immutable `v0.1.5` GitHub release; the concept DOI identifies the evolving Python software record.",
    "`gpbiometricspy 0.1.5` is the current stable release and is published on PyPI from immutable tag `v0.1.5`; live repository development proceeds as `0.1.6.dev0`. Its version-specific Zenodo DOI will be recorded only after Zenodo ingests the immutable GitHub release; the concept DOI identifies the evolving Python software record.",
)

# Documentation distinguishes stable citation from live development.
replace_once(
    "docs/index.md",
    '<div><span class="gp-status-value">0.1.5</span><span class="gp-status-label">stable release</span></div>\n<div><span class="gp-status-value">2026-09-08</span><span class="gp-status-label">release date</span></div>',
    '<div><span class="gp-status-value">0.1.5</span><span class="gp-status-label">stable release</span></div>\n<div><span class="gp-status-value">0.1.6.dev0</span><span class="gp-status-label">development head</span></div>\n<div><span class="gp-status-value">2026-09-08</span><span class="gp-status-label">release date</span></div>',
)
replace_once(
    "docs/index.md",
    "The 0.1.5 Zenodo version DOI is intentionally absent until ingestion; the previous 0.1.4 DOI remains [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782), and the software concept DOI remains [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872).",
    "The 0.1.5 Zenodo version DOI remains intentionally absent until ingestion; the previous 0.1.4 DOI remains [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782), and the software concept DOI remains [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872). The immutable 0.1.5 wheel and sdist are public on PyPI, while live repository development proceeds as `0.1.6.dev0`.",
)
replace_once(
    "docs/citation.md",
    "<strong>Current citation state:</strong> stable Python release <code>0.1.5</code> (2026-09-08). Its version-specific Zenodo DOI will be added only after Zenodo ingests the immutable <code>v0.1.5</code> GitHub release; the software concept DOI remains the identifier for the evolving record.",
    "<strong>Current citation state:</strong> stable Python release <code>0.1.5</code> (2026-09-08). Its version-specific Zenodo DOI will be added only after Zenodo ingests the immutable <code>v0.1.5</code> GitHub release; live repository development proceeds as <code>0.1.6.dev0</code>, while the software concept DOI remains the identifier for the evolving record.",
)
replace_once(
    "docs/citation.md",
    "- `.zenodo.json` identifies archival software version 0.1.5 and preserves the R-reference provenance relationship.",
    "- `.zenodo.json` preserves the R-reference provenance relationship and, on live development, tracks version 0.1.6.dev0 separately from the stable CFF citation record.",
)
replace_once(
    "docs/release-0.1.5.md",
    "The 0.1.5 Zenodo version DOI is intentionally left pending until Zenodo ingests the immutable GitHub release. The previous 0.1.4 version DOI remains **10.5281/zenodo.22515782**, the software concept DOI remains **10.5281/zenodo.22150872**, and the frozen R reference remains **10.5281/zenodo.21434608** as provenance.",
    "The immutable `v0.1.5` GitHub Release and PyPI publication are complete. The wheel SHA-256 is **eb2474a7d3156b305c573a5327040038f6ec08ba7e5cf244952712b3d239c607** and the sdist SHA-256 is **b8605ad8d402a948d0610dd40ff98985dedf6351b681b7e43294df38d10dc47e**; protected Trusted Publishing also generated Sigstore attestations. The 0.1.5 Zenodo version DOI remains pending until Zenodo ingests the immutable GitHub release. The previous 0.1.4 version DOI remains **10.5281/zenodo.22515782**, the software concept DOI remains **10.5281/zenodo.22150872**, and the frozen R reference remains **10.5281/zenodo.21434608** as provenance. Live repository development proceeds as `0.1.6.dev0` without changing the immutable 0.1.5 artifacts.",
)

# Release checklist closes completed public-release gates but leaves Zenodo pending.
checklist = Path("RELEASE_CHECKLIST.md")
text = checklist.read_text(encoding="utf-8")
completed = {
    "- [ ] Require every workflow family triggered by the exact stable-freeze PR head to pass before pinned-head squash merge.": "- [x] Require every workflow family triggered by the exact stable-freeze PR head to pass before pinned-head squash merge.",
    "- [ ] Require all ten stable-release gate families to succeed on the exact merged stable `main` commit before creating `v0.1.5`.": "- [x] Require all ten stable-release gate families to succeed on the exact merged stable `main` commit before creating `v0.1.5`.",
    "- [ ] Create immutable annotated `v0.1.5`, let the protected release workflow build/check GitHub assets, and verify the SHA-256 manifest.": "- [x] Create immutable annotated `v0.1.5`, let the protected release workflow build/check GitHub assets, and verify the SHA-256 manifest.",
    "- [ ] Confirm protected PyPI Trusted Publishing publishes `gpbiometricspy==0.1.5` and fresh public-index installs succeed.": "- [x] Confirm protected PyPI Trusted Publishing publishes `gpbiometricspy==0.1.5`; both distribution uploads returned HTTP 200 and Sigstore attestations were generated.",
}
for old, new in completed.items():
    if text.count(old) != 1:
        raise SystemExit(f"RELEASE_CHECKLIST.md expected one match for {old!r}")
    text = text.replace(old, new, 1)
section = """

### 0.1.5 post-release publication evidence

- [x] Immutable annotated `v0.1.5` resolves to exact qualified commit `294a9b6349aef93abae84bda6f2c89afce1001de`.
- [x] GitHub Release `v0.1.5` published the exact wheel, sdist, and SHA-256 manifest after the ten exact-main release gates passed.
- [x] GitHub Release and PyPI wheel SHA-256 match: `eb2474a7d3156b305c573a5327040038f6ec08ba7e5cf244952712b3d239c607`.
- [x] GitHub Release and PyPI sdist SHA-256 match: `b8605ad8d402a948d0610dd40ff98985dedf6351b681b7e43294df38d10dc47e`.
- [x] Protected PyPI Trusted Publishing generated Sigstore attestations; Rekor indexes: wheel `2762034607`, sdist `2762034601`.
- [ ] Zenodo ingestion / 0.1.5 version DOI is still pending and must not be inferred.
- [ ] After Zenodo mints the DOI, pin `CITATION.cff` to stable 0.1.5 + the actual DOI, add `VersionDOI` / update version-history links, and complete archival closeout.
- [ ] Merge the completed closeout to return live repository identity to `0.1.6.dev0` while leaving immutable `v0.1.5`, GitHub Release, and PyPI artifacts unchanged.
"""
if "### 0.1.5 post-release publication evidence" in text:
    raise SystemExit("post-release evidence section already exists")
checklist.write_text(text.rstrip() + section + "\n", encoding="utf-8")

# Release notes record immutable distribution evidence without fabricating a DOI.
notes = Path("RELEASE_NOTES_0.1.5.md")
text = notes.read_text(encoding="utf-8")
marker = "\n## Release integrity\n"
if text.count(marker) != 1:
    raise SystemExit("RELEASE_NOTES_0.1.5.md release-integrity marker mismatch")
record = """

## Post-release distribution record

- Immutable annotated tag `v0.1.5` resolves to exact qualified commit `294a9b6349aef93abae84bda6f2c89afce1001de`.
- GitHub Release and PyPI wheel SHA-256: `eb2474a7d3156b305c573a5327040038f6ec08ba7e5cf244952712b3d239c607`.
- GitHub Release and PyPI sdist SHA-256: `b8605ad8d402a948d0610dd40ff98985dedf6351b681b7e43294df38d10dc47e`.
- Protected PyPI Trusted Publishing completed with HTTP 200 uploads and Sigstore/Rekor attestations (wheel Rekor `2762034607`; sdist Rekor `2762034601`).
- The 0.1.5 Zenodo version DOI remains pending ingestion and is deliberately not inferred.
- Live repository development is prepared as `0.1.6.dev0`; the stable `CITATION.cff` record remains 0.1.5 / 2026-09-08 until the actual Zenodo version DOI exists.
"""
notes.write_text(text.replace(marker, record + marker, 1), encoding="utf-8")
