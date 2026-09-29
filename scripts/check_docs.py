"""Validate carried-forward decision and backlog inventories without claiming delivery."""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def validate_backlog(value):
    if value.get("schema_version") != 1 or not isinstance(value.get("items"), list):
        raise ValueError("Invalid backlog shape")
    seen = set()
    for item in value["items"]:
        key = item.get("legacy_id")
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError("Missing or duplicate legacy backlog identity")
        seen.add(key)
        if not item.get("title") or not item.get("source_url", "").startswith(
            "https://github.com/PenniLogic-old/"
        ):
            raise ValueError("Backlog item lacks original source provenance")
        if item.get("legacy_status") not in {
            "Backlog", "Ready", "In Progress", "In Review", "In Test", "Blocked", "Done"
        }:
            raise ValueError("Unknown historical status")
    if value.get("item_count") != len(seen):
        raise ValueError("Backlog count does not match its inventory")


def main():
    try:
        reservations = json.loads((ROOT / "adr/reservations.json").read_text(encoding="utf-8"))
        ids = [entry["number"] for entry in reservations["items"]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate ADR reservation")
        for number in ids:
            if not re.fullmatch(r"ADR-\d{3}", number):
                raise ValueError("Invalid ADR reservation identifier")
        adopted = sorted(path.stem for path in (ROOT / "adr").glob("ADR-*.md"))
        if not adopted or set(adopted).intersection(ids):
            raise ValueError("Published ADRs overlap pending reservations")
        validate_backlog(json.loads((ROOT / "planning/backlog.json").read_text(encoding="utf-8")))
        for path in (ROOT / "planning/source").rglob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Documentation check failed: {error}", file=sys.stderr)
        return 1
    print(f"Docs inventory valid: {len(adopted)} carried-forward ADRs, {len(ids)} pending reservations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
