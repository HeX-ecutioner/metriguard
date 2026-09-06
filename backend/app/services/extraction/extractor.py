"""
Declaration Extractor service for MetriGuard.
Extracts declarations from OCR outputs across all 13 Legal Metrology declaration types.
Strictly decoupled from legal compliance decisions.
Handles multi-candidate resolution, conflict detection, and audit traceability.
"""

import logging
from typing import List, Dict, Optional, Union, Any, Tuple
from collections import defaultdict

from app.models.ocr_schemas import OCRResult, OCRItem, OCRBoundingBox
from app.models.declaration_schemas import (
    DeclarationType,
    ExtractionStatus,
    ExtractionCandidate,
    ExtractedDeclaration,
    DeclarationExtractionResult,
)
from app.services.extraction.patterns import EXTRACTION_PATTERNS

logger = logging.getLogger(__name__)

# Reliability confidence threshold
DEFAULT_CONFIDENCE_THRESHOLD = 0.60


class DeclarationExtractor:
    """
    Deterministic rule and pattern-based extractor.
    Parses OCR recognized items, evaluates candidates, flags ambiguities,
    and returns traceable extraction representations.
    """

    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.patterns = EXTRACTION_PATTERNS

    def extract_from_ocr(
        self,
        ocr_input: Union[OCRResult, List[OCRItem], List[str], str],
        image_id: Optional[Union[int, str]] = None
    ) -> DeclarationExtractionResult:
        """
        Extracts packaged commodity declarations from OCR output.
        Accepts:
          - OCRResult object
          - List of OCRItem objects
          - List of raw text strings
          - A single multiline text string
        """
        # 1. Normalize input into a uniform list of OCRItem
        ocr_items, effective_image_id = self._normalize_input(ocr_input, image_id)

        # 2. Extract candidate matches across all items
        all_candidates: List[ExtractionCandidate] = []
        for item in ocr_items:
            candidates = self._extract_item_candidates(item, effective_image_id)
            all_candidates.extend(candidates)

        # 3. Consolidate and resolve candidates per declaration type
        declarations: Dict[DeclarationType, ExtractedDeclaration] = {}
        summary_counts: Dict[str, int] = defaultdict(int)
        has_ambiguities = False

        for decl_type in DeclarationType:
            type_candidates = [c for c in all_candidates if c.declaration_type == decl_type]
            extracted_decl = self._consolidate_type_candidates(decl_type, type_candidates, effective_image_id)
            declarations[decl_type] = extracted_decl
            summary_counts[extracted_decl.status.value] += 1
            if extracted_decl.status == ExtractionStatus.AMBIGUOUS:
                has_ambiguities = True

        return DeclarationExtractionResult(
            image_id=effective_image_id,
            declarations=declarations,
            all_candidates=all_candidates,
            summary=dict(summary_counts),
            has_ambiguities=has_ambiguities,
        )

    def _normalize_input(
        self,
        ocr_input: Union[OCRResult, List[OCRItem], List[str], str],
        image_id: Optional[Union[int, str]] = None
    ) -> Tuple[List[OCRItem], Optional[Union[int, str]]]:
        """Normalizes various input formats into a list of OCRItem."""
        effective_image_id = image_id

        if isinstance(ocr_input, OCRResult):
            effective_image_id = image_id or ocr_input.image_id
            if ocr_input.items:
                return ocr_input.items, effective_image_id
            # If items list is empty, split recognized_text into synthetic lines
            lines = [line.strip() for line in ocr_input.recognized_text.splitlines() if line.strip()]
            synthetic_items = [
                OCRItem(
                    text=line,
                    confidence=ocr_input.confidence,
                    bounding_box=OCRBoundingBox(x=0, y=idx * 30, width=400, height=25),
                    page_or_region_id=ocr_input.page_or_region_id
                )
                for idx, line in enumerate(lines)
            ]
            return synthetic_items, effective_image_id

        if isinstance(ocr_input, list):
            if not ocr_input:
                return [], effective_image_id
            if isinstance(ocr_input[0], OCRItem):
                return ocr_input, effective_image_id
            elif isinstance(ocr_input[0], str):
                items = [
                    OCRItem(
                        text=line.strip(),
                        confidence=0.95,
                        bounding_box=OCRBoundingBox(x=0, y=idx * 30, width=400, height=25),
                        page_or_region_id="panel_1"
                    )
                    for idx, line in enumerate(ocr_input) if line.strip()
                ]
                return items, effective_image_id

        if isinstance(ocr_input, str):
            lines = [l.strip() for l in ocr_input.splitlines() if l.strip()]
            items = [
                OCRItem(
                    text=line,
                    confidence=0.95,
                    bounding_box=OCRBoundingBox(x=0, y=idx * 30, width=400, height=25),
                    page_or_region_id="panel_1"
                )
                for idx, line in enumerate(lines)
            ]
            return items, effective_image_id

        return [], effective_image_id

    def _extract_item_candidates(
        self,
        item: OCRItem,
        source_image_id: Optional[Union[int, str]]
    ) -> List[ExtractionCandidate]:
        """Matches all patterns against an individual OCR item text."""
        matched_candidates: List[ExtractionCandidate] = []
        text = item.text.strip()
        if not text:
            return matched_candidates

        for pattern_def in self.patterns:
            matches = list(pattern_def.pattern.finditer(text))
            for match in matches:
                try:
                    raw_val, norm_val = pattern_def.extractor_func(match)
                    if raw_val and norm_val:
                        candidate_conf = round(item.confidence * pattern_def.confidence_weight, 3)
                        # Clamp confidence
                        candidate_conf = max(0.0, min(1.0, candidate_conf))

                        candidate = ExtractionCandidate(
                            declaration_type=pattern_def.declaration_type,
                            raw_value=str(raw_val).strip(),
                            normalized_value=str(norm_val).strip(),
                            confidence=candidate_conf,
                            original_ocr_text=text,
                            source_image_id=source_image_id,
                            bounding_box=item.bounding_box,
                            page_or_region_id=item.page_or_region_id,
                            pattern_name=pattern_def.name,
                            is_ambiguous=False,
                            ambiguity_reason=None,
                        )
                        matched_candidates.append(candidate)
                except Exception as e:
                    logger.debug(f"Pattern '{pattern_def.name}' extraction error on text '{text}': {e}")

        return matched_candidates

    def _consolidate_type_candidates(
        self,
        decl_type: DeclarationType,
        candidates: List[ExtractionCandidate],
        source_image_id: Optional[Union[int, str]]
    ) -> ExtractedDeclaration:
        """
        Consolidates candidates for a single declaration type.
        Detects conflicts and marks ambiguous extractions for manual review.
        """
        if not candidates:
            return ExtractedDeclaration(
                declaration_type=decl_type,
                status=ExtractionStatus.MISSING,
                value=None,
                confidence=0.0,
                candidates=[],
                source_image_id=source_image_id,
                notes="No declaration detected in OCR text.",
            )

        # Deduplicate redundant candidates on the same line with identical normalized_value:
        # Keep the candidate with the highest confidence
        line_val_map: Dict[Tuple[str, Optional[str]], ExtractionCandidate] = {}
        for c in candidates:
            key = (c.original_ocr_text, c.normalized_value)
            if key not in line_val_map or c.confidence > line_val_map[key].confidence:
                line_val_map[key] = c
        unique_candidates: List[ExtractionCandidate] = list(line_val_map.values())

        # Filter out candidates that are strict substrings of another candidate on the same line
        # (e.g. phone number or email inside a full composite consumer care line)
        subsegment_indices = set()
        for i, c1 in enumerate(unique_candidates):
            for j, c2 in enumerate(unique_candidates):
                if i != j and c1.normalized_value and c2.normalized_value:
                    if (c1.original_ocr_text == c2.original_ocr_text and
                            c1.normalized_value in c2.normalized_value and
                            len(c1.normalized_value) < len(c2.normalized_value)):
                        subsegment_indices.add(i)

        effective_candidates = [c for idx, c in enumerate(unique_candidates) if idx not in subsegment_indices]

        # Find distinct normalized values across effective candidates
        distinct_normalized_values = {c.normalized_value for c in effective_candidates if c.normalized_value}

        # Conflict resolution
        if len(distinct_normalized_values) > 1:
            # Multiple conflicting values detected!
            ambiguity_reason = (
                f"Multiple conflicting values detected: "
                f"{', '.join(repr(v) for v in sorted(distinct_normalized_values))}. "
                f"Requires manual review."
            )
            for c in unique_candidates:
                c.is_ambiguous = True
                c.ambiguity_reason = ambiguity_reason

            max_conf = max(c.confidence for c in unique_candidates)
            return ExtractedDeclaration(
                declaration_type=decl_type,
                status=ExtractionStatus.AMBIGUOUS,
                value=None,  # Do not choose silently
                confidence=max_conf,
                candidates=unique_candidates,
                source_image_id=source_image_id,
                notes=f"Ambiguous extraction: {len(distinct_normalized_values)} distinct values found. {ambiguity_reason}",
            )

        # Single consistent normalized value
        # Select best candidate by confidence from effective candidates
        best_candidate = max(effective_candidates, key=lambda c: c.confidence)

        if best_candidate.confidence < self.confidence_threshold:
            return ExtractedDeclaration(
                declaration_type=decl_type,
                status=ExtractionStatus.LOW_CONFIDENCE,
                value=best_candidate.normalized_value,
                confidence=best_candidate.confidence,
                candidates=unique_candidates,
                source_image_id=best_candidate.source_image_id or source_image_id,
                bounding_box=best_candidate.bounding_box,
                original_ocr_text=best_candidate.original_ocr_text,
                notes=(
                    f"Low confidence match ({best_candidate.confidence:.2f} < {self.confidence_threshold:.2f}). "
                    f"Recommended for manual verification."
                ),
            )

        return ExtractedDeclaration(
            declaration_type=decl_type,
            status=ExtractionStatus.FOUND,
            value=best_candidate.normalized_value,
            confidence=best_candidate.confidence,
            candidates=unique_candidates,
            source_image_id=best_candidate.source_image_id or source_image_id,
            bounding_box=best_candidate.bounding_box,
            original_ocr_text=best_candidate.original_ocr_text,
            notes=f"Authoritative match via pattern '{best_candidate.pattern_name}'.",
        )


def extract_declarations(
    ocr_input: Union[OCRResult, List[OCRItem], List[str], str],
    image_id: Optional[Union[int, str]] = None,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> DeclarationExtractionResult:
    """Convenience helper for declaration extraction."""
    extractor = DeclarationExtractor(confidence_threshold=confidence_threshold)
    return extractor.extract_from_ocr(ocr_input, image_id=image_id)
