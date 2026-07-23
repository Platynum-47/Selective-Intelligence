#!/usr/bin/env python3
"""Intent locking and reconciliation for Selective Intelligence.

This module is deliberately provider-neutral. It can accept a richer structured
classification from any reasoning adapter, but it always preserves the raw user
text and applies conservative deterministic extraction first. The deterministic
path never invents facts or silently weakens explicit constraints.
"""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

_INTENT_SCHEMA = "si.intent_contract.v1"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _event_id() -> str:
    return f"intent-{uuid.uuid4().hex[:12]}"


def _clauses(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|[\r\n]+|\s*;\s*", text.strip())
    return [p.strip(" \t-•") for p in parts if p.strip(" \t-•")]


def _norm(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(text.split())


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = _norm(item)
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _extract_prohibited_concepts(clause: str) -> list[str]:
    lowered = clause.lower()
    patterns = [
        r"(?:do not|don't|must not|never)\s+(.+)",
        r"\bno\s+(.+)",
        r"(?:rather than|instead of)\s+(.+)",
    ]
    concepts: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            value = match.group(1).strip(" .,:;")
            value = re.split(r"\b(?:and|or|but)\b", value, maxsplit=1)[0].strip()
            if value:
                concepts.append(value)
    return concepts


def _extract_required_concepts(clause: str) -> list[str]:
    lowered = clause.lower()
    concepts: list[str] = []
    for pattern in (
        r"(?:must|should|needs? to|required to)\s+(.+)",
        r"(?:only)\s+(.+)",
        r"(?:rather than|instead of)\s+.+?[,;]?\s*(?:use|show|display|implement)\s+(.+)",
    ):
        match = re.search(pattern, lowered)
        if match:
            value = match.group(1).strip(" .,:;")
            if value:
                concepts.append(value)
    return concepts


def validate_override(override: dict[str, Any]) -> None:
    allowed = {
        "product_intent",
        "process_directives",
        "constraints",
        "prohibitions",
        "acceptance_criteria",
        "assumptions",
        "unknowns",
        "contradictions",
        "required_concepts",
        "superseded_concepts",
    }
    unknown = sorted(set(override) - allowed)
    if unknown:
        raise ValueError(f"unsupported intent override fields: {', '.join(unknown)}")
    for key, value in override.items():
        if key == "product_intent":
            if not isinstance(value, str):
                raise ValueError("product_intent override must be a string")
        elif not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError(f"{key} override must be a list of strings")


def classify_intent(
    raw_text: str,
    *,
    event_type: str = "request",
    structured_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify an instruction without discarding the source text.

    A reasoning adapter may supply ``structured_override``. Explicit text-derived
    prohibitions are always retained even when an override is supplied.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        raise ValueError("intent text is empty")

    clauses = _clauses(raw_text)
    prohibitions: list[str] = []
    constraints: list[str] = []
    process: list[str] = []
    acceptance: list[str] = []
    product: list[str] = []
    required: list[str] = []
    superseded: list[str] = []

    for clause in clauses:
        low = clause.lower()
        is_prohibition = bool(re.search(r"\b(do not|don't|must not|never|no)\b", low))
        is_process = bool(
            re.search(
                r"\b(first|before|inspect|discover|verify|validate|report|preserve|continue|stop|resume)\b",
                low,
            )
        )
        is_acceptance = bool(re.search(r"\b(must|should|only|required|acceptance|complete|verified)\b", low))
        is_product = bool(
            re.search(r"\b(add|build|create|implement|fix|repair|update|change|make|turn|produce|design)\b", low)
        )

        if is_prohibition:
            prohibitions.append(clause)
            constraints.append(clause)
            superseded.extend(_extract_prohibited_concepts(clause))
        if is_process:
            process.append(clause)
        if is_acceptance:
            acceptance.append(clause)
            required.extend(_extract_required_concepts(clause))
        if is_product and not is_prohibition:
            product.append(clause)

    if not product:
        product = [clauses[0]]

    result: dict[str, Any] = {
        "schemaVersion": _INTENT_SCHEMA,
        "eventId": _event_id(),
        "eventType": event_type,
        "timestamp": _now(),
        "rawText": raw_text,
        "product_intent": " ".join(_dedupe(product)),
        "process_directives": _dedupe(process),
        "constraints": _dedupe(constraints),
        "prohibitions": _dedupe(prohibitions),
        "acceptance_criteria": _dedupe(acceptance),
        "assumptions": [],
        "unknowns": [],
        "contradictions": [],
        "required_concepts": _dedupe(required),
        "superseded_concepts": _dedupe(superseded),
        "source": "deterministic_explicit_text",
    }

    if structured_override:
        validate_override(structured_override)
        for key, value in structured_override.items():
            if key == "product_intent":
                if value.strip():
                    result[key] = value.strip()
            else:
                result[key] = _dedupe(result.get(key, []) + value)
        result["source"] = "deterministic_text_plus_validated_reasoning_adapter"

    return result


def merge_active_contract(active: dict[str, Any] | None, event: dict[str, Any]) -> dict[str, Any]:
    """Merge a request/correction into the active contract without losing history."""
    active = dict(active or {})
    if not active:
        return {
            "schemaVersion": _INTENT_SCHEMA,
            "product_intent": event["product_intent"],
            "process_directives": list(event["process_directives"]),
            "constraints": list(event["constraints"]),
            "prohibitions": list(event["prohibitions"]),
            "acceptance_criteria": list(event["acceptance_criteria"]),
            "assumptions": list(event["assumptions"]),
            "unknowns": list(event["unknowns"]),
            "contradictions": list(event["contradictions"]),
            "required_concepts": list(event["required_concepts"]),
            "superseded_concepts": list(event["superseded_concepts"]),
            "sourceEventIds": [event["eventId"]],
            "updatedAt": _now(),
        }

    if event.get("product_intent"):
        # A correction refines the contract; retain the original objective and add
        # the correction as an explicit acceptance constraint rather than silently
        # replacing the objective.
        active.setdefault("refinements", []).append(event["product_intent"])
    for key in (
        "process_directives",
        "constraints",
        "prohibitions",
        "acceptance_criteria",
        "assumptions",
        "unknowns",
        "contradictions",
        "required_concepts",
        "superseded_concepts",
    ):
        active[key] = _dedupe(list(active.get(key, [])) + list(event.get(key, [])))
    active.setdefault("sourceEventIds", []).append(event["eventId"])
    active["updatedAt"] = _now()
    return active


def concept_tokens(values: list[str]) -> set[str]:
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
        "must", "should", "do", "not", "only", "it", "this", "that", "be", "is",
    }
    tokens: set[str] = set()
    for value in values:
        tokens.update(t for t in _norm(value).split() if len(t) > 2 and t not in stop)
    return tokens
