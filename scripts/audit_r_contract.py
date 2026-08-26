from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import gpbiometricspy as gp
assert len(gp.R_EXPORTS) == 406, len(gp.R_EXPORTS)
assert len(set(gp.R_EXPORTS)) == 406
assert set(gp.IMPLEMENTED_EXPORTS).isdisjoint(gp.PENDING_EXPORTS)
assert set(gp.IMPLEMENTED_EXPORTS) | set(gp.PENDING_EXPORTS) == set(gp.R_EXPORTS)
assert all(hasattr(gp, name) for name in gp.R_EXPORTS)
assert len(gp.IMPLEMENTED_EXPORTS) + len(gp.PENDING_EXPORTS) == 406
assert set(gp.IMPLEMENTED_EXPORTS).isdisjoint(gp.PENDING_EXPORTS)
assert set(gp.IMPLEMENTED_EXPORTS) | set(gp.PENDING_EXPORTS) == set(gp.R_EXPORTS)
print("R exports: 406")
print(f"Implemented exports: {len(gp.IMPLEMENTED_EXPORTS)}")
print(f"Explicit pending: {len(gp.PENDING_EXPORTS)}")
print("Exact export registry: PASS")
