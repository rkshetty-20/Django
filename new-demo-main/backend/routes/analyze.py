from fastapi import APIRouter, HTTPException

from backend.models.schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    ChatRequest,
    ChatResponse,
    SpecCAnalysisResponse,
    SpecCAnalyzeRequest,
)
from backend.services.ai_service import analyze_product, generate_chat_response
from backend.services.llm_provider import LLMError
from backend.services.spec_c_engine import analyze as specc_analyze


router = APIRouter()


def _extract_product_name(query: str) -> str:
    stripped = query.strip()
    if '"' in stripped:
        parts = [part.strip() for part in stripped.split('"') if part.strip()]
        if parts:
            return parts[0][:80]

    lowered = stripped.lower()
    for marker in ("about ", "for ", "is ", "of "):
        if marker in lowered:
            start = lowered.index(marker) + len(marker)
            candidate = stripped[start:].strip(" ?.!,:;")
            if candidate:
                return candidate[:80]

    return stripped[:80] or "Product from chat query"


@router.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    try:
        return analyze_product(request)
    except LLMError as exc:
        # Never leak provider details; return stable user-safe messages only.
        raise HTTPException(status_code=503, detail=exc.to_public_detail()) from exc
    except ValueError as exc:
        # Treat internal validation/prompt issues as service errors (still user-safe).
        raise HTTPException(status_code=500, detail={"code": "BAD_RESPONSE", "user_message": "Analysis service is temporarily overloaded."}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "UPSTREAM_ERROR", "user_message": "Analysis service is temporarily overloaded."}) from exc


@router.post("/spec_c/analyze", response_model=SpecCAnalysisResponse)
def analyze_spec_c(request: SpecCAnalyzeRequest) -> SpecCAnalysisResponse:
    try:
        return specc_analyze(request)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=exc.to_public_detail()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "BAD_REQUEST", "user_message": "Invalid product payload."},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "UPSTREAM_ERROR", "user_message": "Analysis service is temporarily overloaded."},
        ) from exc


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        context = request.context
        if context is None:
            analyze_request = AnalyzeRequest(
                product_name=_extract_product_name(request.query),
                marketing_text=request.query,
                specs="",
            )
            context = analyze_product(analyze_request)

        answer = generate_chat_response(request.query, context)
        return ChatResponse(answer=answer)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=exc.to_public_detail()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail={"code": "UPSTREAM_ERROR", "user_message": "Analysis service is temporarily overloaded."}) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "UPSTREAM_ERROR", "user_message": "Analysis service is temporarily overloaded."}) from exc
