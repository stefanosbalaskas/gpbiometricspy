# Windows upgrade-policy readiness

## Certified product/release-engineering identity

The Windows upgrade/reinstall/downgrade policy was certified on exact product/release-engineering commit:

`23baed89f4ade5d860d7e5985ef67007a38c44bf`

This certification is independent of any later documentation-only commit. The pull request remained draft and no release artifact was published.

## Policy

The per-user Inno Setup installer keeps the stable AppId:

`fd3ca1af-0ebb-5061-9c59-f7ab1079252e`

Version ordering uses the Windows fixed numeric file version rather than the PEP 440 display version. For the current development line the target is `0.1.6.0` while the product display version remains `0.1.6`.

The installer now:

- preserves the previous application directory, group and task choices for repair/upgrade;
- retains `PrivilegesRequired=lowest` and does not reuse a previous privilege mode;
- stores the installed numeric file version in a private current-user registry marker that is removed on uninstall;
- falls back to the installed executable's fixed file version for installations that predate that marker;
- allows first install, same-version repair and an older-to-newer in-place upgrade;
- blocks a newer-to-older downgrade before payload mutation;
- fails closed when an existing installation is detected but its version cannot be verified.

## Exact-head workflow certification

All fifteen pull-request workflow families completed successfully on the certified SHA:

| Workflow | Run | Run ID |
| --- | ---: | ---: |
| `tests` | #473 | `34589697316` |
| `studio` | #258 | `34589697360` |
| `studio-e2e` | #229 | `34589697322` |
| `studio-production` | #230 | `34589697396` |
| `studio-packaging` | #37 | `34589697375` |
| `studio-signing-readiness` | #22 | `34589697415` |
| `studio-installer-readiness` | #16 | `34589697341` |
| `studio-windowed-readiness` | #11 | `34589697380` |
| `studio-windowed-installer-readiness` | #9 | `34589697320` |
| `studio-release-provenance-readiness` | #5 | `34589697354` |
| `branch-coverage` | #271 | `34589697315` |
| `deep-parity` | #462 | `34589697382` |
| `interoperability` | #461 | `34589697306` |
| `docs` | #243 | `34589697289` |
| `CodeQL` | #464 | `34589697335` |

The standard packaging workflow intentionally leaves the Nuitka comparison as a manual `workflow_dispatch` evaluation; the required PyInstaller packaging jobs passed.

## Upgrade-policy evidence

`studio-windowed-installer-readiness` #9 produced artifact `studio-windowed-installer-readiness-evidence`:

- artifact ID: `10195507157`;
- artifact ZIP SHA-256: `fb113ae228bb3abdb329561ef70a957fa3a3bc7c06f5743d5e42df11abb8c7d1`;
- release artifact: `false`;
- installer published: `false`;
- installer signed: `false`;
- install scope: current user;
- elevation required: `false`;
- version authority: Windows fixed file version;
- target file version: `0.1.6.0`;
- migration fallback: installed executable fixed version;
- first install allowed: `true`;
- custom install path preserved: `true`;
- migration fallback repair allowed/restored source bytes: `true` / `true`;
- same-version repair allowed/restored source bytes: `true` / `true`;
- in-place upgrade: `0.1.5.0` -> `0.1.6.0`, allowed and source bytes restored;
- downgrade attempt: `0.1.7.0` -> `0.1.6.0`, blocked with setup exit code `7`;
- blocked downgrade payload unchanged: `true`;
- blocked downgrade marker unchanged: `true`;
- upgrade-policy registry marker removed on uninstall: `true`;
- uninstall registration removed: `true`;
- payload files removed: `true`;
- Python `3.14.7`, PyInstaller `6.22.2`, pywebview `6.2.1`.

Independent artifact inspection confirmed no `.exe`, `.dll`, `.pfx`, `.p12`, `.pem` or `.key` files were retained.

The retained setup logs directly record:

- `Upgrade policy: first install allowed; target=0.1.6.0`;
- `Upgrade policy: same-version repair allowed; installed=0.1.6.0; target=0.1.6.0; source=executable` for migration fallback;
- the same same-version repair with `source=registry` after marker migration;
- `Upgrade policy: in-place upgrade allowed; installed=0.1.5.0; target=0.1.6.0; source=registry`;
- `Upgrade policy: downgrade blocked; installed=0.1.7.0; target=0.1.6.0; source=registry` before payload mutation.

The same workflow also reconfirmed the existing windowed-installer contract: PE subsystem `IMAGE_SUBSYSTEM_WINDOWS_GUI`, no attached console, byte-identical installed executable, local/public WebView2 DOM readiness without external Python, Evergreen Runtime prerequisite detection, clean uninstall, and diagnostics-only evidence retention.

## Distribution boundary

This is an engineering/readiness certification, not a redistributable release. Production distribution still requires the trusted production code-signing identity/service, RFC 3161-compatible SHA-256 timestamping, final branding/icon review, signed-artifact provenance verification, and human Windows install/upgrade/uninstall plus first-session UX validation. Stable `0.1.5`, GitHub Release, PyPI and Zenodo remain untouched.
