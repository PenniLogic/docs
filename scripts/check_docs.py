"""Validate carried-forward decision and backlog inventories without claiming delivery."""

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def load_check(name):
    """Load a sibling check module by path so this script works from any working directory."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        layout = load_check("validate_adr_layout").check_layout(ROOT)
        validate_backlog(json.loads((ROOT / "planning/backlog.json").read_text(encoding="utf-8")))
        for path in (ROOT / "planning/source").rglob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
        taxonomy = load_check("check_client_states").validate_taxonomy(ROOT)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Documentation check failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Docs inventory valid: {layout['legacy']} carried-forward ADRs, {layout['published']} published "
        f"reserved records, {layout['pending']} pending reservations, "
        f"client state taxonomy {taxonomy['taxonomy_version']} with {taxonomy['states']} states."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
