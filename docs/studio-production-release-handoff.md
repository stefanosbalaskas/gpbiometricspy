# Production desktop release handoff

The automated desktop release-orchestration boundary proves that gpbiometricspy Studio can be built, transiently signed, packaged, installed, verified and uninstalled in CI. That evidence deliberately uses an ephemeral untrusted certificate and **must not** be treated as production signing or human release approval.

A production Windows desktop release is eligible only after the remaining external and human boundaries are recorded in one fail-closed handoff manifest.

## Evidence record

Start from:

```text
tools/release/desktop_release_evidence.template.json
```

Copy the template into the protected release workspace and populate it from the actual production run. Do not commit private keys, signing credentials, certificate exports, or redistributable binaries to the repository.

Validate the completed record against the exact tag and exact release commit:

```powershell
python tools/release/validate_desktop_release_evidence.py `
  --manifest desktop-production-evidence.json `
  --expected-tag v0.1.6 `
  --expected-source-commit <40-character-release-SHA>
```

The validator is intentionally fail-closed. A missing approval, pending human scenario, untrusted signing record, absent RFC 3161 timestamp, missing attestation/SBOM/checksum digest, malformed hash, or source/tag mismatch makes the record ineligible.

## Required production signing evidence

The record requires all of the following from the actual redistributable executable and installer:

- the production signing provider/service identifier;
- signer subject and certificate thumbprint;
- a verified trusted certificate chain;
- SHA-256 Authenticode digest use;
- verified RFC 3161 timestamping using SHA-256;
- the timestamp authority used;
- SHA-256 digests for the final signed executable and final signed installer.

The validator checks the handoff record for completeness and consistency. The protected production release process remains responsible for actually verifying Authenticode trust and timestamp status on the final binaries before recording those fields as passed.

## Protected release-environment evidence

The handoff must also record that the production run occurred in the intended protected release environment and retain SHA-256 identities for:

- the final release attestation/provenance statement;
- the final SBOM;
- the final checksum manifest.

The handoff record itself may be attached to the GitHub Release alongside these non-secret evidence files. Signing keys and certificate private material must never be attached.

## Human branding approval

The generated CI icon remains evaluation/reproducibility artwork. Production eligibility requires explicit final-icon approval with a human reviewer identity and timezone-aware approval timestamp.

## Representative Windows validation

At least **two representative Windows machines** must be recorded. Each machine must identify the Windows version, architecture and WebView2 version, and every required scenario must be marked `pass`:

1. clean install;
2. same-version repair/reinstall;
3. `0.1.5 -> 0.1.6` upgrade;
4. downgrade blocking;
5. uninstall;
6. first-session UX.

The first-session UX check should replay the already documented researcher path: launch, Home/teaching route comprehension, guided synthetic analysis, QC, signal analysis, Reporting, Timeline/Provenance, recipe export, Saved/Unsaved state and safe recovery messaging. Automation remains evidence for functional invariants; this human record is specifically for comprehension, visual hierarchy, perceived friction and real install/launch experience.

## What the repository template means

The committed template intentionally contains blank identities, `false` approvals and `pending` human outcomes. It is therefore **not release-eligible**, and CI asserts that it remains rejected. This prevents the template from being mistaken for a completed production attestation.

Only a separately populated record derived from the real protected release, real trusted signing/timestamp verification and actual human validation can satisfy the contract.
