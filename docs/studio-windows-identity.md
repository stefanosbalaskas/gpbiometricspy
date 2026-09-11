# Studio Windows application identity checkpoint

The Windows application-identity tranche for the gpbiometricspy Studio `0.1.6` development line is certified at product-code SHA:

`1f0ff7df4bcead57767fa04b9fc8c3dde565c432`

At that exact SHA all ten pull-request workflow families completed successfully:

- `tests` #450;
- `studio` #235;
- `studio-e2e` #206;
- `studio-production` #207;
- `studio-packaging` #14;
- `branch-coverage` #248;
- `deep-parity` #439;
- `interoperability` #438;
- `docs` #220;
- CodeQL #441.

## Identity source of truth

Windows identity is generated, not maintained as a second handwritten version source.

- `pyproject.toml` supplies the package version.
- The current PEP 440 ProductVersion is `0.1.6.dev0`.
- The corresponding four-integer Windows FileVersion is `0.1.6.0`.
- `LICENSE` supplies the legal copyright string: `Copyright (c) 2026 Stefanos Balaskas`.
- No CompanyName is fabricated.
- The shared ProductName is `gpbiometricspy Studio`.
- Each target retains a truthful `InternalName` and `OriginalFilename`.

The generated resources are:

- `version-info.txt`, consumed by PyInstaller as the Windows version resource;
- `gpbiometricspy-studio.ico`, a deterministic multi-resolution evaluation icon;
- `windows-identity.json`, which binds expected identity fields and SHA-256 fingerprints for the icon and version resource.

The current icon is deliberately an **evaluation/reproducibility asset**, not an immutable final branding decision. It is a simple geometric Studio mark generated from source so packaging identity can be certified before final visual branding is selected.

## Fail-closed verification

Every PyInstaller Windows build now follows the same sequence:

1. generate identity resources from repository metadata;
2. freeze the executable;
3. inspect the compiled EXE through Windows `FileVersionInfo`;
4. compare all expected string and fixed numeric version fields;
5. extract the executable's associated icon and compare its 32-pixel frame pixel-by-pixel against the generated source icon;
6. only after identity passes, execute the existing external-Python-independence and browser/WebView2 runtime contracts.

The build therefore cannot pass merely because a version file or icon exists beside the executable. The resources must actually be embedded in the compiled PE executable and match the generated source of truth.

## Cross-build determinism

`studio-packaging` run #14 (`34547225854`) passed all six required PyInstaller jobs: onedir, onefile, and native WebView2 on Python 3.11 and 3.14.

All six retained diagnostic artifacts record:

- `windows_identity_verified=true`;
- ProductName `gpbiometricspy Studio`;
- ProductVersion `0.1.6.dev0`;
- FileVersion `0.1.6.0`;
- identical icon SHA-256:
  `cba6b92fdf2e35f84a0f033afdb5fc25cd2583c8de1c79a970e6670ab01062dc`.

Version-resource fingerprints are deterministic across Python versions within each target:

| Target | Version-resource SHA-256 |
| --- | --- |
| browser onedir | `d5c3586a71d083f2e599a11d6c8b7978b027bbfc6bbf942e6af76831533883cb` |
| browser onefile | `d1b1636bba8b6628401d4005fe7007f12bce4f37cf53917c2db49457512b1f4a` |
| native WebView2 | `fa5623dbbef4e32015d9af4c20f1af4d7e97ab533be31fe7d5122699397b3201` |

The hashes differ between targets because their truthful `InternalName`, `OriginalFilename`, and, for the native target, description differ. They are identical between Python 3.11 and 3.14 for the same target.

## Same-run diagnostic measurements

Identity embedding did not alter the packaging architecture or runtime contract. Same-run diagnostics at the certified SHA were:

| Python | Form | Size | Startup / HTTP readiness |
| --- | --- | ---: | ---: |
| 3.11.9 | onedir browser | 235,338,746 bytes | 3.731 s |
| 3.14.7 | onedir browser | 239,653,496 bytes | 4.512 s |
| 3.11.9 | onefile browser | 98,280,539 bytes | 9.615 s |
| 3.14.7 | onefile browser | 101,632,566 bytes | 8.442 s |
| 3.11.9 | native WebView2 | 247,267,397 bytes | local 5.598 s; public 4.169 s |
| 3.14.7 | native WebView2 | 249,806,121 bytes | local 3.833 s; public 3.428 s |

These CI timings remain comparative diagnostics rather than end-user performance guarantees.

## Decision and next boundary

Windows application identity is now a certified packaging property. PyInstaller remains the packaging baseline, native WebView2 remains the preferred desktop-presentation candidate, and browser launch remains a fallback/diagnostic path.

The next release-readiness boundary is **code-signing policy and reproducible unsigned-to-signed provenance**. That boundary must not put private certificates or secrets in the repository. It should define an unsigned reproducible artifact, checksum/provenance evidence, a separate signing operation when authorized credentials exist, and Authenticode verification for signed release artifacts. Installer/uninstaller engineering follows after the signing/provenance boundary is defined and certified.
