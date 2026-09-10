"""
Regex patterns, heuristic rules, and normalization utilities for Indian packaged
commodity declaration extraction from OCR text.
Covers all 13 declaration types under the Legal Metrology (Packaged Commodities) Rules, 2011.
"""

import re
from typing import NamedTuple, Callable, Optional, Tuple, List
from app.models.declaration_schemas import DeclarationType


class PatternDefinition(NamedTuple):
    name: str
    declaration_type: DeclarationType
    pattern: re.Pattern
    extractor_func: Callable[[re.Match], Tuple[str, Optional[str]]]
    confidence_weight: float = 1.0
    description: str = ""


# --- Normalization Utilities ---

def _clean_text(s: str) -> str:
    """Removes extra spaces, leading/trailing punctuation."""
    if not s:
        return ""
    # Strip leading/trailing colons, hyphens, equals, quotes, slashes, whitespace
    cleaned = re.sub(r"^[\s:=–\-\/]+|[\s:=–\-\/]+$", "", s).strip()
    # Normalize multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def normalize_mrp(raw: str) -> Optional[str]:
    """
    Normalizes MRP strings into canonical 'Rs. X.XX'.
    Handles:
      'Rs. 150/-', '₹ 249.50', '150.00', '150', 'Rs 150 (incl. of all taxes)'
    """
    if not raw:
        return None
    # Remove tax clauses
    cleaned = re.sub(r"(?i)\(?(?:incl(?:usive)?\s*(?:of)?\s*(?:all)?\s*taxes?)\)?", "", raw)
    # Remove trailing /- or /- only
    cleaned = re.sub(r"\/[-=.\s]*(?:only)?$", "", cleaned)
    # Extract numerical digits with optional decimal
    num_match = re.search(r"(\d+(?:[.,]\d{1,2})?)", cleaned)
    if not num_match:
        return None
    val_str = num_match.group(1).replace(",", ".")
    try:
        val = float(val_str)
        return f"Rs. {val:.2f}"
    except ValueError:
        return None


def normalize_net_quantity(raw: str) -> Optional[str]:
    """
    Normalizes Net Quantity into canonical quantity and unit.
    Handles:
      '500g', '500 G.', '500 gm', '0.5 kg', '1 L', '750 ml', '4 x 75g = 300g', '10 N'
    """
    if not raw:
        return None
    cleaned = _clean_text(raw)
    # Handle multipack format like "4 x 75g = 300g" or "4 x 75 g"
    multipack = re.search(
        r"(\d+)\s*[xX*]\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)(?:\s*=\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+))?",
        cleaned
    )
    if multipack:
        count, sub_val, sub_unit, total_val, total_unit = multipack.groups()
        sub_unit_norm = _normalize_unit(sub_unit)
        if total_val and total_unit:
            tot_unit_norm = _normalize_unit(total_unit)
            return f"{total_val} {tot_unit_norm} ({count} x {sub_val} {sub_unit_norm})"
        else:
            try:
                computed_tot = float(count) * float(sub_val)
                comp_str = f"{computed_tot:g}"
                return f"{comp_str} {sub_unit_norm} ({count} x {sub_val} {sub_unit_norm})"
            except ValueError:
                return f"{count} x {sub_val} {sub_unit_norm}"

    # Handle standard single quantity
    qty_match = re.search(
        r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+(?:\s*(?:net|contents))?)",
        cleaned
    )
    if qty_match:
        val, unit = qty_match.group(1), qty_match.group(2)
        norm_u = _normalize_unit(unit)
        return f"{val} {norm_u}"

    return cleaned


def _normalize_unit(unit_str: str) -> str:
    """Standardizes metric units."""
    u = unit_str.strip().lower().rstrip(".")
    # Mass
    if u in ("g", "gm", "gms", "gram", "grams"):
        return "g"
    if u in ("kg", "kgs", "kilogram", "kilograms"):
        return "kg"
    if u in ("mg", "mgs", "milligram", "milligrams"):
        return "mg"
    # Volume
    if u in ("ml", "mls", "millilitre", "millilitres", "milliliter", "milliliters"):
        return "ml"
    if u in ("l", "ltr", "ltrs", "litre", "litres", "liter", "liters"):
        return "L"
    # Count / Units
    if u in ("n", "u", "units", "unit", "nos", "pcs", "pieces", "piece", "tablets", "capsules"):
        return "units"
    # Length
    if u in ("m", "meter", "meters", "metre", "metres"):
        return "m"
    if u in ("cm", "centimeter", "centimeters"):
        return "cm"
    return unit_str.strip()


def normalize_unit_sale_price(raw: str) -> Optional[str]:
    """
    Normalizes Unit Sale Price into 'Rs. X.XX / unit'.
    Handles:
      'Rs. 0.30 / g', '₹ 1.50 per unit', '0.25/g', 'Rs 200 / kg'
    """
    if not raw:
        return None
    cleaned = _clean_text(raw)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\/|per)\s*(\d*\s*[a-zA-Z]+)", cleaned, re.IGNORECASE)
    if match:
        rate = match.group(1)
        unit = match.group(2).strip()
        try:
            rate_val = float(rate)
            return f"Rs. {rate_val:.2f} / {_normalize_unit(unit)}"
        except ValueError:
            return f"Rs. {rate} / {_normalize_unit(unit)}"
    return cleaned


def normalize_date(raw: str) -> Optional[str]:
    """
    Normalizes dates into canonical representations.
    Handles:
      '15/10/2025', '15-10-2025', '10/2025', '15.10.25', 'Oct 2025',
      '12 months from packaging', '6 MONTHS FROM MFG'
    """
    if not raw:
        return None
    cleaned = _clean_text(raw)

    # Check relative duration (e.g. "12 months from mfg", "6 months of packaging")
    rel_match = re.search(
        r"(\d+)\s*(months?|days?|years?)\s*(?:from|of)\s*(?:date\s*of\s*)?([a-zA-Z\s]+)",
        cleaned,
        re.IGNORECASE
    )
    if rel_match:
        qty, unit, base = rel_match.group(1), rel_match.group(2).lower(), rel_match.group(3).strip()
        base_clean = re.sub(r"(?i)\b(mfg|mfd|manufacture|manufacturing)\b", "mfg", base)
        base_clean = re.sub(r"(?i)\b(pkd|pack|packed|packaging|packing)\b", "packing", base_clean)
        return f"{qty} {unit} from {base_clean.strip()}"

    # Check full date DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    dmy_match = re.search(r"\b(0?[1-9]|[12]\d|3[01])[/\-\.](0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})\b", cleaned)
    if dmy_match:
        d, m, y = dmy_match.group(1).zfill(2), dmy_match.group(2).zfill(2), dmy_match.group(3)
        if len(y) == 2:
            y = f"20{y}"
        return f"{d}/{m}/{y}"

    # Check MM/YYYY
    my_match = re.search(r"\b(0?[1-9]|1[0-2])[/\-\.](20\d{2}|\d{2})\b", cleaned)
    if my_match:
        m, y = my_match.group(1).zfill(2), my_match.group(2)
        if len(y) == 2:
            y = f"20{y}"
        return f"{m}/{y}"

    # Check Month name + Year (e.g. 'Oct 2025', 'October 2025', '15 Oct 2025')
    text_date_match = re.search(
        r"\b(?:(0?[1-9]|[12]\d|3[01])\s+)?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(20\d{2}|\d{2})\b",
        cleaned,
        re.IGNORECASE
    )
    if text_date_match:
        day = text_date_match.group(1)
        month = text_date_match.group(2)[:3].capitalize()
        year = text_date_match.group(3)
        if len(year) == 2:
            year = f"20{year}"
        if day:
            return f"{day.zfill(2)} {month} {year}"
        return f"{month} {year}"

    return cleaned


def normalize_country(raw: str) -> Optional[str]:
    """Normalizes country name string to title case."""
    if not raw:
        return None
    cleaned = _clean_text(raw)
    # Strip common prefixes
    cleaned = re.sub(r"(?i)^(?:country\s*of\s*origin|made\s*in|product\s*of|origin)\s*[:=\-]?\s*", "", cleaned)
    cleaned = cleaned.strip(" .,-")
    return cleaned.title() if cleaned else None


def normalize_consumer_care(raw: str) -> Optional[str]:
    """Cleans consumer care phone numbers, emails, or address details."""
    if not raw:
        return None
    cleaned = _clean_text(raw)
    # Strip common leading label
    cleaned = re.sub(
        r"(?i)^(?:for\s*)?(?:consumer|customer)\s*(?:care|service|cell|complaints|queries|feedback)?\s*(?:details|cell|helpline)?\s*[:=\-]?\s*",
        "",
        cleaned
    )
    cleaned = cleaned.strip()
    # Strip leading cell / address artifact prefixes e.g. "cell at the address - " or "cell at the "
    cleaned = re.sub(r"(?i)^(?:cell\s+(?:at\s+(?:the\s+)?)?)?(?:address\s*[:=\-]\s*)?", "", cleaned).strip(" ,.-")
    # Filter out non-contact fragments that don't convey contact information
    if cleaned.lower() in ("cell at the", "cell", "at the", "details", "contact", "helpline", "care", "customer care"):
        return None
    if len(cleaned) < 4:
        return None
    return cleaned


def normalize_entity(raw: str) -> Optional[str]:
    """Cleans entity name / address."""
    if not raw:
        return None
    cleaned = _clean_text(raw)
    # Strip label prefix
    cleaned = re.sub(
        r"(?i)^(?:manufactured\s*(?:\/|\&|and)?\s*(?:licensed\s*(?:\/|\&|and)?\s*)?marketed\s*by|manufactured\s*for\s*(?:\/|\&|and)?\s*marketed\s*by|mfd\.?\s*(?:\/|\&|and)?\s*mktd\.?\s*by|mfd\.?\s*by|manufactured\s*by|mfg\.?\s*by|marketed\s*by|packed\s*by|pkd\.?\s*by|re-?packed\s*by|imported\s*by|imp\.?\s*by|produced\s*by)\s*[:=\-]?\s*",
        "",
        cleaned
    )
    return cleaned.strip(" ,.-")


def normalize_commodity(raw: str) -> Optional[str]:
    """Cleans commodity name."""
    if not raw:
        return None
    cleaned = _clean_text(raw)
    cleaned = re.sub(r"(?i)^(?:commodity(?:\s*name)?|name\s*of\s*commodity|generic\s*name|product(?:\s*name)?|item(?:\s*name)?)\s*[:=\-]?\s*", "", cleaned)
    return cleaned.strip(" ,.-").title()


# --- Pattern Definitions for all 13 Declaration Types ---

EXTRACTION_PATTERNS: List[PatternDefinition] = [

    # 1. MRP (Maximum Retail Price)
    # Standard: MRP Rs. 150 / M.R.P. 150 / MRP: ₹ 249.50 / MRP = 150
    PatternDefinition(
        name="mrp_standard",
        declaration_type=DeclarationType.MRP,
        pattern=re.compile(
            r"(?i)\b(?:M\.?R\.?P\.?|MR\s*P|MAX(?:IMUM)?\s*RETAIL\s*PRICE)\b[^0-9\n\r]*(?:(?:Rs\.?|RS\.?|INR|₹|R)\s*)?([0-9]+(?:[.,][0-9]{1,2})?(?:\s*\/\s*[-=.\s]*(?:only)?)?)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_mrp(m.group(1))),
        confidence_weight=1.0,
        description="Standard MRP declaration format"
    ),
    # MRP typo: M.B.P. / NRP / M.A.P.
    PatternDefinition(
        name="mrp_typo_mbp",
        declaration_type=DeclarationType.MRP,
        pattern=re.compile(
            r"(?i)\b(?:M\.?B\.?P\.?|NRP|M\.?A\.?P\.?)\b[^0-9\n\r]*(?:(?:Rs\.?|RS\.?|INR|₹|R)\s*)?([0-9]+(?:[.,][0-9]{1,2})?(?:\s*\/\s*[-=.\s]*(?:only)?)?)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_mrp(m.group(1))),
        confidence_weight=0.88,
        description="MRP with OCR letter confusion (MBP, NRP, MAP)"
    ),
    # MRP with inline tax clause: MRP Rs. 150 (incl. of all taxes)
    PatternDefinition(
        name="mrp_with_taxes",
        declaration_type=DeclarationType.MRP,
        pattern=re.compile(
            r"(?i)\b(?:M\.?R\.?P\.?|MAX(?:IMUM)?\s*RETAIL\s*PRICE)[^0-9\n\r]*([0-9]+(?:[.,][0-9]{1,2})?)[^a-z0-9\n\r]*\(?(?:incl(?:usive)?\s*(?:of)?\s*(?:all)?\s*taxes?)\)?",
        ),
        extractor_func=lambda m: (m.group(1), normalize_mrp(m.group(1))),
        confidence_weight=0.98,
        description="MRP with inclusive of all taxes clause"
    ),

    # 2. NET_QUANTITY
    # Multipack: 4 x 75g = 300g or 4 x 75 g
    PatternDefinition(
        name="net_qty_multipack",
        declaration_type=DeclarationType.NET_QUANTITY,
        pattern=re.compile(
            r"(?i)(?:(?:NET\s*(?:QTY|QUANTITY|WT|WEIGHT|CONTENTS?)|N\.?\s*QTY|Nel\s*Wt|Net\s*Wl|Net\s*W1)\s*[:=–\-]?\s*)?([0-9]+\s*[xX*]\s*[0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|kg|kgs|ml|l|ltr|pcs|units)(?:\s*=\s*[0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|kg|kgs|ml|l|ltr))?)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_net_quantity(m.group(1))),
        confidence_weight=1.0,
        description="Multipack net quantity (e.g. 4 x 75g = 300g)"
    ),
    # Standard: Net Wt: 500g, NET QTY: 1 L, Net Quantity - 500 G.
    PatternDefinition(
        name="net_qty_standard",
        declaration_type=DeclarationType.NET_QUANTITY,
        pattern=re.compile(
            r"(?i)\b(?:NET\s*(?:QUANTITY|QTY|WT|WEIGHT|VOLUME|VOL|CONTENTS?)|N\.?\s*QTY)\s*[:=–\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|gram|grams|kg|kgs|kilogram|kilograms|mg|ml|mls|millilitre|millilitres|milliliter|l|ltr|ltrs|litre|litres|liter|units|unit|nos|pcs|pieces|piece|tablets|capsules|N|U)\b\.?)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_net_quantity(m.group(1))),
        confidence_weight=1.0,
        description="Standard Net Quantity declaration"
    ),
    # Net quantity OCR typos: Nel Wt, Net Wl, Net W1, Nef Wt
    PatternDefinition(
        name="net_qty_ocr_typos",
        declaration_type=DeclarationType.NET_QUANTITY,
        pattern=re.compile(
            r"(?i)\b(?:Nel\s*Wt|Net\s*Wl|Net\s*W1|Nef\s*Wt|Nel\s*Quantity|Net\s*Quantily)\s*[:=–\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:g|gm|gms|kg|kgs|mg|ml|l|ltr|pcs|units|N)\b\.?)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_net_quantity(m.group(1))),
        confidence_weight=0.88,
        description="Net Quantity with OCR typos (Nel Wt, Net Wl, etc.)"
    ),

    # 3. UNIT_SALE_PRICE
    # USP: Rs. 0.30 / g, Unit Sale Price: Rs. 200/kg, ₹ 1.50 per unit
    PatternDefinition(
        name="usp_standard",
        declaration_type=DeclarationType.UNIT_SALE_PRICE,
        pattern=re.compile(
            r"(?i)\b(?:UNIT\s*SALE\s*PRICE|U\.?S\.?P\.?)\s*[:=–\-]?\s*(?:(?:Rs\.?|RS\.?|INR|₹)\s*)?([0-9]+(?:\.[0-9]+)?\s*(?:\/|per)\s*(?:100\s*)?(?:g|gm|gms|kg|kgs|ml|l|ltr|unit|units|piece|pcs|N|m|cm)\b\.?)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_unit_sale_price(m.group(1))),
        confidence_weight=1.0,
        description="Standard Unit Sale Price declaration"
    ),

    # 4. MANUFACTURE_DATE
    # Mfg Date: 15/10/2025, MFD: 10/2025, Date of Mfg: Oct 2025, Month & Year of Manufacture: Feb 2022
    PatternDefinition(
        name="mfg_date_standard",
        declaration_type=DeclarationType.MANUFACTURE_DATE,
        pattern=re.compile(
            r"(?i)\b(?:(?:MONTH\s*(?:&|AND|\/)?\s*YEAR\s*OF\s*)?(?:MFG\.?\s*DATE|MFD\.?\s*DATE|DATE\s*OF\s*MFG\.?|DATE\s*OF\s*MANUFACTURE|MANUFACTURE(?:D)?\s*(?:ON|DATE)?|MFD\.?|MFG\.?|MANUFACTURE)|MONTH\s*(?:&|AND|\/)?\s*YEAR\s*(?:OF\s*)?(?:MANUFACTURE|MFG|MFD))\s*[:=–\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}[/\-\.][0-9]{2,4}|(?:(?:0?[1-9]|[12]\d|3[01])\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(?:20[0-9]{2}|[0-9]{2}))",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=1.0,
        description="Standard Date of Manufacture"
    ),
    # Mfg Date OCR typos: Mfq Date, Mfd Dle, Mfg Dte, Mld Date
    PatternDefinition(
        name="mfg_date_ocr_typo",
        declaration_type=DeclarationType.MANUFACTURE_DATE,
        pattern=re.compile(
            r"(?i)\b(?:Mfq\s*Date|Mfd\s*Dle|Mfg\.?\s*Dte|Mld\s*Date|Mfq\s*Dte)\s*[:=–\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}[/\-\.][0-9]{2,4}|(?:(?:0?[1-9]|[12]\d|3[01])\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(?:20[0-9]{2}|[0-9]{2}))",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=0.88,
        description="Date of Manufacture with OCR typos (Mfq Date, etc.)"
    ),

    # 5. PACKING_DATE
    # Pkd: 15/10/2025, Packed on: 10/2025, Date of Packing: Oct 2025, Month & Year of Packing: Feb 2022
    PatternDefinition(
        name="pkd_date_standard",
        declaration_type=DeclarationType.PACKING_DATE,
        pattern=re.compile(
            r"(?i)\b(?:(?:MONTH\s*(?:&|AND|\/)?\s*YEAR\s*OF\s*)?(?:PKD\.?\s*DATE|PACKING\s*DATE|DATE\s*OF\s*PACKING|DATE\s*OF\s*PRE-?PACKING|PACKED\s*(?:ON|DATE)?|PKD\.?|PACKING|PRE-?PACKING)|MONTH\s*(?:&|AND|\/)?\s*YEAR\s*(?:OF\s*)?(?:PACKING|PKD|PRE-?PACKING))\s*[:=–\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}[/\-\.][0-9]{2,4}|(?:(?:0?[1-9]|[12]\d|3[01])\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(?:20[0-9]{2}|[0-9]{2}))",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=1.0,
        description="Standard Date of Packing"
    ),
    # Packing Date OCR typos: Packd on, Pka Date, Pkd Dte
    PatternDefinition(
        name="pkd_date_ocr_typo",
        declaration_type=DeclarationType.PACKING_DATE,
        pattern=re.compile(
            r"(?i)\b(?:Packd\s*on|Pka\s*Date|Pkd\s*Dte|Pakd\s*Date)\s*[:=–\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}[/\-\.][0-9]{2,4}|(?:(?:0?[1-9]|[12]\d|3[01])\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(?:20[0-9]{2}|[0-9]{2}))",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=0.88,
        description="Date of Packing with OCR typos"
    ),

    # 6. BEST_BEFORE
    # Relative: Best before 12 months from manufacture / Best before 6 months from pkd
    PatternDefinition(
        name="best_before_relative",
        declaration_type=DeclarationType.BEST_BEFORE,
        pattern=re.compile(
            r"(?i)\b(?:BEST\s*BEFORE|BEST\s*BY|B\.?\s*BEFORE)\s*[:=–\-]?\s*([0-9]+\s*(?:months?|days?|years?)\s*(?:from|of)\s*(?:date\s*of\s*)?(?:mfg|mfd|manufacture|pkd|packing|packaging)[^.\n\r,]*)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=1.0,
        description="Best Before with relative duration"
    ),
    # Explicit date: Best Before: 15/10/2026, Best By: Oct 2026
    PatternDefinition(
        name="best_before_date",
        declaration_type=DeclarationType.BEST_BEFORE,
        pattern=re.compile(
            r"(?i)\b(?:BEST\s*BEFORE|BEST\s*BY|BB\s*[:=–\-])\s*[:=–\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}[/\-\.][0-9]{2,4}|(?:(?:0?[1-9]|[12]\d|3[01])\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(?:20[0-9]{2}|[0-9]{2}))",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=0.98,
        description="Best Before with specific date"
    ),

    # 7. USE_BY
    # Use By: 15/10/2026, Expiry Date: 10/2026, EXP: 15.10.26
    PatternDefinition(
        name="use_by_standard",
        declaration_type=DeclarationType.USE_BY,
        pattern=re.compile(
            r"(?i)\b(?:USE\s*BY|EXPIRY\s*DATE|EXP\.?\s*DATE|EXPIRY|EXP\.?|EXPIRES\s*(?:ON)?)\s*[:=–\-]?\s*([0-9]{1,2}[/\-\.][0-9]{1,2}[/\-\.][0-9]{2,4}|[0-9]{1,2}[/\-\.][0-9]{2,4}|(?:(?:0?[1-9]|[12]\d|3[01])\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[,\s]+(?:20[0-9]{2}|[0-9]{2}))",
        ),
        extractor_func=lambda m: (m.group(1), normalize_date(m.group(1))),
        confidence_weight=1.0,
        description="Use By / Expiry Date declaration"
    ),

    # 8. COUNTRY_OF_ORIGIN
    # Country of Origin: India, Made in India, Product of USA
    PatternDefinition(
        name="country_origin_standard",
        declaration_type=DeclarationType.COUNTRY_OF_ORIGIN,
        pattern=re.compile(
            r"(?i)\b(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF|PRODUCE\s*OF|ORIGIN)\s*[:=–\-]?\s*(India|Bharat|China|USA|United States(?: of America)?|UK|United Kingdom|Japan|Germany|Bangladesh|Thailand|Vietnam|Korea|Italy|France|Taiwan|Malaysia|Indonesia|Sri Lanka|Nepal|[a-zA-Z]{3,20}\b)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_country(m.group(1))),
        confidence_weight=1.0,
        description="Country of Origin declaration"
    ),

    # 9. MANUFACTURER
    # Mfd. by: ABC Foods Pvt Ltd, Plot 10, Industrial Area, Mumbai
    PatternDefinition(
        name="manufacturer_standard",
        declaration_type=DeclarationType.MANUFACTURER,
        pattern=re.compile(
            r"(?i)\b(?:MANUFACTURED\s*(?:\/|\&|AND)?\s*(?:LICENSED\s*(?:\/|\&|AND)?\s*)?MARKETED\s*BY|MANUFACTURED\s*FOR\s*(?:\/|\&|AND)?\s*MARKETED\s*BY|MFD\.?\s*(?:\/|\&|AND)?\s*MKTD\.?\s*BY|MFD\.?\s*BY|MANUFACTURED\s*BY|MFG\.?\s*BY|PRODUCED\s*BY|MARKETED\s*BY)\s*[:=–\-]?\s*([^\n\r]+?)(?=(?:\b(?:PKD|PACKED|IMPORTED|MRP|NET|BATCH|EXP|BB|BEST|FOR\s*CUSTOMER|FOR\s*FEEDBACK)\b)|$)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_entity(m.group(1))),
        confidence_weight=1.0,
        description="Manufacturer name and address"
    ),
    # Manufacturer OCR typos: Mfq by, Mld by, Manufacturd by
    PatternDefinition(
        name="manufacturer_ocr_typo",
        declaration_type=DeclarationType.MANUFACTURER,
        pattern=re.compile(
            r"(?i)\b(?:Mfq\s*by|Mld\s*by|Manufacturd\s*by)\s*[:=–\-]?\s*([^\n\r]+?)(?=(?:\b(?:PKD|PACKED|IMPORTED|MRP|NET|BATCH|EXP)\b)|$)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_entity(m.group(1))),
        confidence_weight=0.88,
        description="Manufacturer declaration with OCR typos"
    ),

    # 10. PACKER
    # Packed by: XYZ Logistics Ltd, Warehouse 5, Delhi
    PatternDefinition(
        name="packer_standard",
        declaration_type=DeclarationType.PACKER,
        pattern=re.compile(
            r"(?i)\b(?:PACKED\s*BY|PKD\.?\s*BY|RE-?PACKED\s*BY|PACKAGED\s*BY)\s*[:=–\-]?\s*([^\n\r]+?)(?=(?:\b(?:MFD|MANUFACTURED|IMPORTED|MRP|NET|BATCH|EXP|BB|BEST)\b)|$)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_entity(m.group(1))),
        confidence_weight=1.0,
        description="Packer name and address"
    ),

    # 11. IMPORTER
    # Imported by: Global Goods India Pvt Ltd, Nariman Point, Mumbai
    PatternDefinition(
        name="importer_standard",
        declaration_type=DeclarationType.IMPORTER,
        pattern=re.compile(
            r"(?i)\b(?:IMPORTED\s*BY|IMP\.?\s*BY|IMPORTED\s*(?:&|AND)\s*DISTRIBUTED\s*BY)\s*[:=–\-]?\s*([^\n\r]+?)(?=(?:\b(?:MFD|MANUFACTURED|PACKED|MRP|NET|BATCH|EXP)\b)|$)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_entity(m.group(1))),
        confidence_weight=1.0,
        description="Importer name and address"
    ),

    # 12. CONSUMER_CARE
    # Customer Care: 1800-123-4567, care@company.com
    PatternDefinition(
        name="consumer_care_contact",
        declaration_type=DeclarationType.CONSUMER_CARE,
        pattern=re.compile(
            r"(?i)\b(?:CONSUMER\s*CARE|CUSTOMER\s*CARE|CUSTOMER\s*SERVICE|HELPLINE|TOLL\s*FREE|CARE\s*CELL|FOR\s*(?:QUERIES|FEEDBACK|COMPLAINTS))\s*[:=–\-]?\s*([^\n\r]+)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_consumer_care(m.group(1))),
        confidence_weight=1.0,
        description="Consumer care details (phone, email, contact address)"
    ),
    # Standalone toll free / helpline phone number
    PatternDefinition(
        name="consumer_care_phone",
        declaration_type=DeclarationType.CONSUMER_CARE,
        pattern=re.compile(
            r"(?i)\b(?:(?:Toll\s*Free|Helpline|Call|Phone|Tel|Mobile|Customer\s*Care|Care\s*Cell|Contact)\s*[:=–\-]?\s*(1800[-\s]?[0-9]{3}[-\s]?[0-9]{3,4}|\+?91[-\s]?[0-9]{10}|0[0-9]{2,4}[-\s]?[0-9]{6,8})|(1800[-\s]?[0-9]{3}[-\s]?[0-9]{3,4}))\b",
        ),
        extractor_func=lambda m: (m.group(1) or m.group(2), (m.group(1) or m.group(2)).strip()),
        confidence_weight=0.95,
        description="Consumer care helpline phone number"
    ),
    # Standalone consumer care email
    PatternDefinition(
        name="consumer_care_email",
        declaration_type=DeclarationType.CONSUMER_CARE,
        pattern=re.compile(
            r"(?i)(?:(?:Email|Mail|E-mail)\s*[:=–\-]?\s*)?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b",
        ),
        extractor_func=lambda m: (m.group(1), m.group(1).strip().lower()),
        confidence_weight=0.95,
        description="Consumer care email address"
    ),

    # 13. COMMODITY_NAME
    # Commodity: Refined Sunflower Oil / Generic Name: Biscuits / Product: Atta
    PatternDefinition(
        name="commodity_name_labeled",
        declaration_type=DeclarationType.COMMODITY_NAME,
        pattern=re.compile(
            r"(?i)\b(?:COMMODITY(?:\s*NAME)?|NAME\s*OF\s*COMMODITY|GENERIC\s*NAME|PRODUCT(?:\s*NAME)?|ITEM(?:\s*NAME)?)\s*[:=–\-]?\s*([a-zA-Z0-9\s/&'-]{3,60}?)(?=[,;\n\r]|\s+(?:MFD|PKD|NET|MRP|BATCH|EXP)|\s*$)",
        ),
        extractor_func=lambda m: (m.group(1), normalize_commodity(m.group(1))),
        confidence_weight=1.0,
        description="Labeled Commodity / Generic product name"
    ),
]
