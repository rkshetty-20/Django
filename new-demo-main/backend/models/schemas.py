from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# -----------------------------
# Existing frontend API schemas
# -----------------------------

ClaimClassification = Literal["VERIFIED", "CONDITIONAL", "MISLEADING", "NON-VERIFIABLE"]
ClaimSeverity = Literal["HIGH", "MEDIUM", "LOW"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


class AnalyzeRequest(BaseModel):
    product_name: str = Field(..., min_length=1)
    marketing_text: str = Field(..., min_length=1)
    specs: str = ""


class DimensionScores(BaseModel):
    transparency: int = Field(..., ge=0, le=100)
    verifiability: int = Field(..., ge=0, le=100)
    comparability: int = Field(..., ge=0, le=100)
    consistency: int = Field(..., ge=0, le=100)


class FlaggedClaim(BaseModel):
    claim: str
    classification: ClaimClassification
    severity: ClaimSeverity
    reason: str
    realistic_interpretation: str


class NormalizedSpecItem(BaseModel):
    term: str
    meaning: str


class RealWorldItem(BaseModel):
    feature: str
    insight: str
    confidence: ConfidenceLevel


class AnalysisResponse(BaseModel):
    truth_score: int = Field(..., ge=0, le=100)
    dimensions: DimensionScores
    tldr: list[str] = Field(default_factory=list, min_length=3, max_length=3)
    flagged_claims: list[FlaggedClaim] = Field(default_factory=list)
    normalized_specs: list[NormalizedSpecItem] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    real_world: list[RealWorldItem] = Field(default_factory=list)
    verdict: str


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    context: AnalysisResponse | None = None


class ChatResponse(BaseModel):
    answer: str


# -----------------------------
# Spec_C extension API schemas
# -----------------------------

SpecCConfidence = Literal["high", "medium", "low"]


class SpecCNormalizedProduct(BaseModel):
    name: str = ""
    brand: str = ""
    price: str = ""
    currency: str = ""
    description: str = ""
    features: list[str] = Field(default_factory=list)
    specs: dict[str, str] = Field(default_factory=dict)
    rating: str = ""
    review_count: str = ""
    availability: str = ""
    source: str = ""
    url: str = ""


class SpecCExtractionMeta(BaseModel):
    extractor: str = Field(..., min_length=1)
    page_type_confidence: float = Field(..., ge=0.0, le=1.0)
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SpecCAnalyzeRequest(BaseModel):
    product: SpecCNormalizedProduct
    fingerprint: str = Field(..., min_length=8, max_length=128)
    meta: SpecCExtractionMeta
    # For future: extension_version, request_id, user toggles, etc.
    client: dict[str, Any] = Field(default_factory=dict)


class SpecCFlag(BaseModel):
    type: str = Field(..., min_length=1)
    claim: str = ""
    reason: str = ""
    reality: str = ""


class SpecCAnalysisResponse(BaseModel):
    truth_score: int = Field(..., ge=0, le=100)
    confidence: SpecCConfidence
    summary: str
    flags: list[SpecCFlag] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    verdict: str
