from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable

from backend.models.schemas import SpecCAnalysisResponse, SpecCAnalyzeRequest, SpecCFlag
from backend.services.llm_provider import LLMError, resilient_call_with_fallback

logger = logging.getLogger("specc.engine")


VAGUE_PATTERNS: list[tuple[str, str]] = [
    (r"\bup to\b", "Uses 'up to' which depends on conditions."),
    (r"\bbest\b|\bbest-in-class\b|\bbest in class\b", "Superlative claim without a measurable benchmark."),
    (r"\bindustry[- ]leading\b", "Comparison claim without named baseline."),
    (r"\brevolutionary\b|\bgame[- ]changer\b", "Hype language; not directly verifiable."),
    (r"\bworld(?:'s)?\s*#?1\b", "Global ranking claim without cited source."),
]


def _clamp_0_100(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _confidence_label(score_0_1: float) -> str:
    if score_0_1 >= 0.75:
        return "high"
    if score_0_1 >= 0.45:
        return "medium"
    return "low"


def _iter_claim_lines(product: dict) -> Iterable[str]:
    description = (product.get("description") or "").strip()
    features = product.get("features") or []
    specs = product.get("specs") or {}

    if description:
        # Split on sentence-ish boundaries; keep short and deterministic.
        for part in re.split(r"(?<=[.!?])\s+|\n+", description):
            part = part.strip(" \t•-–—")
            if len(part) >= 8:
                yield part[:280]

    for item in features:
        item = (item or "").strip(" \t•-–—")
        if len(item) >= 6:
            yield item[:280]

    # Specs sometimes contain marketing-y values too.
    for k, v in specs.items():
        k = (k or "").strip()
        v = (v or "").strip()
        if not k or not v:
            continue
        candidate = f"{k}: {v}"
        if len(candidate) >= 10:
            yield candidate[:280]


def _deterministic_flags(request: SpecCAnalyzeRequest) -> list[SpecCFlag]:
    product = request.product.model_dump()
    flags: list[SpecCFlag] = []

    for claim in _iter_claim_lines(product):
        lowered = claim.lower()
        for pattern, reason in VAGUE_PATTERNS:
            if re.search(pattern, lowered):
                flags.append(
                    SpecCFlag(
                        type="non-verifiable",
                        claim=claim,
                        reason=reason,
                        reality="Treat as marketing language unless supported by measurable specs or cited tests.",
                    )
                )
                break

    # Missing critical fields -> transparency flags.
    missing = set((request.meta.missing_fields or []))
    for field in ("name", "price", "brand", "rating", "review_count", "availability"):
        if not getattr(request.product, field, ""):
            missing.add(field)

    if missing:
        flags.append(
            SpecCFlag(
                type="insufficient-data",
                claim="",
                reason=f"Missing key fields: {', '.join(sorted(missing))}.",
                reality="Truth score and verdict are less reliable when product data is incomplete.",
            )
        )

    # Consistency warnings surfaced from extractor.
    for warning in request.meta.warnings or []:
        flags.append(
            SpecCFlag(
                type="extraction-warning",
                claim="",
                reason=warning[:240],
                reality="The page structure may be dynamic/variant; extracted data may be partial.",
            )
        )

    return flags[:12]


def _deterministic_score(request: SpecCAnalyzeRequest, flags: list[SpecCFlag]) -> int:
    # Start from extraction confidence; penalize for missing fields + vague claims.
    base = 50.0 + 50.0 * float(request.meta.extraction_confidence)

    missing_penalty = 0.0
    for f in flags:
        if f.type == "insufficient-data":
            missing_penalty += 18.0
        if f.type == "non-verifiable":
            missing_penalty += 4.0
        if f.type == "extraction-warning":
            missing_penalty += 6.0

    # Reward structured evidence: specs richness + numeric claims.
    specs_count = len(request.product.specs or {})
    reward = min(12.0, specs_count * 1.5)

    score = base + reward - missing_penalty
    return _clamp_0_100(score)


SPEC_C_LLM_SYSTEM = """You are Spec_C Truth Engine.
You MUST follow strict anti-hallucination rules:
- Use ONLY the provided product JSON and extractor meta.
- Do NOT add any facts, tests, comparisons, or brand assumptions.
- If uncertain or data is missing, state uncertainty explicitly.

Return ONLY valid JSON matching this schema:
{
  "summary": string,
  "insights": [string],
  "verdict": string,
  "flags": [
    {"type": string, "claim": string, "reason": string, "reality": string}
  ]
}

Rules:
- insights: 0..6 items, each <= 140 chars, no external references.
- verdict: <= 120 chars, must be consistent with truth_score/confidence.
- flags: may refine provided flags but must not introduce new facts."""


def _llm_enrich(
    request: SpecCAnalyzeRequest,
    truth_score: int,
    confidence: str,
    seed_flags: list[SpecCFlag],
) -> tuple[str, list[str], str, list[SpecCFlag]]:
    if (os.getenv("SPEC_C_DISABLE_LLM") or "").strip().lower() in ("1", "true", "yes", "on"):
        return "", [], "", seed_flags

    # If no credentials, skip AI enrichment (still grounded).
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
        return "", [], "", seed_flags

    # Deterministic request id based on fingerprint to aid caching/tracing.
    request_id = hashlib.sha256(request.fingerprint.encode("utf-8")).hexdigest()[:12]

    payload = {
        "product": request.product.model_dump(),
        "meta": request.meta.model_dump(),
        "truth_score": truth_score,
        "confidence": confidence,
        "seed_flags": [f.model_dump() for f in seed_flags],
    }

    raw_text, _meta = resilient_call_with_fallback(
        messages=[
            {"role": "system", "content": SPEC_C_LLM_SYSTEM},
            {"role": "user", "content": str(payload)},
        ],
        max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "900") or "900"),
        timeout_s=float(os.getenv("LLM_TIMEOUT_SECONDS", "18") or "18"),
        request_id=f"specc_{request_id}",
    )

    import json

    try:
        data = json.loads(raw_text.strip())
    except Exception:
        logger.warning("specc_llm_invalid_json request_id=%s", request_id)
        return "", [], "", seed_flags

    summary = (data.get("summary") or "").strip()
    verdict = (data.get("verdict") or "").strip()
    insights = [str(x).strip() for x in (data.get("insights") or []) if str(x).strip()]

    flags_out: list[SpecCFlag] = []
    for item in (data.get("flags") or [])[:12]:
        try:
            flags_out.append(SpecCFlag.model_validate(item))
        except Exception:
            continue

    # Guardrails: never drop "insufficient-data" if extraction confidence is low.
    if request.meta.extraction_confidence < 0.45 and not any(f.type == "insufficient-data" for f in flags_out):
        flags_out.append(
            SpecCFlag(
                type="insufficient-data",
                claim="",
                reason="Low extraction confidence.",
                reality="The page did not provide enough reliable product data for strong conclusions.",
            )
        )

    return summary, insights[:6], verdict, (flags_out or seed_flags)


def analyze(request: SpecCAnalyzeRequest) -> SpecCAnalysisResponse:
    seed_flags = _deterministic_flags(request)
    truth_score = _deterministic_score(request, seed_flags)

    # Propagate confidence from both page detection and extraction.
    combined_conf = float(request.meta.page_type_confidence) * float(request.meta.extraction_confidence)
    confidence = _confidence_label(combined_conf)

    summary = ""
    verdict = ""
    insights: list[str] = []
    flags = seed_flags

    try:
        summary, insights, verdict, flags = _llm_enrich(request, truth_score, confidence, seed_flags)
    except LLMError:
        # Let API layer handle typed error if needed. Here we just fall back.
        summary = ""
        verdict = ""
        insights = []
        flags = seed_flags

    if not summary:
        summary = (
            "Grounded analysis based on extracted product page data only. "
            "Confidence reflects how complete and consistent the extracted fields are."
        )
    if not verdict:
        if confidence == "low":
            verdict = "Insufficient data to make a reliable call."
        elif truth_score >= 75:
            verdict = "Looks consistent; marketing claims seem mostly supported by visible specs."
        elif truth_score >= 55:
            verdict = "Mixed signals; treat standout claims cautiously and verify key specs."
        else:
            verdict = "High marketing risk; verify claims and compare alternatives before buying."

    # Ensure insights are always input-bound.
    if not insights and (request.product.price or request.product.rating or request.product.review_count):
        if request.product.price:
            insights.append(f"Listed price observed on page: {request.product.price} {request.product.currency}".strip())
        if request.product.rating or request.product.review_count:
            insights.append(
                f"Social proof on page: rating={request.product.rating or 'n/a'}, reviews={request.product.review_count or 'n/a'}."
            )
        insights = insights[:6]

    return SpecCAnalysisResponse(
        truth_score=truth_score,
        confidence=confidence,  # type: ignore[arg-type]
        summary=summary[:600],
        flags=flags,
        insights=[x[:140] for x in insights][:6],
        verdict=verdict[:120],
    )

