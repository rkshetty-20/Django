import re
from typing import List

from models.schemas import (
    AnalysisResponse,
    ComparisonIntegrityItem,
    FeatureAttributionItem,
    FinalVerdict,
    FlaggedClaim,
    NormalizedSpecification,
    RealWorldInterpretationItem,
    TruthScore,
)


SECTION_MARKERS = {
    "CONSUMER TL;DR": "consumer_tldr",
    "FLAGGED CLAIMS": "flagged_claims",
    "NORMALIZED SPECIFICATIONS": "normalized_specifications",
    "COMPARISON INTEGRITY": "comparison_integrity",
    "CONFIGURATION CONSISTENCY": "configuration_consistency",
    "REAL-WORLD INTERPRETATION": "real_world_interpretation",
    "TRADE-OFFS": "trade_offs",
    "FEATURE ATTRIBUTION": "feature_attribution",
    "CAMERA & MEDIA REALITY": "camera_media_reality",
    "FINAL VERDICT": "final_verdict",
}


def _clean_line(line: str) -> str:
    return line.strip().lstrip("•").strip()


def _extract_section(report: str, title: str) -> str:
    pattern = rf"{re.escape(title)}\n[━]+\n(.*?)(?=\n[━]+\n(?:{'|'.join(map(re.escape, SECTION_MARKERS.keys()))}|TRUTH SCORE:)|\Z)"
    match = re.search(pattern, report, flags=re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_list_block(block: str) -> List[str]:
    items = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("• "):
            items.append(_clean_line(line[1:]))
    return items


def _parse_score(report: str) -> TruthScore:
    total = int(re.search(r"TRUTH SCORE:\s*(\d+)/100", report).group(1))
    transparency = int(re.search(r"Transparency:\s*(\d+)/30", report).group(1))
    verifiability = int(re.search(r"Verifiability:\s*(\d+)/30", report).group(1))
    comparability = int(re.search(r"Comparability:\s*(\d+)/20", report).group(1))
    consistency = int(re.search(r"Consistency:\s*(\d+)/20", report).group(1))
    justification_match = re.search(r"Justification:\s*(.+)", report)
    justification = justification_match.group(1).strip() if justification_match else ""
    return TruthScore(
        total=total,
        transparency=transparency,
        verifiability=verifiability,
        comparability=comparability,
        consistency=consistency,
        justification=justification,
    )


def _parse_flagged_claims(block: str) -> List[FlaggedClaim]:
    entries = []
    parts = re.split(r"\n- Claim:\s*", "\n" + block)
    for part in parts[1:]:
        lines = [line.strip() for line in part.strip().splitlines() if line.strip()]
        claim = lines[0].strip('"')
        values = {}
        for line in lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                values[key.lower().replace(" ", "_")] = value.strip()
        entries.append(
            FlaggedClaim(
                claim=claim,
                classification=values.get("classification", "NON-VERIFIABLE"),
                severity=values.get("severity"),
                reason=values.get("reason", ""),
                realistic_interpretation=values.get("realistic_interpretation", ""),
            )
        )
    return entries


def _parse_normalized_specs(block: str) -> List[NormalizedSpecification]:
    items = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        content = line[2:]
        if ": " not in content:
            continue
        marketing_term, standard_equivalent = content.split(": ", 1)
        items.append(
            NormalizedSpecification(
                marketing_term=marketing_term.strip(),
                standard_equivalent=standard_equivalent.strip(),
            )
        )
    return items


def _parse_comparison_integrity(block: str) -> List[ComparisonIntegrityItem]:
    entries = []
    parts = re.split(r"\n- Claim:\s*", "\n" + block)
    for part in parts[1:]:
        lines = [line.strip() for line in part.strip().splitlines() if line.strip()]
        claim = lines[0].strip('"')
        values = {}
        for line in lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                values[key.lower()] = value.strip()
        entries.append(
            ComparisonIntegrityItem(
                claim=claim,
                baseline=values.get("baseline", ""),
                issue=values.get("issue", ""),
                reframed=values.get("reframed", ""),
            )
        )
    return entries


def _parse_real_world(block: str) -> List[RealWorldInterpretationItem]:
    items = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        match = re.match(r"- (.+?): (.+) \[Confidence: (HIGH|MEDIUM|LOW)\]", line)
        if match:
            items.append(
                RealWorldInterpretationItem(
                    feature=match.group(1).strip(),
                    expectation=match.group(2).strip(),
                    confidence=match.group(3),
                )
            )
    return items


def _parse_feature_attribution(block: str) -> List[FeatureAttributionItem]:
    items = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        content = line[2:]
        if ": " not in content:
            continue
        feature, attribution = content.split(": ", 1)
        items.append(
            FeatureAttributionItem(
                feature=feature.strip(),
                attribution=attribution.strip(),
            )
        )
    return items


def _parse_final_verdict(block: str) -> FinalVerdict:
    summary_match = re.search(r"Summary:\s*(.+)", block)
    best_for_match = re.search(r"Best for:\s*(.+)", block)
    not_ideal_match = re.search(r"Not ideal for:\s*(.+)", block)
    return FinalVerdict(
        summary=summary_match.group(1).strip() if summary_match else "",
        best_for=best_for_match.group(1).strip() if best_for_match else "",
        not_ideal_for=not_ideal_match.group(1).strip() if not_ideal_match else "",
    )


def parse_analysis_report(report: str) -> AnalysisResponse:
    product_match = re.search(r"Product:\s*(.+)", report)
    category_match = re.search(r"Category:\s*(.+)", report)
    date_match = re.search(r"Analysis Date:\s*(.+)", report)

    consumer_tldr = _parse_list_block(_extract_section(report, "CONSUMER TL;DR"))
    flagged_claims = _parse_flagged_claims(_extract_section(report, "FLAGGED CLAIMS"))
    normalized_specs = _parse_normalized_specs(_extract_section(report, "NORMALIZED SPECIFICATIONS"))
    comparison_integrity = _parse_comparison_integrity(_extract_section(report, "COMPARISON INTEGRITY"))
    configuration_consistency = _parse_list_block(_extract_section(report, "CONFIGURATION CONSISTENCY"))
    real_world_interpretation = _parse_real_world(_extract_section(report, "REAL-WORLD INTERPRETATION"))
    trade_offs = _parse_list_block(_extract_section(report, "TRADE-OFFS"))
    feature_attribution = _parse_feature_attribution(_extract_section(report, "FEATURE ATTRIBUTION"))
    camera_media_reality = _parse_list_block(_extract_section(report, "CAMERA & MEDIA REALITY"))
    final_verdict = _parse_final_verdict(_extract_section(report, "FINAL VERDICT"))

    return AnalysisResponse(
        product=product_match.group(1).strip() if product_match else "",
        category=category_match.group(1).strip() if category_match else "Unknown",
        analysis_date=date_match.group(1).strip() if date_match else "",
        consumer_tldr=consumer_tldr,
        truth_score=_parse_score(report),
        flagged_claims=flagged_claims,
        normalized_specifications=normalized_specs,
        comparison_integrity=comparison_integrity,
        configuration_consistency=configuration_consistency or ["No inconsistencies detected"],
        real_world_interpretation=real_world_interpretation,
        trade_offs=trade_offs,
        feature_attribution=feature_attribution,
        camera_media_reality=camera_media_reality,
        final_verdict=final_verdict,
        raw_report=report,
    )
