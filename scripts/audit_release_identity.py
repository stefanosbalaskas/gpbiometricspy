from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Release version must be stable X.Y.Z, got {version!r}")

    init_text = (ROOT / "src/gpbiometricspy/__init__.py").read_text(encoding="utf-8")
    match = re.search(r'(?m)^__version__\s*=\s*["\']([^"\']+)["\']\s*$', init_text)
    package_version = match.group(1) if match else None

    zenodo = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    cff_match = re.search(r"(?m)^version:\s*([^\s]+)\s*$", cff)
    cff_version = cff_match.group(1) if cff_match else None

    values = {
        "pyproject": version,
        "package": package_version,
        "zenodo": zenodo.get("version"),
        "citation": cff_version,
    }
    if any(value != version for value in values.values()):
        raise SystemExit(f"Release identity mismatch: {values}")

    generated = json.loads((ROOT / "docs/assets/generated/manifest.json").read_text(encoding="utf-8"))
    if generated.get("package_version") != version:
        raise SystemExit(
            "Generated documentation manifest version mismatch: "
            f"{generated.get('package_version')!r} vs {version!r}"
        )

    release_surfaces = [
        ROOT / "src",
        ROOT / "tests",
        ROOT / "docs",
        ROOT / "scripts",
    ]
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


if __name__ == "__main__":
    main()
