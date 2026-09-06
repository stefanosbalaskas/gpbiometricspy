from __future__ import annotations

import argparse
import json
from pathlib import Path

Arc = tuple[str, int, int]


def _coverage_arcs(payload: dict[str, object]) -> set[Arc]:
    arcs: set[Arc] = set()
    files = payload.get("files")
    if not isinstance(files, dict):
        raise ValueError("Coverage JSON must contain a `files` mapping.")
    for path, entry in files.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Coverage entry for {path!r} must be an object.")
        for arc in entry.get("missing_branches", []):
            if not isinstance(arc, list) or len(arc) != 2:
                raise ValueError(f"Malformed missing branch for {path!r}: {arc!r}")
            arcs.add((str(path), int(arc[0]), int(arc[1])))
    return arcs


def _contract_arcs(contract: dict[str, object]) -> set[Arc]:
    entries = contract.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Structural-debt contract must contain an `entries` list.")
    arcs: set[Arc] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"Malformed structural-debt entry: {entry!r}")
        arc = (str(entry["file"]), int(entry["from"]), int(entry["to"]))
        if arc in arcs:
            raise ValueError(f"Duplicate structural-debt entry: {arc!r}")
        rationale = entry.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"Structural-debt entry lacks rationale: {arc!r}")
        arcs.add(arc)
    declared = int(contract.get("structural_missing_count", -1))
    if declared != len(arcs):
        raise ValueError(
            f"Contract structural_missing_count={declared} does not match {len(arcs)} entries."
        )
    return arcs


def _format_arc(arc: Arc) -> str:
    path, source, target = arc
    return f"{path}:{source}->{target}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that raw branch-coverage debt matches the frozen, audited "
            "structural/caller-dominated branch contract exactly."
        )
    )
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("contract_json", type=Path)
    args = parser.parse_args()

    coverage = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    contract = json.loads(args.contract_json.read_text(encoding="utf-8"))

    totals = coverage.get("totals")
    if not isinstance(totals, dict):
        raise ValueError("Coverage JSON must contain a `totals` object.")
    branch_total = int(totals.get("num_branches", 0))
    covered = int(totals.get("covered_branches", 0))
    raw_missing = branch_total - covered
    expected_total = int(contract.get("coverage_denominator", -1))

    actual_arcs = _coverage_arcs(coverage)
    contract_arcs = _contract_arcs(contract)
    unexpected = actual_arcs - contract_arcs
    stale = contract_arcs - actual_arcs

    print("STRUCTURAL BRANCH DEBT AUDIT")
    print("=" * 76)
    print(f"coverage denominator       : {branch_total:,}")
    print(f"contract denominator       : {expected_total:,}")
    print(f"raw covered branches       : {covered:,}/{branch_total:,}")
    print(f"raw missing branches       : {raw_missing:,}")
    print(f"audited structural entries : {len(contract_arcs):,}")
    print(f"unexpected missing branches: {len(unexpected):,}")
    print(f"stale contract entries     : {len(stale):,}")
    print(f"unaudited branch debt      : {len(unexpected):,}")
    if branch_total:
        accounted = covered + len(actual_arcs & contract_arcs)
        print(f"audited branch accounting  : {accounted:,}/{branch_total:,} ({100.0 * accounted / branch_total:.4f}%)")
    print("raw branch coverage remains the coverage.py value; structural accounting does not redefine it.")

    if unexpected:
        print("\nUnexpected missing branches")
        print("-" * 76)
        for arc in sorted(unexpected):
            print(_format_arc(arc))
    if stale:
        print("\nStale structural-debt entries")
        print("-" * 76)
        for arc in sorted(stale):
            print(_format_arc(arc))

    errors: list[str] = []
    if branch_total != expected_total:
        errors.append(
            f"branch denominator changed from frozen {expected_total} to {branch_total}"
        )
    if raw_missing != len(actual_arcs):
        errors.append(
            f"coverage totals report {raw_missing} missing branches but per-file arcs contain {len(actual_arcs)}"
        )
    if unexpected:
        errors.append(f"{len(unexpected)} unexpected missing branch(es)")
    if stale:
        errors.append(f"{len(stale)} stale structural-debt contract entr{'y' if len(stale) == 1 else 'ies'}")

    if errors:
        raise SystemExit("Structural branch debt audit failed: " + "; ".join(errors) + ".")


if __name__ == "__main__":
    main()
