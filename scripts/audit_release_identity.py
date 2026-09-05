from __future__ import annotations

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
