import hashlib
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Literal

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI


logger = logging.getLogger("truthcart.llm")


ErrorCode = Literal[
    "OVERLOADED",
    "TIMEOUT",
    "UPSTREAM_ERROR",
    "AUTH_ERROR",
    "INVALID_REQUEST",
    "BAD_RESPONSE",
]


@dataclass(frozen=True)
class LLMError(Exception):
    code: ErrorCode
    user_message: str
    retryable: bool
    status_code: int | None = None
    provider: str | None = None
    detail: str | None = None

    def to_public_detail(self) -> dict[str, Any]:
        return {"code": self.code, "user_message": self.user_message}


def _is_openrouter_configured() -> bool:
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return bool(openrouter_api_key or (openai_api_key and openai_api_key.startswith("sk-or-v1-")))


def _get_client(timeout_s: float) -> OpenAI:
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Treat sk-or-v1 keys as OpenRouter keys for convenience.
    if openrouter_api_key or (openai_api_key and openai_api_key.startswith("sk-or-v1-")):
        api_key = openrouter_api_key or openai_api_key
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=timeout_s)

    if openai_api_key:
        return OpenAI(api_key=openai_api_key, timeout=timeout_s)

    raise LLMError(
        code="AUTH_ERROR",
        user_message="Analysis service is missing its LLM credentials.",
        retryable=False,
        provider="openrouter" if _is_openrouter_configured() else "openai",
        detail="Missing OPENAI_API_KEY or OPENROUTER_API_KEY",
    )


def _primary_model() -> str:
    if _is_openrouter_configured():
        return os.getenv("OPENROUTER_PRIMARY_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-mini"))
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def _fallback_model() -> str:
    if _is_openrouter_configured():
        # Cheaper/faster fallback; still must follow same JSON contract.
        return os.getenv("OPENROUTER_FALLBACK_MODEL", "openai/gpt-4.1-mini")
    return os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4.1-mini")


def _max_output_tokens(default: int) -> int:
    configured = os.getenv("LLM_MAX_OUTPUT_TOKENS")
    if configured and configured.isdigit():
        return int(configured)
    return default


def _retry_sleep_s(attempt: int) -> float:
    # attempt: 1..3
    base = {1: 1.5, 2: 3.0, 3: 6.0}.get(attempt, 6.0)
    jitter = random.uniform(0, min(0.6, base * 0.2))
    return base + jitter


def _normalize_provider_error(exc: Exception) -> LLMError:
    if isinstance(exc, AuthenticationError):
        return LLMError(
            code="AUTH_ERROR",
            user_message="Analysis service is temporarily misconfigured.",
            retryable=False,
            provider="openrouter" if _is_openrouter_configured() else "openai",
            detail=str(exc),
        )

    if isinstance(exc, APIConnectionError):
        return LLMError(
            code="TIMEOUT",
            user_message="Analysis is temporarily busy. Retrying…",
            retryable=True,
            provider="openrouter" if _is_openrouter_configured() else "openai",
            detail=str(exc),
        )

    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        provider_message = ""
        try:
            provider_message = str(exc)
        except Exception:
            provider_message = "APIStatusError"

        if status in (429, 503, 502, 504):
            return LLMError(
                code="OVERLOADED",
                user_message="High demand is slowing analysis. Please try again in a few seconds.",
                retryable=True,
                status_code=status,
                provider="openrouter" if _is_openrouter_configured() else "openai",
                detail=provider_message,
            )
        if status == 402:
            return LLMError(
                code="INVALID_REQUEST",
                user_message="Analysis service is temporarily unavailable.",
                retryable=False,
                status_code=status,
                provider="openrouter" if _is_openrouter_configured() else "openai",
                detail=provider_message,
            )
        if status in (400, 401, 403):
            return LLMError(
                code="INVALID_REQUEST",
                user_message="Analysis service is temporarily unavailable.",
                retryable=False,
                status_code=status,
                provider="openrouter" if _is_openrouter_configured() else "openai",
                detail=provider_message,
            )

        return LLMError(
            code="UPSTREAM_ERROR",
            user_message="Analysis service is temporarily overloaded.",
            retryable=status is not None and status >= 500,
            status_code=status,
            provider="openrouter" if _is_openrouter_configured() else "openai",
            detail=provider_message,
        )

    return LLMError(
        code="UPSTREAM_ERROR",
        user_message="Analysis service is temporarily overloaded.",
        retryable=False,
        provider="openrouter" if _is_openrouter_configured() else "openai",
        detail=repr(exc),
    )


class TTLCache:
    def __init__(self, ttl_seconds: int = 900, max_items: int = 256) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_items = max_items
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        created_at, value = item
        if time.time() - created_at > self._ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self._max_items:
            # Drop oldest item (simple + deterministic).
            oldest_key = min(self._store.items(), key=lambda kv: kv[1][0])[0]
            self._store.pop(oldest_key, None)
        self._store[key] = (time.time(), value)


_analysis_cache = TTLCache(
    ttl_seconds=int(os.getenv("LLM_CACHE_TTL_SECONDS", "900") or "900"),
    max_items=int(os.getenv("LLM_CACHE_MAX_ITEMS", "256") or "256"),
)


def analysis_cache_key(product_name: str, marketing_text: str, specs: str) -> str:
    canonical = json.dumps(
        {
            "product_name": product_name.strip(),
            "marketing_text": marketing_text.strip(),
            "specs": (specs or "").strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_cached_analysis(cache_key: str) -> Any | None:
    return _analysis_cache.get(cache_key)


def set_cached_analysis(cache_key: str, value: Any) -> None:
    _analysis_cache.set(cache_key, value)


def call_json_responses_api(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    timeout_s: float,
    request_id: str,
) -> str:
    client = _get_client(timeout_s=timeout_s)
    response = client.responses.create(
        model=model,
        input=messages,
        max_output_tokens=max_output_tokens,
    )
    text = (response.output_text or "").strip()
    if not text:
        raise LLMError(
            code="BAD_RESPONSE",
            user_message="Analysis service is temporarily overloaded.",
            retryable=True,
            provider="openrouter" if _is_openrouter_configured() else "openai",
            detail=f"Empty output_text (request_id={request_id}, model={model})",
        )
    return text


def resilient_call_with_fallback(
    *,
    messages: list[dict[str, str]],
    max_output_tokens: int,
    timeout_s: float,
    request_id: str,
) -> tuple[str, dict[str, Any]]:
    primary = _primary_model()
    fallback = _fallback_model()

    def attempt_model(model_name: str) -> str:
        last: Exception | None = None
        for attempt in range(0, 4):  # 0 initial + 3 retries
            try:
                if attempt == 0:
                    logger.info("llm_attempt_start request_id=%s model=%s", request_id, model_name)
                else:
                    logger.info(
                        "llm_retry request_id=%s model=%s retry=%s",
                        request_id,
                        model_name,
                        attempt,
                    )
                return call_json_responses_api(
                    model=model_name,
                    messages=messages,
                    max_output_tokens=max_output_tokens,
                    timeout_s=timeout_s,
                    request_id=request_id,
                )
            except Exception as exc:  # normalize below
                normalized = _normalize_provider_error(exc)
                last = normalized
                logger.warning(
                    "llm_attempt_failed request_id=%s model=%s code=%s status=%s retryable=%s detail=%s",
                    request_id,
                    model_name,
                    normalized.code,
                    normalized.status_code,
                    normalized.retryable,
                    normalized.detail,
                )
                if attempt >= 3 or not normalized.retryable:
                    raise normalized
                time.sleep(_retry_sleep_s(attempt + 1))
        if last:
            raise _normalize_provider_error(last)
        raise LLMError(
            code="UPSTREAM_ERROR",
            user_message="Analysis service is temporarily overloaded.",
            retryable=False,
            provider="openrouter" if _is_openrouter_configured() else "openai",
            detail="Unknown failure",
        )

    try:
        text = attempt_model(primary)
        return text, {"model_used": primary, "fallback_used": False}
    except LLMError as primary_error:
        if primary_error.code not in ("OVERLOADED", "TIMEOUT", "UPSTREAM_ERROR") or fallback == primary:
            raise

        logger.info("llm_fallback_triggered request_id=%s from_model=%s to_model=%s", request_id, primary, fallback)
        text = attempt_model(fallback)
        return text, {"model_used": fallback, "fallback_used": True, "primary_error_code": primary_error.code}

