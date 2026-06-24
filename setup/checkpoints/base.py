from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CheckpointResult:
    number: int
    name: str
    status: str  # "skipped" | "completed" | "failed"
    message: str = ""
    updates: dict = field(default_factory=dict)


class BaseCheckpoint(ABC):
    number: int
    name: str

    @abstractmethod
    def check(self, creds: dict) -> bool:
        """Return True if this checkpoint is already satisfied."""

    @abstractmethod
    def run(self, creds: dict) -> dict:
        """Execute setup for this checkpoint. Return dict of new credential values to merge."""

    def verify(self, creds: dict) -> list[str]:
        """Return human-readable list of what this checkpoint will verify."""
        return [f"CP{self.number} — {self.name}"]

    def run_idempotent(self, creds: dict, dry_run: bool = False, verbose: bool = False) -> CheckpointResult:
        """
        Idempotent wrapper:
        - If dry_run: print what would run, don't execute (skip live check())
        - If check() passes: skip
        - Otherwise: run() then verify with check() again
        """
        if dry_run:
            checks = self.verify(creds)
            print(f"\n  CP{self.number} would run:")
            for c in checks:
                print(f"    • {c}")
            return CheckpointResult(self.number, self.name, "skipped", "(dry-run)")

        try:
            already_done = self.check(creds)
        except Exception as exc:
            return CheckpointResult(self.number, self.name, "failed", f"check() raised: {exc}")

        if already_done:
            return CheckpointResult(self.number, self.name, "skipped", "already complete")

        try:
            updates = self.run(creds)
        except Exception as exc:
            return CheckpointResult(self.number, self.name, "failed", f"run() raised: {exc}")

        if verbose and updates:
            print(f"  CP{self.number} produced: {json.dumps(updates, indent=2)}")

        try:
            passed = self.check(creds)
        except Exception as exc:
            return CheckpointResult(self.number, self.name, "failed", f"post-run check raised: {exc}")

        if passed:
            return CheckpointResult(self.number, self.name, "completed", "done", updates)
        else:
            return CheckpointResult(self.number, self.name, "failed", "check() still failing after run()")


def _deep_merge(base: dict, updates: dict) -> dict:
    """Recursively merge updates into base (dot-path keys like 'a.b.c' are expanded)."""
    result = dict(base)
    for key, val in updates.items():
        if "." in key:
            parts = key.split(".", 1)
            sub = result.get(parts[0], {})
            result[parts[0]] = _deep_merge(sub if isinstance(sub, dict) else {}, {parts[1]: val})
        elif isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def get_anypoint_token(creds: dict) -> str:
    import requests
    resp = requests.post(
        "https://anypoint.mulesoft.com/accounts/api/v2/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": creds["variable"]["anypoint"]["exchange"]["clientId"],
            "client_secret": creds["variable"]["anypoint"]["exchange"]["clientSecret"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_sf_token(creds: dict, org: str = "serviceCloud") -> tuple[str, str]:
    """Returns (access_token, instance_url)."""
    import requests
    sf = creds["stable"]["salesforce"][org]
    resp = requests.post(
        sf["tokenEndpoint"],
        data={
            "grant_type": "client_credentials",
            "client_id": sf["clientId"],
            "client_secret": sf["clientSecret"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    return body["access_token"], body["instance_url"]
