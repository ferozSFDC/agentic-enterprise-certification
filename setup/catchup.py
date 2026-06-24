#!/usr/bin/env python3
"""
Agentic Enterprise Course — Checkpoint Catch-Up CLI

Usage:
    python setup/catchup.py --student student.json --checkpoint 3
    python setup/catchup.py --student student.json --only 4
    python setup/catchup.py --student student.json --checkpoint 6 --dry-run

Runs all checkpoints from 1 up to --checkpoint N (or just --only N),
idempotently standing up every artifact a student needs to start that exercise.
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Allow running from repo root or from setup/ dir
sys.path.insert(0, str(Path(__file__).parent))

from checkpoints import CHECKPOINTS
from checkpoints.base import _deep_merge


REQUIRED_VARIABLE_FIELDS = [
    ("anypoint", "orgId"),
    ("anypoint", "environmentId"),
    ("anypoint", "username"),
    ("anypoint", "password"),
    ("anypoint", "exchange", "clientId"),
    ("anypoint", "exchange", "clientSecret"),
    ("cloudHub", "deploymentTargetName"),
    ("student", "email"),
]


def load_creds(path: str) -> dict:
    with open(path) as f:
        creds = json.load(f)
    return creds


def validate_creds(creds: dict) -> list[str]:
    errors = []
    variable = creds.get("variable", {})
    for path in REQUIRED_VARIABLE_FIELDS:
        node = variable
        for key in path:
            if not isinstance(node, dict) or key not in node:
                errors.append(f"variable.{'.'.join(path)} is missing")
                break
            node = node[key]
        else:
            if not node or str(node).startswith("REPLACE"):
                errors.append(f"variable.{'.'.join(path)} is empty or not filled in")
    return errors


def save_creds(path: str, creds: dict, updates: dict) -> dict:
    if not updates:
        return creds
    merged = _deep_merge(creds, updates)
    with open(path, "w") as f:
        json.dump(merged, f, indent=2)
    return merged


def print_summary(results: list) -> None:
    print()
    print("=" * 60)
    print("  CHECKPOINT SUMMARY")
    print("=" * 60)
    icons = {"skipped": "✓", "completed": "✓", "failed": "✗"}
    colors = {"skipped": "\033[90m", "completed": "\033[32m", "failed": "\033[31m"}
    reset = "\033[0m"

    all_ok = True
    for r in results:
        icon = icons.get(r.status, "?")
        color = colors.get(r.status, "")
        label = "already done" if r.status == "skipped" else r.status
        msg = f" — {r.message}" if r.message and r.status not in ("skipped", "completed") else ""
        print(f"  {color}{icon} CP{r.number}: {r.name} [{label}]{msg}{reset}")
        if r.status == "failed":
            all_ok = False

    print()
    if all_ok:
        print("  All checkpoints satisfied. You are ready to continue.")
    else:
        print("  One or more checkpoints failed. See messages above.")
        print("  Re-run with --verbose for full API responses.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Stand up all course artifacts up to a given checkpoint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bring student up to Exercise 3 (runs CP1, CP2, CP3):
  python setup/catchup.py --student student.json --checkpoint 3

  # Re-run only CP4 (e.g. after a machine restart):
  python setup/catchup.py --student student.json --only 4

  # Preview what CP6 would do without making changes:
  python setup/catchup.py --student student.json --checkpoint 6 --dry-run
        """,
    )
    parser.add_argument("--student", required=True, help="Path to student.json credentials file")
    parser.add_argument("--checkpoint", type=int, default=6, help="Run CPs 1 through N (default: 6)")
    parser.add_argument("--only", type=int, help="Run only CP N, skip all others")
    parser.add_argument("--dry-run", action="store_true", help="Print what would run; make no changes")
    parser.add_argument("--verbose", action="store_true", help="Show full API responses")
    args = parser.parse_args()

    if not os.path.exists(args.student):
        print(f"Error: student file not found: {args.student}")
        print(f"Hint: copy student.template.json to student.json and fill in the variable section.")
        sys.exit(1)

    creds = load_creds(args.student)

    errors = validate_creds(creds)
    if errors:
        print("Error: student.json is missing required values:")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)

    # Determine which checkpoints to run
    if args.only:
        target_cps = [cp for cp in CHECKPOINTS if cp.number == args.only]
        if not target_cps:
            print(f"Error: no checkpoint with number {args.only}")
            sys.exit(1)
    else:
        target_cps = [cp for cp in CHECKPOINTS if cp.number <= args.checkpoint]

    print()
    if args.dry_run:
        print(f"  DRY RUN — checkpoints 1–{args.checkpoint}")
    elif args.only:
        print(f"  Running CP{args.only} only")
    else:
        print(f"  Running checkpoints 1–{args.checkpoint}")
    print(f"  Student: {creds['variable']['student'].get('email', '(email not set)')}")
    print()

    results = []
    accumulated_updates = {}

    for cp in target_cps:
        print(f"  CP{cp.number}: {cp.name}")
        result = cp.run_idempotent(creds, dry_run=args.dry_run, verbose=args.verbose)
        results.append(result)

        if result.updates:
            accumulated_updates.update(result.updates)
            creds = save_creds(args.student, creds, result.updates)
            print(f"    → Updated student.json with {len(result.updates)} new value(s)")

        status_line = {
            "skipped": "  ✓ already done",
            "completed": "  ✓ complete",
            "failed": f"  ✗ FAILED: {result.message}",
        }.get(result.status, f"  ? {result.status}")
        print(status_line)

        if result.status == "failed":
            print(f"\n  Stopping at CP{cp.number}. Fix the issue above and re-run.")
            print_summary(results)
            sys.exit(1)

    print_summary(results)


if __name__ == "__main__":
    main()
