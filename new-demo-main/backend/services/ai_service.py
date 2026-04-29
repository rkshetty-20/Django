import hashlib
import json
import logging
import os
from typing import Any

from pydantic import ValidationError
from dotenv import load_dotenv

from backend.models.schemas import AnalysisResponse, AnalyzeRequest
from backend.services.llm_provider import (
    LLMError,
    analysis_cache_key,
    get_cached_analysis,
    resilient_call_with_fallback,
    set_cached_analysis,
)


load_dotenv()

logger = logging.getLogger("truthcart.analysis")

ANALYSIS_SYSTEM_PROMPT = """You are a consumer technology truth analysis engine.
Return ONLY valid JSON matching this exact schema:
{
  "truth_score": number,
  "dimensions": {
    "transparency": number,
    "verifiability": number,
    "comparability": number,
    "consistency": number
  },
  "tldr": [string, string, string],
  "flagged_claims": [
    {
      "claim": string,
      "classification": "VERIFIED | CONDITIONAL | MISLEADING | NON-VERIFIABLE",
      "severity": "LOW | MEDIUM | HIGH",
      "reason": string,
      "realistic_interpretation": string
    }
  ],
  "normalized_specs": [
    {
      "term": string,
      "meaning": string
    }
  ],
  "tradeoffs": [string],
  "real_world": [
    {
      "feature": string,
      "insight": string,
      "confidence": "HIGH | MEDIUM | LOW"
    }
  ],
  "verdict": string
}

Rules:
- Output JSON only. No markdown, no prose outside JSON.
- Score every dimension from 0 to 100.
- truth_score must also be 0 to 100 and reflect the dimensions.
- Always return exactly 3 TL;DR bullets.
- Do not hallucinate missing specs or benchmarks.
- If specs are missing, say so inside relevant fields instead of inventing details.
- Be critical but fair, grounded only in the provided product details.
- Flag vague phrases like "up to", "best-in-class", "industry-leading", "revolutionary", unnamed comparisons, and other non-verifiable marketing language when present."""

CHAT_SYSTEM_PROMPT = """You are a consumer tech truth assistant.
Answer ONLY using the provided analysis.
Do not hallucinate.
Be concise and practical."""

DEFAULT_MAX_OUTPUT_TOKENS = 1800


def _get_max_output_tokens() -> int:
    configured = os.getenv("LLM_MAX_OUTPUT_TOKENS")
    if configured and configured.isdigit():
        return int(configured)
    return DEFAULT_MAX_OUTPUT_TOKENS


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return JSON.")
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError as exc:
            raise ValueError("Unable to parse model JSON output.") from exc


def _validate_analysis_payload(payload: dict[str, Any]) -> AnalysisResponse:
    normalized = dict(payload)
    tldr = list(normalized.get("tldr", []))
    if len(tldr) < 3:
        tldr.extend(["Insufficient information to generate this takeaway."] * (3 - len(tldr)))
    normalized["tldr"] = tldr[:3]
    return AnalysisResponse.model_validate(normalized)


def _analysis_messages(data: AnalyzeRequest, strict_json_retry: bool = False) -> list[dict[str, str]]:
    retry_instruction = ""
    if strict_json_retry:
        retry_instruction = (
            "\nYour previous response was invalid JSON or did not match schema. "
            "Return corrected JSON only."
        )

    specs_text = data.specs.strip() if data.specs.strip() else "Specs not provided."
    return [
        {
            "role": "system",
            "content": (
                "You are TruthCart, a consumer-tech truth analysis engine.\n"
                "Return ONLY minified valid JSON matching this schema:\n"
                "{"
                '"truth_score":0,'
                '"dimensions":{"transparency":0,"verifiability":0,"comparability":0,"consistency":0},'
                '"tldr":["","",""],'
                '"flagged_claims":[{"claim":"","classification":"VERIFIED|CONDITIONAL|MISLEADING|NON-VERIFIABLE","severity":"LOW|MEDIUM|HIGH","reason":"","realistic_interpretation":""}],'
                '"normalized_specs":[{"term":"","meaning":""}],'
                '"tradeoffs":[""],'
                '"real_world":[{"feature":"","insight":"","confidence":"HIGH|MEDIUM|LOW"}],'
                '"verdict":""'
                "}\n"
                "Rules:\n"
                "- JSON only. No markdown.\n"
                "- All scores 0..100 integers.\n"
                "- tldr must be exactly 3 strings.\n"
                "- Do not invent benchmarks/specs; if missing, say so inside fields.\n"
                "- Flag vague/hedged claims (e.g., 'up to', unnamed comparisons).\n"
                + (retry_instruction or "")
            ),
        },
        {
            "role": "user",
            "content": (
                f"Product name: {data.product_name}\n"
                f"Marketing text:\n{data.marketing_text.strip()}\n\n"
                f"Technical specifications:\n{specs_text}"
            ),
        },
    ]


def generate_analysis(data: AnalyzeRequest) -> AnalysisResponse:
    max_output_tokens = _get_max_output_tokens()
    last_error: Exception | None = None

    request_id = analysis_cache_key(data.product_name, data.marketing_text, data.specs)[:12]

    for attempt in range(2):  # second pass only for strict JSON correction
        try:
            raw_text, _meta = resilient_call_with_fallback(
                messages=_analysis_messages(data, strict_json_retry=attempt > 0),
                max_output_tokens=max_output_tokens,
                timeout_s=float(os.getenv("LLM_TIMEOUT_SECONDS", "20") or "20"),
                request_id=request_id,
            )
        except LLMError as exc:
            # Typed error: keep it typed so the API layer can return safe structured detail.
            raise

        try:
            payload = _extract_json_payload(raw_text)
            return _validate_analysis_payload(payload)
        except (ValueError, ValidationError) as exc:
            last_error = exc

    if last_error is not None:
        raise ValueError("Failed to generate valid structured analysis.") from last_error
    raise ValueError("Failed to generate analysis.")


def analyze_product(data: AnalyzeRequest) -> AnalysisResponse:
    cache_key = analysis_cache_key(data.product_name, data.marketing_text, data.specs)
    logger.info("analysis_start cache_key=%s product=%s", cache_key[:12], data.product_name.strip()[:80])
    cached = get_cached_analysis(cache_key)
    if cached is not None:
        logger.info("analysis_cache_hit cache_key=%s", cache_key[:12])
        return cached

    result = generate_analysis(data)
    set_cached_analysis(cache_key, result)
    logger.info("analysis_complete cache_key=%s truth_score=%s", cache_key[:12], result.truth_score)
    return result


def generate_chat_response(query: str, context: AnalysisResponse) -> str:
    max_output_tokens = min(_get_max_output_tokens(), 600)
    request_id = hashlib.sha256(f"{query.strip()}|{context.truth_score}".encode("utf-8")).hexdigest()[:12]
    try:
        raw_text, _meta = resilient_call_with_fallback(
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Analysis JSON:\n{context.model_dump_json(indent=2)}\n\n"
                        f"User question: {query.strip()}"
                    ),
                },
            ],
            max_output_tokens=max_output_tokens,
            timeout_s=float(os.getenv("LLM_TIMEOUT_SECONDS", "20") or "20"),
            request_id=request_id,
        )
    except LLMError as exc:
        raise

    answer = raw_text.strip()
    if not answer:
        raise ValueError("Failed to generate chat response.")
    return answer
