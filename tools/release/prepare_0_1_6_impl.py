from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.6"
RELEASE_DATE = "2026-09-11"
CONCEPT_DOI = "10.5281/zenodo.22150872"
PREVIOUS_DOI = "10.5281/zenodo.22672823"
R_REFERENCE_DOI = "10.5281/zenodo.21434608"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one occurrence of {old!r}, found {count}")
    write(path, text.replace(old, new, 1))


def replace_all_exact(path: str, old: str, new: str, minimum: int = 1) -> None:
    text = read(path)
    count = text.count(old)
    if count < minimum:
        raise SystemExit(f"{path}: expected at least {minimum} occurrences of {old!r}, found {count}")
    write(path, text.replace(old, new))


def prepare_pyproject() -> None:
    text = read("pyproject.toml")
    text = text.replace('version = "0.1.6.dev0"', 'version = "0.1.6"', 1)
    version_doi = 'VersionDOI = "https://doi.org/10.5281/zenodo.22672823"\n'
    if text.count(version_doi) != 1:
        raise SystemExit("pyproject.toml: expected the 0.1.5 VersionDOI exactly once")
    text = text.replace(version_doi, "", 1)
    old_previous = 'PreviousVersionDOI = "https://doi.org/10.5281/zenodo.22515782"'
    new_previous = 'PreviousVersionDOI = "https://doi.org/10.5281/zenodo.22672823"'
    if text.count(old_previous) != 1:
        raise SystemExit("pyproject.toml: expected the 0.1.4 PreviousVersionDOI exactly once")
    text = text.replace(old_previous, new_previous, 1)
    write("pyproject.toml", text)


def prepare_zenodo() -> None:
    path = ROOT / ".zenodo.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != "0.1.6.dev0":
        raise SystemExit(f"Unexpected Zenodo development version: {data.get('version')!r}")
    data["version"] = VERSION
    data["description"] = (
        "gpbiometricspy is the Python counterpart of gpbiometrics, with gpbiometrics 2.0.0 frozen as its initial "
        "semantic reference. It provides Gazepoint-native workflows for EDA/GSR/SCR, PPG/HRV, pupil, gaze, fixation, "
        "AOI, TTL/event alignment, multimodal quality control, analysis, plotting, reporting, simulation, reproducibility, "
        "and interoperability. Version 0.1.6 preserves the complete 406-export scientific contract and 100% statement "
        "coverage while promoting gpbiometricspy Studio as a guided end-user research workflow with project identity, "
        "quality-control routing, analysis modules, timeline/provenance, reporting, and reproducible recipe support. "
        "The normal Python/GitHub/PyPI release remains independent of the optional standalone Windows signing path."
    )
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare_cff() -> None:
    text = read("CITATION.cff")
    text = re.sub(r"(?m)^version:\s*0\.1\.5\s*$", f"version: {VERSION}", text, count=1)
    text = re.sub(r"(?m)^date-released:\s*2026-09-08\s*$", f"date-released: {RELEASE_DATE}", text, count=1)
    text, n = re.subn(r"(?m)^doi:\s*10\.5281/zenodo\.22672823\s*\n", "", text, count=1)
    if n != 1:
        raise SystemExit("CITATION.cff: expected the top-level 0.1.5 DOI exactly once")
    write("CITATION.cff", text)


def prepare_source_and_generated_identity() -> None:
    for path in [
        "src/gpbiometricspy/__init__.py",
        "src/gpbiometricspy/governance_core.py",
        "src/gpbiometricspy/governance_extra.py",
        "src/gpbiometricspy/remaining_core.py",
        "docs/assets/generated/manifest.json",
        "tests/test_post_release_completeness.py",
        "tests/test_coverage_completion_remaining_core.py",
    ]:
        replace_all_exact(path, "0.1.6.dev0", VERSION)


def prepare_tests() -> None:
    path = "tests/test_post_release_completeness.py"
    text = read(path)
    replacements = {
        'assert "version: 0.1.5" in cff': 'assert "version: 0.1.6" in cff',
        'assert "date-released: 2026-09-08" in cff': 'assert "date-released: 2026-09-11" in cff',
        'assert "doi: 10.5281/zenodo.22672823" in cff': 'assert "\\ndoi: 10.5281/zenodo.22672823\\n" not in cff',
        'assert urls["VersionDOI"] == "https://doi.org/10.5281/zenodo.22672823"': 'assert "VersionDOI" not in urls',
        'assert urls["PreviousVersionDOI"] == "https://doi.org/10.5281/zenodo.22515782"': 'assert urls["PreviousVersionDOI"] == "https://doi.org/10.5281/zenodo.22672823"',
    }
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise SystemExit(f"{path}: expected exactly one assertion {old!r}")
        text = text.replace(old, new, 1)
    write(path, text)


def prepare_readme() -> None:
    path = "README.md"
    text = read(path)
    badge_old = (
        '<a href="https://doi.org/10.5281/zenodo.22672823"><img alt="Version DOI" '
        'src="https://zenodo.org/badge/DOI/10.5281/zenodo.22672823.svg"></a>'
    )
    badge_new = (
        '<a href="https://doi.org/10.5281/zenodo.22150872"><img alt="Concept DOI" '
        'src="https://zenodo.org/badge/DOI/10.5281/zenodo.22150872.svg"></a>'
    )
    if badge_old not in text:
        raise SystemExit("README.md: expected 0.1.5 DOI badge")
    text = text.replace(badge_old, badge_new, 1)
    text = text.replace('gpbiometricspy[studio]==0.1.5', 'gpbiometricspy[studio]==0.1.6', 1)
    text = text.replace('| Stable release | **0.1.5** |', '| Stable release | **0.1.6** |', 1)
    text = text.replace('| Development head | **0.1.6.dev0** |', '| Release date | **2026-09-11** |', 1)
    text = text.replace('| Tests | **567** |', '| Tests | **641** |', 1)
    old_intro = (
        'Stable `gpbiometricspy 0.1.5` was released on **2026-09-08** from immutable tag `v0.1.5`. '
        'Live repository development proceeds as `0.1.6.dev0`.'
    )
    new_intro = (
        'Stable `gpbiometricspy 0.1.6` was released on **2026-09-11** from the fully qualified stable-release line. '
        'The 0.1.6 Zenodo version DOI is intentionally left unset until Zenodo ingests the immutable GitHub release.'
    )
    if old_intro not in text:
        raise SystemExit("README.md: expected archival intro")
    text = text.replace(old_intro, new_intro, 1)
    old_bullets = (
        '- **0.1.5 version DOI:** [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)\n'
        '- **Software concept DOI:** [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)\n'
        '- **Previous 0.1.4 DOI:** [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)'
    )
    new_bullets = (
        '- **0.1.6 version DOI:** pending Zenodo ingestion of `v0.1.6` — no DOI is fabricated before minting\n'
        '- **Software concept DOI:** [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872)\n'
        '- **Previous 0.1.5 DOI:** [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823)\n'
        '- **Earlier 0.1.4 DOI:** [10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)'
    )
    if old_bullets not in text:
        raise SystemExit("README.md: expected DOI history block")
    text = text.replace(old_bullets, new_bullets, 1)
    old_citation = (
        '> Balaskas, S. (2026). *gpbiometricspy: Python tools for Gazepoint biometric workflows* '
        '(Version 0.1.5) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.22672823'
    )
    new_citation = (
        '> Balaskas, S. (2026). *gpbiometricspy: Python tools for Gazepoint biometric workflows* '
        '(Version 0.1.6) [Computer software]. GitHub. https://github.com/stefanosbalaskas/gpbiometricspy/releases/tag/v0.1.6'
    )
    if old_citation not in text:
        raise SystemExit("README.md: expected 0.1.5 recommended citation")
    text = text.replace(old_citation, new_citation, 1)
    write(path, text)


def prepare_docs_index() -> None:
    path = "docs/index.md"
    text = read(path)
    replacements = {
        '<span class="gp-status-value">0.1.5</span><span class="gp-status-label">stable release</span>': '<span class="gp-status-value">0.1.6</span><span class="gp-status-label">stable release</span>',
        '<span class="gp-status-value">0.1.6.dev0</span><span class="gp-status-label">development head</span>': '<span class="gp-status-value">2026-09-11</span><span class="gp-status-label">release date</span>',
        'gpbiometricspy[studio]==0.1.5': 'gpbiometricspy[studio]==0.1.6',
        'Stable 0.1.5 freezes 567 tests, 10,456/10,456 statements, 5,629/5,648 raw branches = 99.6636%, and zero unexpected, stale or unaudited branch debt.': 'Stable 0.1.6 freezes 641 core tests, preserves 10,456/10,456 package statements = 100.00%, 5,629/5,648 raw branches = 99.6636%, and zero unexpected, stale or unaudited branch debt.',
        'Stable `gpbiometricspy 0.1.5` was released on **2026-09-08**. The version DOI is [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823), the software concept DOI is [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872), and live development proceeds as `0.1.6.dev0`.': 'Stable `gpbiometricspy 0.1.6` was released on **2026-09-11**. Its version DOI remains pending until Zenodo ingests `v0.1.6`; the software concept DOI is [10.5281/zenodo.22150872](https://doi.org/10.5281/zenodo.22150872), and the previous 0.1.5 version DOI is [10.5281/zenodo.22672823](https://doi.org/10.5281/zenodo.22672823).',
    }
    for old, new in replacements.items():
        if old not in text:
            raise SystemExit(f"{path}: expected text not found: {old!r}")
        text = text.replace(old, new, 1)
    write(path, text)


def prepare_citation_page() -> None:
    text = f'''# Citation and archival

`gpbiometricspy` is archived through Zenodo.

<div class="gp-version-note">
<strong>Current citation state:</strong> stable Python release <code>{VERSION}</code> was frozen on <strong>{RELEASE_DATE}</strong>. The software concept DOI remains <strong>{CONCEPT_DOI}</strong>. The {VERSION} version DOI will be recorded only after Zenodo ingests the immutable <code>v{VERSION}</code> GitHub release.
</div>

## Cite the Python software

For reproducibility, cite the exact software release used.

- **{VERSION} version DOI:** pending Zenodo ingestion; no DOI is invented before minting.
- **Previous 0.1.5 version DOI:** **[{PREVIOUS_DOI}](https://doi.org/{PREVIOUS_DOI})**
- **Earlier 0.1.4 version DOI:** **[10.5281/zenodo.22515782](https://doi.org/10.5281/zenodo.22515782)**
- **Earlier 0.1.3 version DOI:** **[10.5281/zenodo.22313884](https://doi.org/10.5281/zenodo.22313884)**
- **Earlier 0.1.2 version DOI:** **[10.5281/zenodo.22150873](https://doi.org/10.5281/zenodo.22150873)**
- **Software concept DOI:** **[{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI})**

Until Zenodo mints the {VERSION} version DOI, cite the immutable GitHub release together with the version number. After ingestion, the genuine Zenodo version DOI can be added in a post-release metadata closeout without altering the immutable PyPI/GitHub artifacts.

GitHub reads [`CITATION.cff`](https://github.com/stefanosbalaskas/gpbiometricspy/blob/main/CITATION.cff) for its **Cite this repository** control. The stable release record is pinned to version `{VERSION}` and release date `{RELEASE_DATE}`; its DOI field is deliberately absent before Zenodo minting.

## Published gpbiometrics paper

The peer-reviewed paper describing the original R package is:

> Balaskas, S. **gpbiometrics: An R Package for Reproducible Analysis and Reporting of Gazepoint Biometrics Exports.** *Signals* **2026**, *7*, 86. [https://doi.org/10.3390/signals7050086](https://doi.org/10.3390/signals7050086)

This article documents the R `gpbiometrics` package that provides the scientific and software lineage for `gpbiometricspy`. When an analysis uses the Python package, cite the relevant `gpbiometricspy` software version as well; the R-package article is a related publication rather than a substitute for the Python software citation.

## R reference provenance

The frozen semantic reference is **gpbiometrics 2.0.0**, independently archived at DOI **[{R_REFERENCE_DOI}](https://doi.org/{R_REFERENCE_DOI})**.

That DOI identifies the R reference package. `.zenodo.json` preserves it with relation `isDerivedFrom`, so the Python and R software objects remain distinct.

## Metadata files

- `CITATION.cff` identifies stable Python release {VERSION} and release date {RELEASE_DATE}; the version DOI is intentionally absent until Zenodo minting.
- `.zenodo.json` identifies software version {VERSION} and preserves the R-reference provenance relationship.
- `pyproject.toml` exposes the software concept DOI, previous 0.1.5 version DOI, and R-reference DOI in distinct URL roles; `VersionDOI` will be added only after the genuine {VERSION} DOI exists.
- README and documentation retain prior version DOIs for reproducible citation.

## Interpretation

A Zenodo DOI provides a persistent identifier for a software archive. It does not replace the package's scientific validation evidence, which remains documented under [Parity & validation](parity.md) and [Deep validation](deep-validation.md).
'''
    write("docs/citation.md", text)


def clean_historical_dev_literals() -> None:
    replacements = {
        "docs/release-0.1.5.md": ("Live repository development proceeds as `0.1.6.dev0`", "Subsequent repository development proceeded on the 0.1.6 development line"),
        "RELEASE_NOTES_0.1.5.md": ("Live repository development is `0.1.6.dev0`", "Subsequent repository development moved to the 0.1.6 development line"),
        "RELEASE_CHECKLIST.md": ("live repository identity `0.1.6.dev0`", "live repository identity on the 0.1.6 development line"),
    }
    for path, (old, new) in replacements.items():
        replace_once(path, old, new)


def append_release_checklist() -> None:
    path = "RELEASE_CHECKLIST.md"
    text = read(path)
    marker = "## 0.1.6 — Studio product release and canonical Python publication"
    if marker in text:
        raise SystemExit("RELEASE_CHECKLIST.md already contains the 0.1.6 section")
    section = f'''\n\n{marker}\n\n- [x] Preserve the frozen `gpbiometrics 2.0.0` semantic contract at **406/406 implemented exports, 0 pending**.\n- [x] Merge the fully certified Studio product-polish tranche, including guided researcher/teaching routes, QC prerequisites, project identity/fingerprints, Timeline/provenance, reporting, recipes and end-to-end first-session validation.\n- [x] Freeze the development line to stable `{VERSION}` across package/runtime, Zenodo metadata, generated documentation metadata, README/site and release-sensitive tests.\n- [x] Record release date **{RELEASE_DATE}** and deliberately omit a `{VERSION}` Zenodo version DOI before ingestion.\n- [x] Retain software concept DOI `{CONCEPT_DOI}`, previous 0.1.5 DOI `{PREVIOUS_DOI}`, and R-reference DOI `{R_REFERENCE_DOI}` only in their correct roles.\n- [x] Keep optional Windows PyInstaller/signing/installer/handoff evidence separate from the normal Python/GitHub/PyPI/Zenodo release gate.\n- [ ] Require all ten exact-main package/scientific release-gate families to pass on the merged stable commit.\n- [ ] Create immutable annotated `v{VERSION}` only from that exact current-main commit.\n- [ ] Confirm canonical GitHub Release wheel/sdist, `SHA256SUMS.txt`, and `RELEASE-METADATA.json`.\n- [ ] Confirm protected PyPI Trusted Publishing publishes `gpbiometricspy=={VERSION}` only from the canonical successful release workflow artifact.\n- [ ] Wait for Zenodo ingestion, record the genuine {VERSION} version DOI, and complete the post-release citation/metadata closeout without altering immutable release artifacts.\n'''
    write(path, text.rstrip() + section)


def write_release_notes() -> None:
    text = f'''# gpbiometricspy {VERSION} — Studio product workflow and release simplification

Release candidate frozen **{RELEASE_DATE}**.

`gpbiometricspy {VERSION}` preserves the frozen **406/406** `gpbiometrics 2.0.0` scientific API while promoting Studio into a substantially more complete end-user research workflow.

## Product and workflow layer

- guided researcher and teaching routes;
- project identity and fingerprint checks;
- module prerequisites and researcher-facing remediation;
- integrated QC, EDA/SCR, PPG/HR/HRV, pupil, gaze/AOI, event alignment, multimodal, statistics and reporting routes;
- project Timeline/provenance, recent-project handling and reproducible recipe lifecycle;
- browser end-to-end coverage of the first physiology session from guided synthetic start through reporting and project edit state.

## Scientific contract

- **406 / 406** frozen exports implemented;
- **0 pending** exports;
- package statement coverage remains **100%**;
- the release-preparation baseline carries **641 passing core tests** on the certified Studio product head before stable identity freeze;
- public demonstration mode remains synthetic-only.

## Python publication boundary

The normal Python release no longer depends on optional standalone Windows code signing or human installer validation. The Windows packaging/signing/handoff workflows remain available as engineering evidence for a future signed standalone installer, but they do not block the Python/GitHub/PyPI/Zenodo release.

Stable publication remains fail-closed: exact-current-main validation, immutable exact tag, reproducible wheel/sdist build, SHA-256 package manifest, canonical release metadata, byte-identical GitHub Release assets, and PyPI Trusted Publishing only from the successful canonical release workflow artifact.

## Archival boundary

- software concept DOI: **{CONCEPT_DOI}**;
- previous 0.1.5 version DOI: **{PREVIOUS_DOI}**;
- frozen R-reference provenance DOI: **{R_REFERENCE_DOI}**;
- {VERSION} version DOI: **pending Zenodo ingestion**; no pre-ingestion DOI is fabricated.
'''
    write("RELEASE_NOTES_0.1.6.md", text)


def assert_no_dev_literals() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".toml", ".cff", ".yml", ".yaml", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "0.1.6.dev0" in text:
            offenders.append(str(path.relative_to(ROOT)))
    if offenders:
        raise SystemExit("0.1.6.dev0 literals remain: " + ", ".join(sorted(offenders)))


def main() -> None:
    prepare_pyproject()
    prepare_zenodo()
    prepare_cff()
    prepare_source_and_generated_identity()
    prepare_tests()
    prepare_readme()
    prepare_docs_index()
    prepare_citation_page()
    clean_historical_dev_literals()
    append_release_checklist()
    write_release_notes()
    assert_no_dev_literals()
    print("gpbiometricspy 0.1.6 deterministic release freeze prepared")


if __name__ == "__main__":
    main()
