from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEV = "0.1.4.dev0"
STABLE = "0.1.3"
VERSION_DOI = "10.5281/zenodo.22313884"
CONCEPT_DOI = "10.5281/zenodo.22150872"
PREVIOUS_DOI = "10.5281/zenodo.22150873"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one {old!r}, found {count}")
    write(path, text.replace(old, new, 1))


# Live package/development identity.
replace_once("pyproject.toml", 'version = "0.1.3"', 'version = "0.1.4.dev0"')
pyproject = read("pyproject.toml")
marker = (
    f'DOI = "https://doi.org/{CONCEPT_DOI}"\n'
    f'PreviousVersionDOI = "https://doi.org/{PREVIOUS_DOI}"'
)
replacement = (
    f'DOI = "https://doi.org/{CONCEPT_DOI}"\n'
    f'VersionDOI = "https://doi.org/{VERSION_DOI}"\n'
    f'PreviousVersionDOI = "https://doi.org/{PREVIOUS_DOI}"'
)
if marker not in pyproject:
    raise SystemExit("pyproject DOI marker not found")
write("pyproject.toml", pyproject.replace(marker, replacement, 1))

for path in [
    "src/gpbiometricspy/__init__.py",
    "src/gpbiometricspy/governance_core.py",
    "src/gpbiometricspy/governance_extra.py",
    "src/gpbiometricspy/remaining_core.py",
]:
    text = read(path)
    count = text.count(STABLE)
    if count < 1:
        raise SystemExit(f"{path}: no live {STABLE} literal found")
    write(path, text.replace(STABLE, DEV))

zenodo_path = ROOT / ".zenodo.json"
zenodo = json.loads(zenodo_path.read_text(encoding="utf-8"))
if zenodo.get("version") != STABLE:
    raise SystemExit(f"Unexpected Zenodo version: {zenodo.get('version')!r}")
zenodo["version"] = DEV
zenodo_path.write_text(json.dumps(zenodo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

manifest_path = ROOT / "docs/assets/generated/manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("package_version") != STABLE:
    raise SystemExit(f"Unexpected docs manifest version: {manifest.get('package_version')!r}")
manifest["package_version"] = DEV
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Stable citation identity remains 0.1.3 and receives its minted DOI.
cff = read("CITATION.cff")
if "version: 0.1.3" not in cff or "date-released: 2026-09-05" not in cff:
    raise SystemExit("CITATION.cff stable identity is not 0.1.3")
if re.search(r"(?m)^doi:", cff):
    raise SystemExit("CITATION.cff already contains a DOI")
cff = cff.replace(
    "date-released: 2026-09-05\n",
    f"date-released: 2026-09-05\ndoi: {VERSION_DOI}\n",
    1,
)
write("CITATION.cff", cff)

# Stable-release documentation now records the minted version DOI.
readme = read("README.md")
old_readme = (
    "`gpbiometricspy 0.1.3` is the current stable release. Its version-specific Zenodo DOI "
    "will be recorded after Zenodo ingests the GitHub release; until then the concept DOI "
    "identifies the evolving Python software record."
)
new_readme = (
    f"`gpbiometricspy 0.1.3` is the current stable release. Its version-specific Zenodo DOI is "
    f"**{VERSION_DOI}**; the concept DOI identifies the evolving Python software record."
)
if old_readme not in readme:
    raise SystemExit("README pending-Zenodo sentence not found")
readme = readme.replace(old_readme, new_readme, 1)
anchor = f"- **Software concept DOI:** [`{CONCEPT_DOI}`](https://doi.org/{CONCEPT_DOI})"
if VERSION_DOI not in readme:
    if anchor not in readme:
        raise SystemExit("README citation anchor not found")
    readme = readme.replace(
        anchor,
        f"- **0.1.3 version DOI:** [`{VERSION_DOI}`](https://doi.org/{VERSION_DOI})\n{anchor}",
        1,
    )
if "| Development head |" not in readme:
    readme = readme.replace(
        "| Stable release | **0.1.3** |",
        "| Stable release | **0.1.3** |\n| Development head | **0.1.4.dev0** |",
        1,
    )
write("README.md", readme)

citation = read("docs/citation.md")
old_note = (
    "stable Python release <code>0.1.3</code> (2026-09-05); its version-specific Zenodo DOI "
    "will be added after Zenodo ingests the GitHub release; the software concept DOI is already registered."
)
new_note = (
    f"stable Python release <code>0.1.3</code> (2026-09-05); its version-specific Zenodo DOI is "
    f'<a href="https://doi.org/{VERSION_DOI}">{VERSION_DOI}</a>; the software concept DOI remains '
    "the identifier for the evolving record."
)
if old_note not in citation:
    raise SystemExit("docs/citation.md pending note not found")
citation = citation.replace(old_note, new_note, 1)
pending_line = "- **0.1.3 version DOI:** pending Zenodo ingestion of the `v0.1.3` GitHub release"
if pending_line not in citation:
    raise SystemExit("docs/citation.md pending DOI line not found")
citation = citation.replace(
    pending_line,
    f"- **0.1.3 version DOI:** **[{VERSION_DOI}](https://doi.org/{VERSION_DOI})**",
    1,
)
write("docs/citation.md", citation)

index = read("docs/index.md")
old_index = (
    "The 0.1.3 version DOI will be added after Zenodo ingests the GitHub release. "
    "The evolving software concept DOI is"
)
if old_index not in index:
    raise SystemExit("docs/index.md pending DOI text not found")
index = index.replace(
    old_index,
    f"The 0.1.3 version DOI is [{VERSION_DOI}](https://doi.org/{VERSION_DOI}). "
    "The evolving software concept DOI is",
    1,
)
write("docs/index.md", index)

validation = read("VALIDATION.md")
old_validation = (
    "- public PyPI release: `gpbiometricspy 0.1.2`;\n"
    "- Zenodo version DOI: `10.5281/zenodo.22150873`;\n"
    "- Zenodo concept DOI: `10.5281/zenodo.22150872`;"
)
if old_validation in validation:
    validation = validation.replace(
        old_validation,
        f"- public PyPI release: `gpbiometricspy 0.1.3`;\n"
        f"- Zenodo version DOI: `{VERSION_DOI}`;\n"
        f"- previous 0.1.2 version DOI: `{PREVIOUS_DOI}`;\n"
        f"- Zenodo concept DOI: `{CONCEPT_DOI}`;",
        1,
    )
if VERSION_DOI not in validation:
    validation += (
        "\n\n### 0.1.3 post-release archival verification\n\n"
        "- Public PyPI 0.1.3 wheel/sdist hashes match the GitHub Release exactly.\n"
        "- Clean public-index installs passed on Python 3.11 and 3.14 with Studio included.\n"
        f"- Zenodo 0.1.3 version DOI: `{VERSION_DOI}`.\n"
        f"- Software concept DOI: `{CONCEPT_DOI}`.\n"
    )
write("VALIDATION.md", validation)

checklist = read("RELEASE_CHECKLIST.md")
if VERSION_DOI not in checklist:
    checklist += (
        "\n\n### 0.1.3 post-release closeout\n\n"
        "- [x] Protected PyPI Trusted Publishing completed successfully.\n"
        "- [x] Public PyPI JSON hashes match the GitHub Release wheel and sdist.\n"
        "- [x] Clean public-index installs passed on Python 3.11 and 3.14, including Studio launchers.\n"
        f"- [x] Zenodo ingested `v0.1.3`; version DOI: `{VERSION_DOI}`.\n"
        f"- [x] Concept DOI remains `{CONCEPT_DOI}`.\n"
        "- [x] Move repository development identity to `0.1.4.dev0` after the immutable 0.1.3 release.\n"
    )
write("RELEASE_CHECKLIST.md", checklist)

notes = read("RELEASE_NOTES_0.1.3.md")
if VERSION_DOI not in notes:
    notes += (
        "\n\n## Post-release archival record\n\n"
        "- PyPI: `gpbiometricspy 0.1.3` published through Trusted Publishing with Sigstore attestations.\n"
        f"- Zenodo version DOI: **[{VERSION_DOI}](https://doi.org/{VERSION_DOI})**.\n"
        f"- Zenodo software concept DOI: **[{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI})**.\n"
        "- Public-index wheel/sdist hashes were independently revalidated against the GitHub Release and "
        "clean installs passed on Python 3.11 and 3.14.\n"
    )
write("RELEASE_NOTES_0.1.3.md", notes)

release_page = read("docs/release-0.1.3.md")
if VERSION_DOI not in release_page:
    release_page += (
        "\n\n## Archival identifiers\n\n"
        f"- Version DOI: **[{VERSION_DOI}](https://doi.org/{VERSION_DOI})**\n"
        f"- Software concept DOI: **[{CONCEPT_DOI}](https://doi.org/{CONCEPT_DOI})**\n"
    )
write("docs/release-0.1.3.md", release_page)

# Validation/report helper follows the live package identity rather than a hard-coded release.
finalize = read("scripts/finalize_validation.py")
if '"gpbiometricspy 0.1.3 RELEASE VALIDATION",' not in finalize:
    raise SystemExit("finalize_validation.py release title not found")
finalize = finalize.replace(
    '"gpbiometricspy 0.1.3 RELEASE VALIDATION",',
    'f"gpbiometricspy {gp.__version__} VALIDATION",',
    1,
)
write("scripts/finalize_validation.py", finalize)

# Tests distinguish live development identity from latest stable citation metadata.
post = read("tests/test_post_release_completeness.py")
replacements = {
    "def test_stable_version_and_contract():\n    assert gp.__version__=='0.1.3'":
        "def test_development_version_and_contract():\n    assert gp.__version__=='0.1.4.dev0'",
    "assert manifest['package_version']=='0.1.3'": "assert manifest['package_version']=='0.1.4.dev0'",
    'assert zenodo["version"] == "0.1.3"': 'assert zenodo["version"] == "0.1.4.dev0"',
    'assert "doi: 10.5281/zenodo.22150873" not in cff':
        f'assert "doi: {VERSION_DOI}" in cff\n    assert "doi: 10.5281/zenodo.22150873" not in cff',
    'assert "10.5281/zenodo.22150872" in readme and "10.5281/zenodo.22150873" in readme':
        f'assert "{CONCEPT_DOI}" in readme and "{VERSION_DOI}" in readme and "{PREVIOUS_DOI}" in readme',
}
for old, new in replacements.items():
    if old not in post:
        raise SystemExit(f"post-release test marker not found: {old!r}")
    post = post.replace(old, new, 1)
write("tests/test_post_release_completeness.py", post)

coverage = read("tests/test_coverage_completion_remaining_core.py")
old_coverage = "assert out['package_version']=='0.1.3'"
if old_coverage not in coverage:
    raise SystemExit("remaining_core fallback assertion not found")
coverage = coverage.replace(old_coverage, "assert out['package_version']=='0.1.4.dev0'", 1)
write("tests/test_coverage_completion_remaining_core.py", coverage)

# Permanent identity audit supports stable and development states.
audit = r'''from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    stable = re.fullmatch(r"\d+\.\d+\.\d+", version) is not None
    development = re.fullmatch(r"\d+\.\d+\.\d+\.dev\d+", version) is not None
    if not (stable or development):
        raise SystemExit(f"Package version must be stable X.Y.Z or development X.Y.Z.devN, got {version!r}")

    init_text = (ROOT / "src/gpbiometricspy/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']\s*$', init_text)
    package_version = match.group(1) if match else None

    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    cff_match = re.search(r"(?m)^version:\s*([^\s]+)\s*$", cff)
    cff_version = cff_match.group(1) if cff_match else None

    live_values = {
        "pyproject": version,
        "package": package_version,
        "zenodo": zenodo.get("version"),
    }
    if any(value != version for value in live_values.values()):
        raise SystemExit(f"Live package identity mismatch: {live_values}")

    generated = json.loads((ROOT / "docs/assets/generated/manifest.json").read_text(encoding="utf-8"))
    if generated.get("package_version") != version:
        raise SystemExit(
            "Generated documentation manifest version mismatch: "
            f"{generated.get('package_version')!r} vs {version!r}"
        )

    if stable:
        if cff_version != version:
            raise SystemExit(f"Stable citation identity mismatch: CFF={cff_version!r}, package={version!r}")

        release_surfaces = [ROOT / "src", ROOT / "tests", ROOT / "docs", ROOT / "scripts"]
        offenders: list[str] = []
        for root in release_surfaces:
            for path in root.rglob("*"):
                if not path.is_file() or path == Path(__file__).resolve():
                    continue
                if path.suffix not in {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".cff"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if f"{version}.dev" in text:
                    offenders.append(str(path.relative_to(ROOT)))

        for path in [
            ROOT / "README.md",
            ROOT / "CHANGELOG.md",
            ROOT / "VALIDATION.md",
            ROOT / "CITATION.cff",
            ROOT / ".zenodo.json",
            ROOT / "RELEASE_CHECKLIST.md",
        ]:
            if f"{version}.dev" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))

        if offenders:
            raise SystemExit("Development-version literals remain: " + ", ".join(sorted(set(offenders))))
        print(f"release identity PASS: gpbiometricspy {version}")
        return

    # Development main keeps CFF pinned to the latest stable archival release.
    if cff_version is None or not re.fullmatch(r"\d+\.\d+\.\d+", cff_version):
        raise SystemExit(f"Development citation must point to a stable release, got CFF={cff_version!r}")
    if cff_version == version:
        raise SystemExit("Development CFF must not cite the development package version")
    print(f"development identity PASS: gpbiometricspy {version}; latest stable citation {cff_version}")


if __name__ == "__main__":
    main()
'''
write("scripts/audit_release_identity.py", audit)

# Final contract checks before committing.
assert 'version = "0.1.4.dev0"' in read("pyproject.toml")
assert '__version__ = "0.1.4.dev0"' in read("src/gpbiometricspy/__init__.py")
assert json.loads(read(".zenodo.json"))["version"] == DEV
assert json.loads(read("docs/assets/generated/manifest.json"))["package_version"] == DEV
assert "version: 0.1.3" in read("CITATION.cff")
assert f"doi: {VERSION_DOI}" in read("CITATION.cff")
assert VERSION_DOI in read("docs/citation.md")
print("post-release closeout edits applied")
