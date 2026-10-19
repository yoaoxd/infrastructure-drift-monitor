#!/usr/bin/env python3
"""Summarize Terraform's recorded drift without exposing resource values."""

import argparse
import json
import sys
from pathlib import Path


def summarize(plan, planned=False):
    """Return address/action metadata. Never include before/after values."""
    if not isinstance(plan, dict):
        raise ValueError("Expected a Terraform JSON plan object")
    version = str(plan.get("format_version", ""))
    if version.split(".")[0] != "1":
        raise ValueError("Supported Terraform JSON format major version: 1")
    if "terraform_version" not in plan or not any(
        key in plan for key in ("planned_values", "resource_changes", "resource_drift")
    ):
        raise ValueError("Expected terraform show -json output from a saved plan")
    key = "resource_changes" if planned else "resource_drift"
    changes = plan.get(key, [])
    if not isinstance(changes, list):
        raise ValueError(f"{key} must be an array")
    rows = []
    for item in changes:
        if not isinstance(item, dict) or not isinstance(item.get("change"), dict):
            raise ValueError("Malformed resource change")
        actions = item["change"].get("actions")
        if not isinstance(actions, list) or not actions or not all(isinstance(x, str) for x in actions):
            raise ValueError("Resource change is missing action names")
        if actions == ["no-op"] or item.get("mode") == "data":
            continue
        address = item.get("address")
        if not isinstance(address, str) or not address:
            raise ValueError("Resource change is missing an address")
        rows.append({"address": address, "actions": actions})
    return {
        "kind": "planned_changes" if planned else "recorded_drift",
        "terraform_version": plan["terraform_version"],
        "count": len(rows),
        "resources": sorted(rows, key=lambda row: row["address"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="JSON exported by terraform show -json")
    parser.add_argument("--planned", action="store_true", help="Report proposed configuration changes instead of recorded drift")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    try:
        report = summarize(json.loads(args.plan.read_text()), args.planned)
        if args.format == "json":
            print(json.dumps(report, indent=2))
        else:
            print(f"{report['kind']}: {report['count']} resource(s)")
            for row in report["resources"]:
                # JSON escaping keeps control characters out of terminals and logs.
                print(f"{json.dumps(row['address'])}: {', '.join(row['actions'])}")
        return 2 if report["count"] else 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
