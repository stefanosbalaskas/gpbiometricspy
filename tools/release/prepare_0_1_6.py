from __future__ import annotations

import importlib.util
from pathlib import Path

_IMPL_PATH = Path(__file__).with_name("prepare_0_1_6_impl.py")
_spec = importlib.util.spec_from_file_location("gpbiometricspy_release_prepare_impl", _IMPL_PATH)
if _spec is None or _spec.loader is None:
    raise SystemExit("Could not load deterministic release preparation implementation")
_prep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_prep)
_IMPL_PATH.unlink()


def _assert_no_dev_literals() -> None:
    needle = "0.1.6" + ".dev0"
    offenders: list[str] = []
    for path in _prep.ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".toml", ".cff", ".yml", ".yaml", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if needle in text:
            offenders.append(str(path.relative_to(_prep.ROOT)))
    if offenders:
        raise SystemExit("development-version literals remain: " + ", ".join(sorted(offenders)))


_prep.assert_no_dev_literals = _assert_no_dev_literals

if __name__ == "__main__":
    _prep.main()
