
# Studio deployment and support

gpbiometricspy Studio has three deliberately different product surfaces: a local research workspace, a desktop-style local launcher, and a synthetic-only public demonstration. They share one scientific backend but **do not share the same data boundary**.

## Preflight: run Studio Doctor

After installing the Studio extra, run:

```bash
python -m pip install "gpbiometricspy[studio]"
gpbiometricspy-studio-doctor
```

The doctor checks the installed Shiny dependency, packaged Studio application/CSS assets, runtime mode and ability to bind a loopback port. It does not inspect raw biometric samples and does not transmit diagnostics.

Machine-readable output is available for support and deployment probes:

```bash
gpbiometricspy-studio-doctor --json
```

## Local research workspace

Use the full Studio when files remain on the researcher's controlled machine:

```bash
gpbiometricspy-studio
```

Or use the desktop-style launcher, which chooses an available loopback port and opens the browser automatically:

```bash
gpbiometricspy-studio-desktop
```

The browser is only the interface. The Shiny process and analysis run locally through the installed Python environment.

## Public demonstration

The public boundary is intentionally synthetic-only:

```bash
gpbiometricspy-studio-public
```

In this mode, external uploads are disabled and application errors are sanitized. A public anonymous deployment should never be converted into a participant-data upload service merely by adding a file control.

A public deployment should preserve these invariants:

- `GPBIOMETRICSPY_STUDIO_MODE=public-demo`;
- no external research-data upload path;
- sanitized application errors;
- HTTPS at the hosting layer;
- dependency and image updates under version control;
- synthetic browser regression tests before deployment;
- resource limits appropriate for an anonymous demonstration.

## Authenticated/private deployment

A private institutional deployment is possible, but authentication is not supplied by Studio itself. Put the application behind an institution-approved identity/access layer or a managed Shiny platform with authentication.

Before enabling research-data uploads, define all of the following outside the scientific package:

1. who is authorized to access the service;
2. where uploaded files and temporary files reside;
3. retention and deletion timing;
4. encryption and backup policy;
5. request and audit logging policy;
6. file-size and resource limits;
7. incident response and recovery ownership.

Do not advertise a private deployment as suitable for identifiable or sensitive research data until those institutional controls are actually in place.

## Project continuity

Studio project recipes are deliberately metadata-only. They persist project identity, dataset fingerprint, annotations, provenance and analysis inventory without embedding raw biometric rows or cached result tables.

The restore sequence is:

```text
reopen Studio
  → load the source dataset
  → open Report → Project recipe
  → validate the recipe
  → exact SHA-256 fingerprint match
  → restore metadata
  → recompute analyses or use the replay script
```

The project name is restored with the recipe. Studio also suggests a project-derived export filename to make multi-project work easier to organize.

## Troubleshooting startup

Start with:

```bash
gpbiometricspy-studio-doctor
```

If the doctor is green but the browser does not open, run:

```bash
gpbiometricspy-studio-desktop --no-browser
```

and open the printed loopback URL manually. If port `8765` is busy, the launcher automatically selects another available port.

For reproducible support requests, share the doctor output and the package version. Do **not** attach participant data merely to demonstrate an installation problem.
