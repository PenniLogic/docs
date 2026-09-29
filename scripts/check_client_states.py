"""Validate the shared client state taxonomy: schema, semantic rules and document consistency.

The taxonomy (T-UX-01) is published as data in product/client-state-taxonomy.json with a JSON
Schema in product/client-state-taxonomy.schema.json and prose in product/client-state-taxonomy.md.
This module validates the data against the schema with a strict draft-07 subset (any keyword it
does not implement is an error, so nothing passes silently), enforces the rules the acceptance
criteria state, and checks that the document names everything the data publishes.
"""

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA = "product/client-state-taxonomy.json"
SCHEMA = "product/client-state-taxonomy.schema.json"
DOCUMENT = "product/client-state-taxonomy.md"

REQUIRED_STATES = (
    "empty", "loading", "error", "offline", "stale",
    "permission_denied", "quota_exceeded", "degraded",
)
REQUIRED_DISTINCTIONS = (("offline", "stale"), ("error", "degraded"))
REQUIRED_COPY_RULES = (
    "no_blame", "no_invented_cause", "no_internal_detail",
    "no_hidden_data_disclosure", "same_wording", "one_action",
)
REQUIRED_CONTRACT_CONDITIONS = {
    "entitlement_denied": "permission_denied",
    "grant_not_active": "permission_denied",
}
REQUIRED_CAUSES = ("device", "plan", "sharing")
REQUIRED_EXAMPLES = {
    "capture_surface_permission_denied": "permission_denied",
    "ai_surface_quota_exceeded": "quota_exceeded",
    "shared_balance_stale": "stale",
}
REQUIRED_ASSERTIONS = ("client_state_coverage", "taxonomy_first")
# The only region states whose presence in a supplementary region makes the host surface degraded.
DEGRADED_PRODUCERS = ("error", "offline")

PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
# An HTTP-style status or a SCREAMING_SNAKE token would be an invented code; T-CON-12 owns codes.
CODE_LIKE = re.compile(r"(?<![A-Za-z0-9])[45][0-9]{2}(?![A-Za-z0-9])|\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
SEVERAL_ACTIONS = re.compile(r"\bor\b|/")

ANNOTATIONS = {"$schema", "$id", "title", "description", "examples", "default", "definitions"}
SUPPORTED = {
    "type", "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
    "uniqueItems", "enum", "const", "pattern", "minLength", "$ref",
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
        if len(value) > schema.get("maxItems", len(value)):
            raise ValueError(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ValueError(f"{path}: items are not unique")
        if "items" in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema["items"], root, f"{path}[{index}]")


def canonical_strings(state):
    """Every canonical string a client renders for a state: copy, variants and action labels."""
    copy = state["copy"]
    yield copy["headline"]
    yield copy["body"]
    for variant in copy.get("variants", {}).values():
        yield variant["headline"]
        yield variant["body"]
    action = state["recovery_action"]
    yield action["label"]
    yield from action.get("label_by_cause", {}).values()


def forbidden_term(text, terms):
    lowered = text.lower()
    for term in terms:
        if any(character.isalpha() for character in term):
            if re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", lowered):
                return term
        elif term in lowered:
            return term
    return None


def _unique_ids(items, label):
    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {label} identifier")
    return {item["id"]: item for item in items}


def _check_states(data, states):
    placeholders = set(_unique_ids(data["placeholders"], "placeholder"))
    for missing in set(REQUIRED_STATES) - set(states):
        raise ValueError(f"Missing required state identifier: {missing}")
    for state_id, state in states.items():
        if state["name"] != state_id.replace("_", "-"):
            raise ValueError(f"State {state_id}: name must be the hyphenated identifier")
        if state["signal"] != data["signals"]["prefix"] + state_id:
            raise ValueError(f"State {state_id}: signal must be {data['signals']['prefix']}{state_id}")
        action = state["recovery_action"]
        for label in [action["label"], *action.get("label_by_cause", {}).values()]:
            if SEVERAL_ACTIONS.search(label):
                raise ValueError(f"State {state_id}: recovery action label must offer exactly one action")
        for text in canonical_strings(state):
            for name in PLACEHOLDER.findall(text):
                if name not in placeholders:
                    raise ValueError(f"State {state_id}: undeclared placeholder {{{name}}}")
            term = forbidden_term(text, data["forbidden_terms"])
            if term:
                raise ValueError(f"State {state_id}: forbidden term {term!r} in canonical copy")
        causes = {cause["id"] for cause in state.get("causes", [])}
        for key in action.get("label_by_cause", {}):
            if key not in causes:
                raise ValueError(f"State {state_id}: label_by_cause names unknown cause {key!r}")
    if set(data["precedence"]) != set(states) or len(data["precedence"]) != len(states):
        raise ValueError("Precedence must list every state exactly once")
    denied = states["permission_denied"]
    causes = {cause["id"] for cause in denied.get("causes", [])}
    for cause in REQUIRED_CAUSES:
        if cause not in causes:
            raise ValueError(f"permission_denied must define cause {cause!r}")
    for key, variant in denied["copy"].get("variants", {}).items():
        if key not in causes:
            raise ValueError(f"permission_denied copy variant {key!r} is not a cause")
        if key == "sharing" and PLACEHOLDER.search(variant["headline"] + variant["body"]):
            raise ValueError("permission_denied sharing-cause copy must not contain placeholders")
    if denied["data_display"] != "hidden":
        raise ValueError("permission_denied must hide data behind the denial")
    guarantees = denied.get("guarantees", {})
    if guarantees.get("rest_of_surface_usable") is not True:
        raise ValueError("permission_denied must keep the rest of the surface usable")
    if guarantees.get("discloses_hidden_data") is not False:
        raise ValueError("permission_denied must not disclose hidden data")
    quota = states["quota_exceeded"]
    if quota.get("guarantees", {}).get("states_what_remains_available") is not True:
        raise ValueError("quota_exceeded must state what remains available")
    if quota["data_display"] != "shown":
        raise ValueError("quota_exceeded must keep what the capability produced visible")
    degraded = states["degraded"]
    if degraded["scopes"] != ["surface"]:
        raise ValueError("degraded is a surface-scope notice")
    # Degraded composes only over self-resolving dependency failures; a denial or an exhausted
    # quota already names what still works and offers one action, so it never adds a notice.
    for state_id, state in states.items():
        composes = state["composes_to_degraded"]
        if state_id in DEGRADED_PRODUCERS and composes is not True:
            raise ValueError(f"A supplementary region in {state_id} must compose to degraded")
        if state_id not in DEGRADED_PRODUCERS and composes is not False:
            raise ValueError(f"A region in {state_id} must not compose to degraded")


def _check_distinctions(data, states):
    distinctions = _unique_ids(data["distinctions"], "distinction")
    pairs = {frozenset(item["states"]) for item in distinctions.values()}
    for pair in REQUIRED_DISTINCTIONS:
        if frozenset(pair) not in pairs:
            raise ValueError(f"Missing distinction between {pair[0]} and {pair[1]}")
    for item in distinctions.values():
        for state_id in item["states"]:
            if state_id not in states:
                raise ValueError(f"Distinction {item['id']}: unknown state {state_id!r}")
            if state_id not in item["observable_difference"]:
                raise ValueError(f"Distinction {item['id']}: observable_difference must name both states")
        if set(item["data_shown"]) != set(item["states"]):
            raise ValueError(f"Distinction {item['id']}: data_shown must cover both states")
        for state_id, shown in item["data_shown"].items():
            if shown != states[state_id]["data_display"]:
                raise ValueError(f"Distinction {item['id']}: data_shown disagrees with state {state_id}")
        if len(set(item["data_shown"].values())) != 2:
            raise ValueError(f"Distinction {item['id']}: states are not observably different")


def _check_contract_conditions(data, states):
    conditions = _unique_ids(data["contract_conditions"], "contract condition")
    for condition_id, state_id in REQUIRED_CONTRACT_CONDITIONS.items():
        if condition_id not in conditions:
            raise ValueError(f"Missing contract-level condition: {condition_id}")
        if conditions[condition_id]["binds_to"] != state_id:
            raise ValueError(f"Contract condition {condition_id} must bind to {state_id}")
    for condition in conditions.values():
        target = states.get(condition["binds_to"])
        if target is None:
            raise ValueError(f"Contract condition {condition['id']}: binds to unknown state")
        if "cause" in condition:
            causes = {cause["id"] for cause in target.get("causes", [])}
            if condition["cause"] not in causes:
                raise ValueError(
                    f"Contract condition {condition['id']}: cause {condition['cause']!r} "
                    f"is not a cause of {target['id']}"
                )
        for text in (condition["id"], condition["description"], condition["binding_owner"]):
            token = CODE_LIKE.search(text)
            if token:
                raise ValueError(
                    f"Contract condition {condition['id']}: names a code-like token "
                    f"{token.group(0)!r}; codes belong to T-CON-12"
                )


def _template(text):
    """Regex that matches any instantiation of a canonical string's placeholders."""
    parts = PLACEHOLDER.split(text)
    pattern = "".join(re.escape(part) if index % 2 == 0 else r"(.+?)" for index, part in enumerate(parts))
    return re.compile(pattern + r"\Z", re.DOTALL)


def _instantiates(rendered, canonical):
    return _template(canonical).match(rendered) is not None


def _check_rendered_copy(example, state):
    """A worked example renders the state's canonical copy, never a paraphrase."""
    rendered = example["copy_rendered"]
    copy = state["copy"]
    templates = [(copy["headline"], copy["body"])]
    templates += [(variant["headline"], variant["body"]) for variant in copy.get("variants", {}).values()]
    if not any(
        _instantiates(rendered["headline"], headline) and _instantiates(rendered["body"], body)
        for headline, body in templates
    ):
        raise ValueError(
            f"Worked example {example['id']}: rendered copy is not an instantiation "
            f"of the canonical copy of {state['id']}"
        )
    action = state["recovery_action"]
    labels = [action["label"], *action.get("label_by_cause", {}).values()]
    if not any(_instantiates(rendered["action"], label) for label in labels):
        raise ValueError(
            f"Worked example {example['id']}: rendered action is not the recovery action of {state['id']}"
        )


def _check_worked_examples(data, states):
    examples = _unique_ids(data["worked_examples"], "worked example")
    for missing in set(REQUIRED_EXAMPLES) - set(examples):
        raise ValueError(f"Missing required worked example: {missing}")
    attributes = _unique_ids(data["signals"]["attributes"], "signal attribute")
    for example in examples.values():
        expected = REQUIRED_EXAMPLES.get(example["id"], example["state"])
        if example["state"] != expected:
            raise ValueError(f"Worked example {example['id']} must use state {expected}")
        if example["state"] not in states:
            raise ValueError(f"Worked example {example['id']}: unknown state {example['state']!r}")
        state = states[example["state"]]
        causes = {cause["id"] for cause in state.get("causes", [])}
        if causes and example.get("cause") not in causes:
            raise ValueError(f"Worked example {example['id']} must name a cause of {state['id']}")
        for text in example["copy_rendered"].values():
            term = forbidden_term(text, data["forbidden_terms"])
            if term:
                raise ValueError(f"Worked example {example['id']}: forbidden term {term!r}")
        _check_rendered_copy(example, state)
        record = example["signal_recorded"]
        if record["signal"] != state["signal"]:
            raise ValueError(f"Worked example {example['id']}: signal must be {state['signal']}")
        for key, value in record["attributes"].items():
            if key not in attributes:
                raise ValueError(f"Worked example {example['id']}: undeclared signal attribute {key!r}")
            allowed = attributes[key].get("values")
            if allowed and value not in allowed:
                raise ValueError(f"Worked example {example['id']}: attribute {key!r} value not allowed")
        surface_id = record["attributes"].get("surface_id", "")
        if not surface_id.startswith("example_"):
            raise ValueError(
                f"Worked example {example['id']}: surface_id must be prefixed example_; "
                "no client registers surfaces yet"
            )


def _check_adoption(data, states):
    adoption = data["adoption"]
    assertions = _unique_ids(adoption["coverage_assertions"], "coverage assertion")
    for required in REQUIRED_ASSERTIONS:
        if required not in assertions:
            raise ValueError(f"Missing coverage assertion: {required}")
    registration = adoption["illustrative_surface_registration"]
    for state_id in registration["applicable_states"]:
        if state_id not in states:
            raise ValueError(f"Illustrative registration names unknown state {state_id!r}")
    if registration["client"] not in data["clients"]:
        raise ValueError("Illustrative registration names an unknown client")


def _state_sections(document, states):
    """Slice the document into each state's own `### 3.n \\`<id>\\`` section."""
    headings = list(re.finditer(r"^### 3\.\d+ `([a-z][a-z0-9_]*)`\s*$", document, re.MULTILINE))
    sections = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        following = re.search(r"^## ", document[heading.end():end], re.MULTILINE)
        if following:
            end = heading.end() + following.start()
        sections[heading.group(1)] = document[heading.start():end]
    for state_id in states:
        if state_id not in sections:
            raise ValueError(f"Document has no section headed ### 3.n `{state_id}`")
    return sections


def _check_document(data, document, states):
    # Each state's own section must carry its canonical copy verbatim, so a paraphrase in the
    # state's definition cannot hide behind another mention elsewhere in the document. The
    # document hard-wraps prose and wraps placeholders in code spans; neither changes wording.
    sections = _state_sections(document, states)
    for state_id, state in states.items():
        plain = re.sub(r"\s+", " ", sections[state_id].replace("`", ""))
        for text in canonical_strings(state):
            if text not in plain:
                raise ValueError(
                    f"Section 3.n `{state_id}` does not carry the canonical copy {text!r} verbatim"
                )
    mentions = [(f"`{state_id}`", f"state `{state_id}`") for state_id in states]
    mentions += [
        (f"`{state['recovery_action']['id']}`", f"recovery action `{state['recovery_action']['id']}`")
        for state in states.values()
    ]
    mentions += [(item["title"], f"section {item['title']!r}") for item in data["distinctions"]]
    mentions += [(item["title"], f"worked example {item['title']!r}") for item in data["worked_examples"]]
    mentions += [(f"`{item['id']}`", f"contract condition `{item['id']}`") for item in data["contract_conditions"]]
    mentions += [(f"`{item['id']}`", f"copy rule `{item['id']}`") for item in data["copy_rules"]]
    mentions += [
        (f"`{item['id']}`", f"coverage assertion `{item['id']}`")
        for item in data["adoption"]["coverage_assertions"]
    ]
    mentions += [
        (data["taxonomy_version"], f"taxonomy version {data['taxonomy_version']}"),
        (DATA, f"data file {DATA}"),
        (SCHEMA, f"schema file {SCHEMA}"),
    ]
    for needle, label in mentions:
        if needle not in document:
            raise ValueError(f"Document does not mention {label}")


def check_taxonomy(data, document):
    """Enforce the rules the acceptance criteria state; return a short summary."""
    for rule in REQUIRED_COPY_RULES:
        if rule not in _unique_ids(data["copy_rules"], "copy rule"):
            raise ValueError(f"Missing copy rule: {rule}")
    states = _unique_ids(data["states"], "state")
    _check_states(data, states)
    _check_distinctions(data, states)
    _check_contract_conditions(data, states)
    _check_worked_examples(data, states)
    _check_adoption(data, states)
    _check_document(data, document, states)
    return {
        "taxonomy_version": data["taxonomy_version"],
        "states": len(states),
        "contract_conditions": len(data["contract_conditions"]),
        "worked_examples": len(data["worked_examples"]),
    }


def validate_taxonomy(root=None):
    """Validate the published files under root; raise ValueError on the first problem."""
    root = ROOT if root is None else Path(root)
    data = load_json(root / DATA)
    schema = load_json(root / SCHEMA)
    validate_schema(data, schema)
    return check_taxonomy(data, (root / DOCUMENT).read_text(encoding="utf-8"))


def main():
    try:
        summary = validate_taxonomy()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Client state taxonomy check failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Client state taxonomy {summary['taxonomy_version']} valid: {summary['states']} states, "
        f"{summary['contract_conditions']} conceptual contract conditions, "
        f"{summary['worked_examples']} worked examples; no client coverage implied."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
