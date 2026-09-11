# Production desktop release handoff

> **Scope:** this contract applies only when gpbiometricspy Studio is distributed as a standalone Windows executable/installer. It is **not** a prerequisite for the normal Python package, GitHub Release, PyPI publication, or Zenodo archival release.

The automated desktop release-orchestration boundary proves that gpbiometricspy Studio can be built, transiently signed, packaged, installed, verified and uninstalled in CI. That evidence deliberately uses an ephemeral untrusted certificate and **must not** be treated as production signing or human release approval.

A future production Windows desktop release is eligible only after the remaining external and human boundaries are recorded in one fail-closed handoff manifest. Until then, users can install the Python package and launch Studio through its Python entry points; the standalone Windows installer remains an optional distribution channel.

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

The validator is intentionally fail-closed. A missing approval, pending human scenario, untrusted signing record, absent RFC 3161 timestamp, missing attestation/SBOM/checksum digest, malformed hash, or source/tag mismatch makes the **desktop installer handoff** ineligible.

## Required production signing evidence

The desktop record requires all of the following from the actual redistributable executable and installer:

- the production signing provider/service identifier;
- signer subject and certificate thumbprint;
- a verified trusted certificate chain;
- SHA-256 Authenticode digest use;
- verified RFC 3161 timestamping using SHA-256;
- the timestamp authority used;
- SHA-256 digests for the final signed executable and final signed installer.

The validator checks the handoff record for completeness and consistency. The protected production desktop process remains responsible for actually verifying Authenticode trust and timestamp status on the final binaries before recording those fields as passed.

## Protected release-environment evidence

The desktop handoff must also record that the production run occurred in the intended protected release environment and retain SHA-256 identities for:

- the final release attestation/provenance statement;
- the final SBOM;
- the final checksum manifest.

The handoff record itself may be retained with the desktop release evidence. Signing keys and certificate private material must never be attached.

## Human branding approval

The generated CI icon remains evaluation/reproducibility artwork. Production desktop eligibility requires explicit final-icon approval with a human reviewer identity and timezone-aware approval timestamp.

## Representative Windows validation

At least **two representative Windows machines** must be recorded before distributing a production standalone installer. Each machine must identify the Windows version, architecture and WebView2 version, and every required scenario must be marked `pass`:

1. clean install;
2. same-version repair/reinstall;
3. `0.1.5 -> 0.1.6` upgrade;
4. downgrade blocking;
5. uninstall;
6. first-session UX.

The first-session UX check should replay the already documented researcher path: launch, Home/teaching route comprehension, guided synthetic analysis, QC, signal analysis, Reporting, Timeline/Provenance, recipe export, Saved/Unsaved state and safe recovery messaging. Automation remains evidence for functional invariants; this human record is specifically for comprehension, visual hierarchy, perceived friction and real install/launch experience.

## Optional desktop handoff workflow

The completed desktop record is **not committed to the source tree**. Committing a record that names its own source commit would create a circular source-identity problem because adding the record would change the commit SHA.

When a signed standalone Windows distribution is eventually wanted:

1. complete real production signing/timestamping, attestation, branding approval and representative-machine validation;
2. run the manual `studio-production-release-handoff` workflow on `main`;
3. provide the stable tag, the exact 40-character source commit, and the completed **non-secret** evidence JSON;
4. pass the `production-release` GitHub Environment boundary;
5. allow the workflow to verify current-main identity, validate the desktop record, reject secret-looking content, and retain only the evidence JSON plus its SHA-256 manifest.

This workflow remains available as a rigorous desktop-distribution control, but its success is deliberately **not consulted by `cut-release.yml`, `release.yml`, or `pypi.yml`**.

## Python package release and PyPI publication

The stable Python package has a separate package-only publication contract.

`cut-release.yml` requires the exact-current-`main` package/scientific validation matrix:

- tests;
- docs;
- CodeQL;
- deep parity;
- interoperability;
- branch coverage;
- private real-data validation;
- Studio;
- Studio E2E;
- Studio production-mode validation.

Desktop packaging/signing/installer workflows remain useful engineering evidence but do not block the Python package.

After the immutable tag is created, `cut-release.yml` dispatches `release.yml` **on that exact tag**. `release.yml` additionally requires the tag commit to equal current `main`, rebuilds the wheel and sdist using a source-commit-derived `SOURCE_DATE_EPOCH`, smoke-installs both artifacts, verifies the frozen 406-function contract and Studio entry points, writes `SHA256SUMS.txt`, and writes schema-v2 `RELEASE-METADATA.json`.

`tools/release/validate_stable_release_artifact.py` binds only the exact stable tag/source SHA, checksum manifest, wheel and sdist. It intentionally contains no code-signing or desktop-handoff requirement.

If a GitHub Release already exists, the release workflow downloads the wheel, sdist, checksum manifest and metadata and requires byte-for-byte identity with the newly rebuilt exact-source candidate before treating it as canonical.

## Canonical PyPI publication chain

`pypi.yml` runs only after a successful canonical `release` workflow, or manually as a recovery path that first resolves an already successful canonical release run for the requested stable tag. It then:

1. downloads the `distributions` artifact from that successful release run;
2. requires schema-v2 `RELEASE-METADATA.json` with exact tag/source binding;
3. checks out the exact tag and confirms the source commit remains in `main` history;
4. verifies `SHA256SUMS.txt` and reruns the canonical package-artifact validator;
5. downloads the current GitHub Release package assets and requires byte-for-byte identity with the successful workflow artifact;
6. publishes **only** `canonical-release/dist/` through PyPI Trusted Publishing.

This preserves the important anti-bypass property: a manually substituted GitHub Release, plausible filenames, or a free-standing publisher invocation cannot replace the canonical exact-source package artifact.

## Configure `production-release` before desktop use

The optional manual desktop-handoff job references the GitHub Environment named `production-release`. Repository administrators should retain appropriate deployment restrictions on that environment before using it for a real standalone Windows release.

A workflow run reaching that environment is not, by itself, evidence that a trusted signing operation occurred. The desktop handoff manifest still has to contain the real trusted signer/timestamp, attestation and human-validation evidence and pass the fail-closed validator.

## What the repository template means

The committed desktop template intentionally contains blank identities, `false` approvals and `pending` human outcomes. It is therefore **not desktop-release-eligible**, and CI asserts that it remains rejected. This prevents the template from being mistaken for a completed production attestation.

Only a separately populated record derived from a real protected desktop release, real trusted signing/timestamp verification and actual human validation can satisfy the standalone Windows distribution contract.
