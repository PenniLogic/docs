"""Validate the per-epic STRIDE threat-model refresh records (T-QA-14, PenniLogic/docs#48).

governance/threat-model/categories.json publishes the model: the category list (the six STRIDE
categories plus the seven previously missing ones), each category's owner, the refresh cadence in
weeks and the named early-refresh triggers. governance/threat-model/records/<epic>.json carries one
record per epic with its dated refreshes; an epic with no refresh has an empty list, never a missing
file. This module validates both against governance/threat-model/schema.json with a strict draft-07
subset (a keyword it does not implement is an error, so nothing passes silently), enforces the rules
the acceptance criteria state, and reports every epic as current, stale, blocked, not_refreshed or
invalid against an injectable clock, so the T-GOV-04 pull-request check can gate an epic without a
human reading prose.

    python scripts/check_threat_model.py                     validate everything and print the summary
    python scripts/check_threat_model.py --epic E01          exit 1 unless E01 has a current refresh
    python scripts/check_threat_model.py --today 2027-01-15  evaluate against another date
    python scripts/check_threat_model.py --json              machine-readable summary on stdout
"""

import argparse
import datetime
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
MODEL = "governance/threat-model/categories.json"
SCHEMA = "governance/threat-model/schema.json"
RECORDS = "governance/threat-model/records"
TEMPLATE = "governance/threat-model/STRIDE-refresh-template.md"
README = "governance/threat-model/README.md"
BACKLOG = "planning/backlog.json"
EPICS = "planning/source/epics.json"

STRIDE_CATEGORIES = (
    "spoofing", "tampering", "repudiation", "information_disclosure",
    "denial_of_service", "elevation_of_privilege",
)
ADDED_CATEGORIES = (
    "billing_forgery", "entitlement_tampering", "ai_service_compromise", "request_forgery",
    "prompt_injection", "split_manipulation", "administrative_identity_compromise",
)
REQUIRED_TRIGGERS = ("definition_of_ready", "cadence", "model_changed")
# A refresh may be dated this far ahead of the checking clock, so a record written late in the
# evening in India is not rejected by a continuous-integration runner still on the previous UTC day.
FUTURE_TOLERANCE = datetime.timedelta(days=1)

EPIC_ID = re.compile(r"^E[0-9]{2}$")
EPIC_TITLE = re.compile(r"^\[EPIC\] (E[0-9]{2}) - (.+)$")
URL = re.compile(r"[a-z][a-z0-9+.-]*://", re.IGNORECASE)

ANNOTATIONS = {"$schema", "$id", "title", "description", "examples", "default", "definitions"}
SUPPORTED = {
    "type", "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
    "uniqueItems", "enum", "const", "pattern", "minLength", "minimum", "maximum", "$ref",
}


class SchemaError(ValueError):
    """The schema uses something this validator does not implement."""


def load_json(path):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"Duplicate JSON key {key!r} in {path.name}")
            value[key] = item
        return value
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def _type_matches(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    simple = {"string": str, "object": dict, "array": list, "boolean": bool, "null": type(None)}
    if name not in simple:
        raise SchemaError(f"Unsupported schema type: {name}")
    return isinstance(value, simple[name])


def _resolve(ref, root):
    prefix = "#/definitions/"
    if not ref.startswith(prefix):
        raise SchemaError(f"Unsupported $ref: {ref}")
    try:
        return root["definitions"][ref[len(prefix):]]
    except KeyError:
        raise SchemaError(f"Unknown definition in $ref: {ref}") from None


def validate_schema(value, schema, root=None, path="$"):
    """Validate value against a draft-07 schema subset; raise ValueError on the first problem."""
    root = schema if root is None else root
    if not isinstance(schema, dict):
        raise SchemaError(f"{path}: schema must be an object")
    unknown = set(schema) - SUPPORTED - ANNOTATIONS
    if unknown:
        raise SchemaError(f"{path}: unsupported schema keyword(s): {', '.join(sorted(unknown))}")
    if "$ref" in schema:
        validate_schema(value, _resolve(schema["$ref"], root), root, path)
    if "const" in schema and value != schema["const"]:
        raise ValueError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path}: {value!r} is not one of {schema['enum']}")
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_matches(value, name) for name in names):
            raise ValueError(f"{path}: expected type {'/'.join(names)}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ValueError(f"{path}: shorter than {schema['minLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise ValueError(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: {value} is below the minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{path}: {value} is above the maximum {schema['maximum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], root, f"{path}.{key}")
            elif additional is False:
                raise ValueError(f"{path}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                validate_schema(item, additional, root, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ValueError(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(item, sort_keys=True) for item in value]
            if len(seen) != len(set(seen)):
                raise ValueError(f"{path}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema["items"], root, f"{path}[{index}]")


def definition(schema, name):
    return {"$ref": f"#/definitions/{name}", "definitions": schema["definitions"]}


def parse_date(value, label):
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{label}: {value!r} is not a calendar date") from None


def check_model(model):
    """Enforce the model rules that the schema cannot express; raise ValueError on the first problem."""
    ids = [category["id"] for category in model["categories"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate category id in the model")
    for required in STRIDE_CATEGORIES + ADDED_CATEGORIES:
        if required not in ids:
            raise ValueError(f"Model is missing the required category {required!r}")
    owners = set(model["accountable_owners"])
    roles = set(model["review_roles"])
    for category in model["categories"]:
        label = f"category {category['id']!r}"
        if category["family"] == "stride" and category["stride_letter"] is None:
            raise ValueError(f"{label}: a STRIDE category needs its letter")
        if category["family"] == "extension" and category["stride_letter"] is not None:
            raise ValueError(f"{label}: an extension category has no STRIDE letter")
        if category["added_in_model_version"] > model["model_version"]:
            raise ValueError(f"{label}: added_in_model_version is ahead of model_version")
        owner = category["owner"]
        if owner["accountable"] not in owners:
            raise ValueError(f"{label}: owner {owner['accountable']!r} is not an accountable owner")
        if owner["review_role"] not in roles:
            raise ValueError(f"{label}: review role {owner['review_role']!r} is not a published role")
        for role in owner["supporting_review_roles"]:
            if role not in roles or role == owner["review_role"]:
                raise ValueError(f"{label}: supporting role {role!r} is invalid")
    triggers = [trigger["id"] for trigger in model["refresh_triggers"]]
    if len(triggers) != len(set(triggers)):
        raise ValueError("Duplicate refresh trigger id in the model")
    for required in REQUIRED_TRIGGERS:
        if required not in triggers:
            raise ValueError(f"Model is missing the required trigger {required!r}")


def required_categories(model, model_version):
    """Category ids a refresh performed against model_version must have reviewed."""
    if not 1 <= model_version <= model["model_version"]:
        raise ValueError(f"model_version {model_version} is not between 1 and {model['model_version']}")
    return {
        category["id"] for category in model["categories"]
        if category["added_in_model_version"] <= model_version
    }


def check_refresh(refresh, epic, model, today, epic_issues):
    """Return the list of rule violations in one refresh (an empty list means it is valid)."""
    problems = []
    date = parse_date(refresh["date"], f"{epic} refresh date")
    if date > today + FUTURE_TOLERANCE:
        problems.append(f"refresh {refresh['date']} is dated after the checking clock {today}")
    if refresh["trigger"] not in {trigger["id"] for trigger in model["refresh_triggers"]}:
        problems.append(f"unknown refresh trigger {refresh['trigger']!r}")
    if refresh["performed_by"]["accountable"] not in model["accountable_owners"]:
        problems.append(f"performer {refresh['performed_by']['accountable']!r} is not an accountable owner")
    try:
        required = required_categories(model, refresh["model_version"])
    except ValueError as error:
        return problems + [str(error)]
    reviewed = [review["id"] for review in refresh["categories"]]
    if len(reviewed) != len(set(reviewed)):
        problems.append("a category is reviewed twice")
    missing = sorted(required - set(reviewed))
    unknown = sorted(set(reviewed) - required)
    if missing:
        problems.append(
            f"reviews {len(set(reviewed)) - len(unknown)} of {len(required)} required categories; "
            f"missing: {', '.join(missing)}"
        )
    if unknown:
        problems.append(f"reviews categories outside model version {refresh['model_version']}: {', '.join(unknown)}")

    findings = {}
    for finding in refresh["findings"]:
        if finding["id"] in findings:
            problems.append(f"duplicate finding id {finding['id']}")
        findings[finding["id"]] = finding
        label = f"finding {finding['id']}"
        if not finding["id"].startswith(f"{epic}-"):
            problems.append(f"{label} does not belong to {epic}")
        if finding["category"] not in required:
            problems.append(f"{label} names an unreviewed category {finding['category']!r}")
        if finding["status"] == "handed_off":
            if finding["owner_ticket"] is None:
                problems.append(f"{label} is handed off but names no owner ticket")
            elif finding["owner_ticket"] in epic_issues:
                problems.append(f"{label} is handed to an epic rather than to a ticket")
            if finding["resolution"] is not None:
                problems.append(f"{label} is handed off but also carries a resolution")
        elif finding["status"] == "closed":
            if finding["resolution"] is None:
                problems.append(f"{label} is closed without a resolution")
            if finding["owner_ticket"] is not None:
                problems.append(f"{label} is closed but also names an owner ticket")
        else:
            if finding["owner_ticket"] is not None or finding["resolution"] is not None:
                problems.append(f"{label} is open but carries an owner ticket or resolution")

    for review in refresh["categories"]:
        label = f"category {review['id']!r}"
        if not review["analysis"].strip():
            problems.append(f"{label} has no analysis")
        if review["disposition"] in {"controlled", "accepted"} and not review["evidence"]:
            problems.append(f"{label} is {review['disposition']} without evidence")
        if review["disposition"] == "finding" and not review["findings"]:
            problems.append(f"{label} is a finding disposition without findings")
        if review["disposition"] != "finding" and review["findings"]:
            problems.append(f"{label} lists findings but its disposition is {review['disposition']!r}")
        for finding_id in review["findings"]:
            if finding_id not in findings:
                problems.append(f"{label} references unknown finding {finding_id}")
    for finding in findings.values():
        primary = next((r for r in refresh["categories"] if r["id"] == finding["category"]), None)
        if primary is None or finding["id"] not in primary["findings"]:
            problems.append(f"finding {finding['id']} is not listed by its category {finding['category']!r}")
    return problems


def check_record(record, epic, model, today, epic_issues):
    problems = []
    if record["epic"] != epic:
        problems.append(f"record names epic {record['epic']} but the file is {epic}.json")
    if record["owner"]["accountable"] not in model["accountable_owners"]:
        problems.append(f"record owner {record['owner']['accountable']!r} is not an accountable owner")
    if record["issue"] is None and not record.get("note", "").strip():
        problems.append("record has no public epic issue and no note explaining why")
    # A record names attack paths and controls by repository path and issue identifier. A URL is
    # either a live endpoint or an external reference the checker cannot vouch for; neither belongs.
    if URL.search(json.dumps(record)):
        problems.append("record contains a URL; reference repository paths and public issue identifiers instead")
    previous = None
    for index, refresh in enumerate(record["refreshes"]):
        date = parse_date(refresh["date"], f"{epic} refresh {index}")
        if previous is not None and date < previous:
            problems.append("refreshes are not in ascending date order")
        previous = date
        problems.extend(check_refresh(refresh, epic, model, today, epic_issues))
    return problems


def evaluate_epic(record, epic, model, today, problems):
    """Classify one epic for the Definition of Ready gate."""
    owner = record["owner"]["accountable"] if isinstance(record.get("owner"), dict) else None
    result = {
        "epic": epic, "title": record.get("title"), "issue": record.get("issue"),
        # A record too broken to name its owner still has one: the model's accountable owner.
        "owner": owner or model["accountable_owners"][0],
        "status": None, "reasons": [], "latest_refresh": None, "next_refresh_due": None,
        "findings": 0, "unowned_findings": [],
    }
    if problems:
        result["status"] = "invalid"
        result["reasons"] = list(problems)
        return result
    if not record["refreshes"]:
        result["status"] = "not_refreshed"
        result["reasons"] = ["no refresh recorded; record the Definition of Ready refresh before the first ticket starts"]
        return result
    latest = record["refreshes"][-1]
    date = datetime.date.fromisoformat(latest["date"])
    due = date + datetime.timedelta(weeks=model["cadence_weeks"])
    result["latest_refresh"] = latest["date"]
    result["next_refresh_due"] = due.isoformat()
    result["findings"] = len(latest["findings"])
    result["unowned_findings"] = [f["id"] for f in latest["findings"] if f["status"] == "open"]
    reasons = []
    if today > due:
        reasons.append(f"latest refresh {latest['date']} is older than the {model['cadence_weeks']}-week cadence (due {due})")
    if latest["model_version"] < model["model_version"]:
        reasons.append(
            f"latest refresh used model version {latest['model_version']} but the model is at "
            f"version {model['model_version']}; the new categories have not been reviewed"
        )
    if reasons:
        result["status"] = "stale"
        result["reasons"] = reasons
    elif result["unowned_findings"]:
        result["status"] = "blocked"
        result["reasons"] = [
            f"{len(result['unowned_findings'])} unowned finding(s) block Definition of Ready: "
            + ", ".join(result["unowned_findings"])
        ]
    else:
        result["status"] = "current"
    if result["status"] != "blocked" and result["unowned_findings"]:
        result["reasons"].append("unowned finding(s): " + ", ".join(result["unowned_findings"]))
    return result


def inventory(root):
    """Epic ids the records must cover: every epic on the preserved board plus the source epic files."""
    epics = {}
    backlog = load_json(root / BACKLOG)
    for item in backlog["items"]:
        match = EPIC_TITLE.match(item.get("title", ""))
        if match:
            epics[match.group(1)] = match.group(2)
    for item in load_json(root / EPICS)["items"]:
        match = EPIC_TITLE.match(item.get("title", ""))
        if match:
            epics.setdefault(match.group(1), match.group(2))
    if not epics:
        raise ValueError("No epics found in the planning inventory")
    return epics


def check_documents(model, root):
    """The template and README must name everything the data publishes."""
    template = (root / TEMPLATE).read_text(encoding="utf-8")
    readme = (root / README).read_text(encoding="utf-8")
    for category in model["categories"]:
        if f"`{category['id']}`" not in template:
            raise ValueError(f"Template does not cover category {category['id']!r}")
    cadence = f"{model['cadence_weeks']} weeks"
    if cadence not in readme or cadence not in template:
        raise ValueError(f"Published cadence {cadence!r} is not stated in both the README and the template")
    for trigger in model["refresh_triggers"]:
        if f"`{trigger['id']}`" not in readme:
            raise ValueError(f"README does not publish the refresh trigger {trigger['id']!r}")


def run(root=ROOT, today=None):
    """Validate the model, every record and the documents; return the evaluation summary."""
    today = datetime.date.today() if today is None else today
    schema = load_json(root / SCHEMA)
    model = load_json(root / MODEL)
    validate_schema(model, definition(schema, "model"))
    check_model(model)
    check_documents(model, root)
    epics = inventory(root)
    files = {path.stem: path for path in sorted((root / RECORDS).glob("*.json"))}
    for stem in files:
        if not EPIC_ID.match(stem):
            raise ValueError(f"Record file {stem}.json is not named after an epic")
        if stem not in epics:
            raise ValueError(f"Record {stem}.json has no epic in the planning inventory")
    missing = sorted(set(epics) - set(files))
    if missing:
        raise ValueError(f"Epics without a threat-model record: {', '.join(missing)}")

    records = {}
    problems = {}
    for epic, path in files.items():
        try:
            record = load_json(path)
            validate_schema(record, definition(schema, "record"))
        except ValueError as error:
            records[epic] = {"title": epics[epic], "issue": None}
            problems[epic] = [str(error)]
            continue
        records[epic] = record
        problems[epic] = []
    epic_issues = {record["issue"] for record in records.values() if record.get("issue")}
    for epic, record in records.items():
        if not problems[epic]:
            try:
                problems[epic] = check_record(record, epic, model, today, epic_issues)
            except ValueError as error:
                problems[epic] = [str(error)]

    evaluations = [evaluate_epic(records[epic], epic, model, today, problems[epic]) for epic in sorted(records)]
    counts = {status: 0 for status in ("current", "stale", "blocked", "not_refreshed", "invalid")}
    for evaluation in evaluations:
        counts[evaluation["status"]] += 1
    unowned = [
        {"epic": e["epic"], "finding": finding, "owner": e["owner"]}
        for e in evaluations for finding in e["unowned_findings"]
    ]
    return {
        "today": today.isoformat(),
        "model_version": model["model_version"],
        "cadence_weeks": model["cadence_weeks"],
        "categories": len(model["categories"]),
        "epics": evaluations,
        "counts": counts,
        "unowned_findings": unowned,
    }


def format_summary(summary):
    counts = summary["counts"]
    lines = [
        f"Threat model v{summary['model_version']} with {summary['categories']} categories, "
        f"{summary['cadence_weeks']}-week cadence, evaluated on {summary['today']}: "
        f"{counts['current']} current, {counts['stale']} stale, {counts['blocked']} blocked, "
        f"{counts['not_refreshed']} not refreshed, {counts['invalid']} invalid "
        f"of {len(summary['epics'])} epics."
    ]
    for evaluation in summary["epics"]:
        if evaluation["status"] == "not_refreshed":
            continue
        detail = "; ".join(evaluation["reasons"]) if evaluation["reasons"] else f"due {evaluation['next_refresh_due']}"
        lines.append(f"  {evaluation['epic']} {evaluation['status']}: {detail}")
    for item in summary["unowned_findings"]:
        lines.append(f"  unowned finding {item['finding']} ({item['epic']}) needs a ticket; owner {item['owner']}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--epic", help="exit 1 unless this epic has a current refresh (the Definition of Ready gate)")
    parser.add_argument("--today", help="evaluate staleness against this ISO date instead of the system clock")
    parser.add_argument("--json", action="store_true", help="print the machine-readable summary")
    args = parser.parse_args(argv)
    try:
        today = parse_date(args.today, "--today") if args.today else None
        summary = run(ROOT, today)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Threat-model check failed: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(summary, indent=2))
    elif not args.epic:
        print(format_summary(summary))
    if args.epic:
        evaluation = next((e for e in summary["epics"] if e["epic"] == args.epic), None)
        if evaluation is None:
            print(f"Threat-model check failed: unknown epic {args.epic}", file=sys.stderr)
            return 1
        if evaluation["status"] != "current":
            print(
                f"Definition of Ready not met for {args.epic}: {evaluation['status']} "
                f"({'; '.join(evaluation['reasons'])}). Owner who must record the refresh: {evaluation['owner']}.",
                file=sys.stderr,
            )
            return 1
        if not args.json:
            print(
                f"{args.epic} current: refreshed {evaluation['latest_refresh']}, "
                f"next refresh due {evaluation['next_refresh_due']}, {evaluation['findings']} finding(s) all owned or closed."
            )
        return 0
    return 1 if summary["counts"]["invalid"] else 0


if __name__ == "__main__":
    sys.exit(main())
