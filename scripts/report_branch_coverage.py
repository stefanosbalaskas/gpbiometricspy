from __future__ import annotations

import argparse
import json
from pathlib import Path


def _missing_branch_count(summary: dict[str, object]) -> int:
    return int(summary.get("num_branches", 0)) - int(summary.get("covered_branches", 0))


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize coverage.py branch debt by source file.")
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    payload = json.loads(args.coverage_json.read_text(encoding="utf-8"))
    totals = payload["totals"]
    files = payload["files"]

    branch_total = int(totals.get("num_branches", 0))
    covered = int(totals.get("covered_branches", 0))
    missing = branch_total - covered
    pct = 100.0 if branch_total == 0 else (100.0 * covered / branch_total)

    rows: list[tuple[int, str, int, int, float]] = []
    for path, entry in files.items():
        summary = entry["summary"]
        debt = _missing_branch_count(summary)
        if debt <= 0:
            continue
        total = int(summary.get("num_branches", 0))
        hit = int(summary.get("covered_branches", 0))
        file_pct = 100.0 if total == 0 else (100.0 * hit / total)
        rows.append((debt, path, hit, total, file_pct))

    rows.sort(key=lambda row: (-row[0], row[1]))

    print("BRANCH COVERAGE AUDIT")
    print("=" * 76)
    print(f"covered branches : {covered:,}/{branch_total:,}")
    print(f"missing branches : {missing:,}")
    print(f"branch coverage  : {pct:.4f}%")
    print()
    print(f"Top {min(args.top, len(rows))} files by missing branch paths")
    print("-" * 76)
    for debt, path, hit, total, file_pct in rows[: args.top]:
        print(f"{debt:5d} missing | {hit:5d}/{total:<5d} | {file_pct:8.3f}% | {path}")


if __name__ == "__main__":
    main()
