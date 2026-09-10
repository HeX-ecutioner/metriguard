"""
Declaration Extractor service for MetriGuard.
Extracts declarations from OCR outputs across all 13 Legal Metrology declaration types.
Strictly decoupled from legal compliance decisions.
Handles multi-candidate resolution, conflict detection, and audit traceability.
"""

import logging
from typing import List, Dict, Optional, Union, Any, Tuple, Set
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

        scan_confidence = 1.0
        if isinstance(ocr_input, OCRResult):
            scan_confidence = ocr_input.confidence
        elif ocr_items:
            scan_confidence = round(sum(it.confidence for it in ocr_items) / len(ocr_items), 4)

        # 2. Multi-resolution layout reconstruction:
        #    a) Raw OCR items
        #    b) Horizontally reconstructed lines (grouping two-column labels / key-value items)
        #    c) Multi-line consecutive sliding windows (for composite manufacturer/packer/consumer care blocks)
        reconstructed_lines = self._reconstruct_reading_lines(ocr_items)
        multiline_windows = self._generate_multiline_windows(reconstructed_lines, max_window=5)

        # Composite multi-line declaration types that may span multiple lines
        COMPOSITE_MULTILINE_TYPES = {
            DeclarationType.MANUFACTURER,
            DeclarationType.PACKER,
            DeclarationType.IMPORTER,
            DeclarationType.CONSUMER_CARE,
        }

        all_candidates: List[ExtractionCandidate] = []

        # 3. Extract candidate matches:
        #    a) Base scan units: raw OCR items and horizontally reconstructed lines (all declaration types)
        base_units = list(ocr_items)
        seen_texts = {it.text.strip() for it in base_units if it.text}
        for rl in reconstructed_lines:
            rl_text = rl.text.strip()
            if rl_text and rl_text not in seen_texts:
                base_units.append(rl)
                seen_texts.add(rl_text)

        for item in base_units:
            candidates = self._extract_item_candidates(item, effective_image_id)
            all_candidates.extend(candidates)

        #    b) Multi-line sliding windows (strictly composite multi-line declarations)
        seen_mw_texts = set()
        for mw in multiline_windows:
            mw_text = mw.text.strip()
            if mw_text and mw_text not in seen_texts and mw_text not in seen_mw_texts:
                seen_mw_texts.add(mw_text)
                candidates = self._extract_item_candidates(
                    mw, effective_image_id, allowed_types=COMPOSITE_MULTILINE_TYPES
                )
                all_candidates.extend(candidates)

        #    c) Full consolidated text if available (strictly composite multi-line declarations)
        if isinstance(ocr_input, OCRResult) and ocr_input.recognized_text:
            rec_text = ocr_input.recognized_text.strip()
            if rec_text and rec_text not in seen_texts and rec_text not in seen_mw_texts:
                full_box = ocr_input.bounding_box or (reconstructed_lines[0].bounding_box if reconstructed_lines else None)
                full_item = OCRItem(
                    text=rec_text,
                    confidence=ocr_input.confidence,
                    bounding_box=full_box or OCRBoundingBox(x=0, y=0, width=100, height=100),
                    page_or_region_id=ocr_input.page_or_region_id
                )
                candidates = self._extract_item_candidates(
                    full_item, effective_image_id, allowed_types=COMPOSITE_MULTILINE_TYPES
                )
                all_candidates.extend(candidates)

        # 4. Consolidate and resolve candidates per declaration type
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
            overall_confidence=scan_confidence,
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

    def _reconstruct_reading_lines(self, items: List[OCRItem]) -> List[OCRItem]:
        """
        Clusters OCR items sharing the same horizontal baseline (two-column labels,
        key-value pairs) into unified horizontal reading lines.
        """
        if not items:
            return []

        # Sort items top-to-bottom, then left-to-right
        sorted_items = sorted(
            items,
            key=lambda it: (it.bounding_box.y if it.bounding_box else 0, it.bounding_box.x if it.bounding_box else 0)
        )
        lines: List[List[OCRItem]] = []

        for it in sorted_items:
            if not it.bounding_box:
                lines.append([it])
                continue

            it_cy = it.bounding_box.y + it.bounding_box.height / 2.0
            placed = False
            for line in lines:
                valid_boxes = [m.bounding_box for m in line if m.bounding_box]
                if not valid_boxes:
                    continue
                line_cy = sum(b.y + b.height / 2.0 for b in valid_boxes) / len(valid_boxes)
                line_avg_h = sum(b.height for b in valid_boxes) / len(valid_boxes)
                # Allow horizontal clustering if centers are within 60% of average line height
                if abs(it_cy - line_cy) <= max(it.bounding_box.height, line_avg_h) * 0.6:
                    line.append(it)
                    placed = True
                    break
            if not placed:
                lines.append([it])

        merged_items: List[OCRItem] = []
        for line in lines:
            line_sorted = sorted(line, key=lambda it: it.bounding_box.x if it.bounding_box else 0)
            text = " ".join(it.text.strip() for it in line_sorted if it.text.strip())
            valid_boxes = [it.bounding_box for it in line_sorted if it.bounding_box]
            if valid_boxes:
                min_x = min(b.x for b in valid_boxes)
                min_y = min(b.y for b in valid_boxes)
                max_x = max(b.x + b.width for b in valid_boxes)
                max_y = max(b.y + b.height for b in valid_boxes)
                bbox = OCRBoundingBox(x=min_x, y=min_y, width=max(0, max_x - min_x), height=max(0, max_y - min_y))
            else:
                bbox = OCRBoundingBox(x=0, y=0, width=0, height=0)
            avg_conf = sum(it.confidence for it in line_sorted) / len(line_sorted)
            merged_items.append(OCRItem(
                text=text,
                confidence=avg_conf,
                bounding_box=bbox,
                page_or_region_id=line_sorted[0].page_or_region_id if line_sorted else None
            ))
        return merged_items

    def _generate_multiline_windows(self, lines: List[OCRItem], max_window: int = 5) -> List[OCRItem]:
        """
        Generates sliding window blocks of consecutive lines (2 to max_window lines)
        to capture multi-line entity names, addresses, and consumer care details.
        """
        windows: List[OCRItem] = []
        n = len(lines)
        for w in range(2, min(max_window + 1, n + 1)):
            for i in range(n - w + 1):
                window = lines[i:i + w]
                text = " ".join(it.text.strip() for it in window if it.text.strip())
                valid_boxes = [it.bounding_box for it in window if it.bounding_box]
                if valid_boxes:
                    min_x = min(b.x for b in valid_boxes)
                    min_y = min(b.y for b in valid_boxes)
                    max_x = max(b.x + b.width for b in valid_boxes)
                    max_y = max(b.y + b.height for b in valid_boxes)
                    bbox = OCRBoundingBox(x=min_x, y=min_y, width=max(0, max_x - min_x), height=max(0, max_y - min_y))
                else:
                    bbox = OCRBoundingBox(x=0, y=0, width=0, height=0)
                avg_conf = sum(it.confidence for it in window) / len(window)
                windows.append(OCRItem(
                    text=text,
                    confidence=avg_conf,
                    bounding_box=bbox,
                    page_or_region_id=window[0].page_or_region_id if window else None
                ))
        return windows

    def _extract_item_candidates(
        self,
        item: OCRItem,
        source_image_id: Optional[Union[int, str]],
        allowed_types: Optional[Set[DeclarationType]] = None,
    ) -> List[ExtractionCandidate]:
        """Matches patterns against an individual OCR item text, optionally filtered by declaration types."""
        matched_candidates: List[ExtractionCandidate] = []
        text = item.text.strip()
        if not text:
            return matched_candidates

        for pattern_def in self.patterns:
            if allowed_types is not None and pattern_def.declaration_type not in allowed_types:
                continue
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

        # Filter out candidates that are strict substrings/subsegments of another candidate
        # (e.g. phone number or email inside a full composite consumer care line,
        # or company name inside full company name + complete address)
        subsegment_indices = set()
        for i, c1 in enumerate(unique_candidates):
            for j, c2 in enumerate(unique_candidates):
                if i != j and c1.normalized_value and c2.normalized_value:
                    val1 = c1.normalized_value.lower().strip()
                    val2 = c2.normalized_value.lower().strip()
                    if val1 in val2 and len(val1) < len(val2):
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
