from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{path}: expected {count} occurrence(s) of {old!r}, found {found}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# Advance only the live development identity; the stable CFF citation remains 0.1.6.
replace("pyproject.toml", 'version = "0.1.6"', 'version = "0.1.7.dev0"')
replace(".zenodo.json", '"version": "0.1.6"', '"version": "0.1.7.dev0"')
replace("src/gpbiometricspy/__init__.py", '__version__ = "0.1.6"', '__version__ = "0.1.7.dev0"')
replace("src/gpbiometricspy/governance_core.py", "package_version='0.1.6'", "package_version='0.1.7.dev0'")
replace("src/gpbiometricspy/governance_extra.py", "'gpbiometricspy_version':'0.1.6'", "'gpbiometricspy_version':'0.1.7.dev0'")
replace("src/gpbiometricspy/remaining_core.py", 'version = "0.1.6"', 'version = "0.1.7.dev0"')
replace("docs/assets/generated/manifest.json", '"package_version": "0.1.6"', '"package_version": "0.1.7.dev0"')
replace("tests/test_post_release_completeness.py", "assert gp.__version__=='0.1.6'", "assert gp.__version__=='0.1.7.dev0'")
replace("tests/test_post_release_completeness.py", "assert manifest['package_version']=='0.1.6'", "assert manifest['package_version']=='0.1.7.dev0'")
replace("tests/test_post_release_completeness.py", 'assert zenodo["version"] == "0.1.6"', 'assert zenodo["version"] == "0.1.7.dev0"')
replace("tests/test_coverage_completion_remaining_core.py", "assert out['package_version']=='0.1.6'", "assert out['package_version']=='0.1.7.dev0'")
replace(
    "README.md",
    "| Stable release | **0.1.6** |\n| Release date | **2026-09-11** |",
    "| Stable release | **0.1.6** |\n| Development head | **0.1.7.dev0** |\n| Release date | **2026-09-11** |",
)

cut = ROOT / ".github/workflows/cut-release.yml"
cut_text = cut.read_text(encoding="utf-8")
old_cut = '''      - name: Dispatch exact-tag release workflow
        if: >-
          steps.release.outputs.eligible == 'true' &&
          steps.current.outputs.current == 'true' &&
          steps.gates.outputs.ready == '1' &&
          steps.tag.outputs.created == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          TAG="${{ steps.release.outputs.tag }}"
          gh workflow run release.yml --ref "$TAG" -f tag="$TAG"
          echo "Dispatched release.yml on exact $TAG; the workflow run SHA is therefore the immutable release commit."
'''
new_cut = '''      - name: Dispatch exact-tag release workflow and trusted publication
        if: >-
          steps.release.outputs.eligible == 'true' &&
          steps.current.outputs.current == 'true' &&
          steps.gates.outputs.ready == '1' &&
          steps.tag.outputs.created == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          TAG="${{ steps.release.outputs.tag }}"
          TARGET_SHA="${{ steps.current.outputs.sha }}"
          gh workflow run release.yml --ref "$TAG" -f tag="$TAG"
          echo "Dispatched release.yml on exact $TAG; waiting for the canonical release result."

          RUN_ID=""
          for _ in $(seq 1 60); do
            RUN_ID="$(gh run list --workflow release.yml --commit "$TARGET_SHA" --event workflow_dispatch --limit 20 \\
              --json databaseId,createdAt \\
              --jq 'sort_by(.createdAt) | last | .databaseId // empty')"
            if [[ -n "$RUN_ID" ]]; then
              break
            fi
            sleep 5
          done
          test -n "$RUN_ID" || { echo "Canonical release workflow did not materialize." >&2; exit 1; }
          gh run watch "$RUN_ID" --exit-status

          gh workflow run pypi.yml --ref main -f tag="$TAG"
          echo "Canonical release succeeded; dispatched guarded PyPI Trusted Publishing recovery path for $TAG."
'''
if cut_text.count(old_cut) != 1:
    raise SystemExit("cut-release.yml: exact dispatch block not found once")
cut.write_text(cut_text.replace(old_cut, new_cut), encoding="utf-8")

policy = ROOT / "tests/test_production_release_handoff_wiring.py"
policy_text = policy.read_text(encoding="utf-8")
old_policy = '''    assert 'gh workflow run release.yml --ref "$TAG" -f tag="$TAG"' in workflow
    assert 'gh workflow run release.yml --ref main' not in workflow
'''
new_policy = '''    assert 'gh workflow run release.yml --ref "$TAG" -f tag="$TAG"' in workflow
    assert 'gh run watch "$RUN_ID" --exit-status' in workflow
    assert 'gh workflow run pypi.yml --ref main -f tag="$TAG"' in workflow
    assert workflow.index('gh run watch "$RUN_ID" --exit-status') < workflow.index('gh workflow run pypi.yml --ref main -f tag="$TAG"')
    assert 'gh workflow run release.yml --ref main' not in workflow
'''
if policy_text.count(old_policy) != 1:
    raise SystemExit("release wiring test: expected cut-release assertions not found once")
policy.write_text(policy_text.replace(old_policy, new_policy), encoding="utf-8")

recovery = ROOT / ".github/workflows/recover-pypi-v0.1.6.yml"
recovery.write_text('''name: recover-pypi-v0.1.6

on:
  push:
    branches: [main]
    paths:
      - .github/workflows/recover-pypi-v0.1.6.yml

permissions:
  contents: read
  actions: write

concurrency:
  group: recover-pypi-v0.1.6
  cancel-in-progress: false

jobs:
  recover:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7.0.1
        with:
          fetch-depth: 0

      - name: Verify immutable 0.1.6 release and dispatch guarded Trusted Publishing
        env:
          GH_TOKEN: ${{ github.token }}
        shell: bash
        run: |
          set -euo pipefail
          TAG="v0.1.6"
          EXPECTED_SHA="a3ad2d82447011284da8ea97d35bb7aea2ee8206"
          LIVE_VERSION="$(python - <<'PY'
          import pathlib, tomllib
          print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
          PY
          )"
          test "$LIVE_VERSION" = "0.1.7.dev0"

          git fetch origin "refs/tags/$TAG:refs/tags/$TAG" --force
          test "$(git rev-parse "refs/tags/$TAG^{commit}")" = "$EXPECTED_SHA"

          RELEASE_RUN="$(gh run list --workflow release.yml --commit "$EXPECTED_SHA" --event workflow_dispatch --limit 30 \\
            --json databaseId,conclusion,createdAt \\
            --jq '[.[] | select(.conclusion == "success")] | sort_by(.createdAt) | last | .databaseId // empty')"
          test -n "$RELEASE_RUN" || { echo "No successful canonical release exists for $TAG." >&2; exit 1; }

          if curl --fail --silent --show-error "https://pypi.org/pypi/gpbiometricspy/0.1.6/json" >/dev/null 2>&1; then
            echo "gpbiometricspy 0.1.6 is already public on PyPI; recovery is an idempotent no-op."
            exit 0
          fi

          gh workflow run pypi.yml --ref main -f tag="$TAG"
          echo "Dispatched the repository's guarded pypi.yml recovery path for $TAG."
''', encoding="utf-8")

print("post-0.1.6 publication recovery preparation complete")
