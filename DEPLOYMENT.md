# gpbiometricspy Studio deployment

This repository exposes two deliberately different Studio entrypoints:

| Entrypoint | Intended use | External uploads |
| --- | --- | --- |
| `app.py` | Public synthetic demonstration | **Blocked in the UI and fail-closed on the server** |
| `studio/app.py` | Local Positron use or an authenticated/private deployment | Enabled with the existing validation and size limits |

The scientific package remains the computational engine in both cases. Deployment code lives outside `src/gpbiometricspy/` and must not fork scientific algorithms.

## Public Posit Connect Cloud deployment

Current Posit Connect Cloud guidance for Shiny for Python requires a GitHub repository containing the primary Python file and a `requirements.txt`. This repository keeps both at the root for the public deployment:

- primary file: `app.py`
- dependency file: `requirements.txt`
- application object: `app`

The root entrypoint imports `studio.public_demo`, which forces `GPBIOMETRICSPY_STUDIO_MODE=public-demo` before the full Studio UI is constructed.

### Publish from GitHub

1. Sign in to Posit Connect Cloud.
2. Choose **Publish** and select **Shiny**.
3. Select `stefanosbalaskas/gpbiometricspy` and the branch to publish.
4. Select `app.py` as the primary file.
5. Select a supported Python version. Python 3.11 and 3.14 are both covered by the Studio production and browser matrices; the package itself supports Python 3.11–3.14.
6. Keep automatic republishing on push only if the deployment should follow the selected branch automatically.
7. Do not add secrets for the public synthetic demo; it does not require external credentials.

Official references:

- https://docs.posit.co/connect-cloud/user/content/shiny.html
- https://docs.posit.co/connect-cloud/user/publish/github.html
- https://docs.posit.co/connect-cloud/user/platform/python.html

## Public-demo security boundary

The public app is intentionally not a research-data upload service.

`studio.public_demo` replaces all current external-file consumers with fail-closed guards:

- Gazepoint biometric dataset upload;
- AOI definition upload;
- external event-log upload;
- secondary biometric stream upload;
- project-recipe upload/restore.

The public UI also removes file-input affordances and related restore/load buttons. This UI treatment is only a usability measure; the server-side guards are the security boundary.

Public mode additionally enables Shiny error sanitization so unexpected server exceptions are not rendered with internal detail to anonymous users.

The public banner states that the deployment is synthetic-data-only and that participant data should not be submitted.

## Local Positron / controlled research use

For the full Studio with research-data intake:

```powershell
python -m pip install -e ".[studio]"
shiny run --reload studio/app.py
```

Opening `studio/app.py` in Positron and choosing **Run Shiny App** uses the same full local entrypoint.

`GPBIOMETRICSPY_STUDIO_MODE` defaults to `local`. Unknown values are rejected instead of silently falling back to a permissive mode.

## Self-hosted Posit Connect

Install the publishing CLI in the project environment:

```bash
python -m pip install rsconnect-python
```

Register the server using a Connect API key, following your organization’s credential policy:

```bash
rsconnect add --server https://connect.example.org/ --name my-connect --api-key "$CONNECT_API_KEY"
```

### Public synthetic deployment

From the repository root, the default `app.py` / `app` entrypoint is sufficient:

```bash
rsconnect deploy shiny -n my-connect .
```

An explicit equivalent is:

```bash
rsconnect deploy shiny -n my-connect --entrypoint app:app .
```

### Authenticated/full Studio deployment

Use the full Studio module explicitly:

```bash
rsconnect deploy shiny -n my-connect --entrypoint studio.app:app .
```

Only use the full deployment where authentication, access control, storage/privacy policy, and institutional handling requirements for research data have been decided.

To generate a manifest for a git-backed/self-hosted workflow:

```bash
rsconnect write-manifest shiny --entrypoint app:app .
```

Official references:

- https://docs.posit.co/connect/user/shiny-python/
- https://docs.posit.co/connect/user/publishing-cli-apps/
- https://docs.posit.co/connect/user/manifest/

## Dependency reconstruction

`requirements.txt` is intentionally small:

```text
.
shiny>=1.7,<2
```

The `.` line installs this repository’s Python package through `pyproject.toml`, which supplies NumPy, pandas, SciPy, and matplotlib. Shiny remains an application dependency rather than a hard dependency of the scientific library.

The production CI matrix installs from this exact `requirements.txt` rather than from the developer extra, so dependency reconstruction is continuously checked using the same contract expected by Connect Cloud.

## Runtime and performance smoke tests

Run the production path locally:

```bash
python -m studio.production
```

or write machine-readable metrics:

```bash
python -m studio.production --json studio-production-metrics.json
```

The smoke profile exercises:

1. bundled synthetic kiosk loading;
2. lightweight package-native inspection;
3. foundation QC;
4. coarse Python allocation tracking.

The runtime limits are deliberately broad regression tripwires rather than benchmarks. Performance claims should be based on dedicated controlled profiling, not shared CI timings.

## Accessibility and responsive hardening

Studio includes a shared stylesheet that provides:

- visible keyboard focus treatment;
- a keyboard-accessible skip link;
- an English document language declaration;
- live status semantics for project-level feedback;
- reduced-motion handling;
- long-text wrapping;
- mobile-width constraints and responsive overflow protection.

Browser CI checks both the normal Studio and the public deployment using Chromium on Python 3.11 and 3.14, including a narrow mobile viewport. Automated checks reduce regression risk but do **not** constitute a WCAG conformance certification; manual keyboard, screen-reader, contrast, zoom, and task-based accessibility review is still required before making a formal WCAG 2.2 AA claim.

## Production checklist

Before publishing a public URL:

- confirm the primary file is **root `app.py`**, not `studio/app.py`;
- confirm the deployment log installs from root `requirements.txt` successfully;
- confirm the public synthetic-only banner is visible;
- confirm no file chooser is visible anywhere in the public app;
- load the bundled demo and run foundation QC;
- verify the browser E2E and `studio-production` workflows are green on the exact deployed commit;
- set sharing/access policy in Connect Cloud or Posit Connect intentionally;
- do not add real participant files, private AOI definitions, external event logs, or project recipes to a public deployment;
- review compute limits and session behavior for the selected hosting plan;
- perform manual accessibility testing before advertising WCAG conformance.
