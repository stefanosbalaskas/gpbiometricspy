from __future__ import annotations
from _shared import *
manifest=gp.gazepoint_interoperability_manifest(); audit=gp.audit_gazepoint_interoperability_versions(manifest=manifest)
with tempfile.TemporaryDirectory() as td: written=gp.write_gazepoint_interoperability_audit(audit,output_dir=td)
finish('interoperability-version-testing',manifest=manifest,audit=audit,written=written)
