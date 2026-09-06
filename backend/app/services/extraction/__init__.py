"""
MetriGuard Declaration Extraction Subsystem.
Provides deterministic extraction of packaged commodity declarations from OCR output.
Strictly decoupled from legal metrology compliance decisions.
"""

from app.models.declaration_schemas import (
    DeclarationType,
    ExtractionStatus,
    ExtractionCandidate,
    ExtractedDeclaration,
    DeclarationExtractionResult,
)
from app.services.extraction.extractor import (
    DeclarationExtractor,
    extract_declarations,
    DEFAULT_CONFIDENCE_THRESHOLD,
)
from app.services.extraction.patterns import (
    EXTRACTION_PATTERNS,
    PatternDefinition,
    normalize_mrp,
    normalize_net_quantity,
    normalize_unit_sale_price,
    normalize_date,
    normalize_country,
    normalize_consumer_care,
    normalize_entity,
    normalize_commodity,
)

__all__ = [
    "DeclarationType",
    "ExtractionStatus",
    "ExtractionCandidate",
    "ExtractedDeclaration",
    "DeclarationExtractionResult",
    "DeclarationExtractor",
    "extract_declarations",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "EXTRACTION_PATTERNS",
    "PatternDefinition",
    "normalize_mrp",
    "normalize_net_quantity",
    "normalize_unit_sale_price",
    "normalize_date",
    "normalize_country",
    "normalize_consumer_care",
    "normalize_entity",
    "normalize_commodity",
]
