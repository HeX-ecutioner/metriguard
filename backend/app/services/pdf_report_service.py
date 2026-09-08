"""
PDF Report Generation Service for AlgoForge Prototype - MK I.

Generates audit-ready, deterministic PDF inspection reports from saved
database entities without re-running OCR or regulatory evaluation.
"""

import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)

from app.db.models import Inspection, InspectionStatus, PackageImage, Declaration, Violation
from app.services.storage import get_storage_service, StorageService

logger = logging.getLogger(__name__)

DECLARATION_LABELS: Dict[str, str] = {
    "MRP": "Maximum Retail Price (MRP)",
    "NET_QUANTITY": "Net Quantity",
    "MANUFACTURER": "Manufacturer Name & Address",
    "PACKER": "Packer Name & Address",
    "IMPORTER": "Importer Name & Address",
    "COUNTRY_OF_ORIGIN": "Country of Origin",
    "PACKING_DATE": "Date of Packing",
    "MANUFACTURE_DATE": "Date of Manufacture",
    "BEST_BEFORE": "Best Before Date",
    "USE_BY": "Use By / Expiry Date",
    "CONSUMER_CARE": "Consumer Care Details",
    "UNIT_SALE_PRICE": "Unit Sale Price (USP)",
    "COMMODITY_NAME": "Generic / Commodity Name",
}

STATUS_COLORS: Dict[str, colors.Color] = {
    "COMPLIANT": colors.HexColor("#10b981"),      # Emerald Green
    "NON_COMPLIANT": colors.HexColor("#ef4444"),  # Red
    "MANUAL_REVIEW": colors.HexColor("#f59e0b"),  # Amber
    "FAILED": colors.HexColor("#dc2626"),         # Dark Red
    "CREATED": colors.HexColor("#3b82f6"),        # Blue
    "PROCESSING": colors.HexColor("#8b5cf6"),     # Purple
}


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic total page count calculation and running headers/footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Top Header (Only from page 2 onwards, page 1 has main title banner)
        if self._pageNumber > 1:
            self.drawString(36, 810, "AlgoForge Prototype - MK I | Legal Metrology Compliance Inspection Report")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(36, 804, 559, 804)

        # Bottom Running Footer (All pages)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 42, 559, 42)

        self.drawString(36, 30, "AlgoForge Prototype - MK I  |  Automated Legal Metrology Screener  |  Not for Legal Certification")
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(559, 30, page_str)

        self.restoreState()


class PDFReportService:
    """
    Service responsible for building formal inspection PDF documents.
    """

    def __init__(self, storage_service: Optional[StorageService] = None):
        self.storage = storage_service or get_storage_service()

    def generate_report(self, inspection: Inspection) -> bytes:
        """
        Builds and returns the PDF report as bytes for a given completed inspection.
        """
        buffer = io.BytesIO()

        # Page setup: A4 with 0.5 inch margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=50,
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )
        section_title_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
        )
        bold_body = ParagraphStyle(
            "BoldBody",
            parent=body_style,
            fontName="Helvetica-Bold",
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#475569"),
        )

        story: List[Any] = []

        # =========================================================================
        # 1. Header Banner & Branding
        # =========================================================================
        status_val = inspection.status.value if hasattr(inspection.status, "value") else str(inspection.status)
        status_color = STATUS_COLORS.get(status_val, colors.HexColor("#64748b"))

        header_table_data = [
            [
                Paragraph("<b>AlgoForge Prototype - MK I</b>", title_style),
                Paragraph(
                    f"<font color='{status_color.hexval()}'><b>[{status_val.replace('_', ' ')}]</b></font>",
                    ParagraphStyle("StatusBadge", parent=title_style, alignment=2, fontSize=13)
                ),
            ],
            [
                Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011 - Automated Inspection Report", subtitle_style),
                Paragraph(f"<b>Inspection #{inspection.id}</b>", ParagraphStyle("InspID", parent=subtitle_style, alignment=2))
            ]
        ]
        header_table = Table(header_table_data, colWidths=[360, 163])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))

        # =========================================================================
        # 2. Executive Metadata Summary Grid
        # =========================================================================
        created_at_str = inspection.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if inspection.created_at else "N/A"
        report_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        conf_str = f"{(inspection.overall_confidence * 100):.1f}%" if inspection.overall_confidence is not None else "N/A"
        product_str = inspection.product_name or "N/A (Unspecified Commodity)"

        metadata_data = [
            [
                Paragraph("<b>Product / Commodity:</b>", bold_body),
                Paragraph(product_str, body_style),
                Paragraph("<b>Overall Confidence:</b>", bold_body),
                Paragraph(conf_str, body_style),
            ],
            [
                Paragraph("<b>Inspection Date:</b>", bold_body),
                Paragraph(created_at_str, body_style),
                Paragraph("<b>Report Generated:</b>", bold_body),
                Paragraph(report_timestamp, body_style),
            ],
            [
                Paragraph("<b>Inspection Status:</b>", bold_body),
                Paragraph(f"<b>{status_val}</b>", body_style),
                Paragraph("<b>Applicable Framework:</b>", bold_body),
                Paragraph("Legal Metrology Act, 2009 & LMR 2011", body_style),
            ],
        ]
        metadata_table = Table(metadata_data, colWidths=[120, 160, 115, 128])
        metadata_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 10))

        # =========================================================================
        # 3. Summary & Findings Callout
        # =========================================================================
        summary_text = (
            inspection.result.summary
            if inspection.result and inspection.result.summary
            else f"Inspection concluded with outcome '{status_val}'."
        )

        bg_summary = colors.HexColor("#f1f5f9")
        border_summary = colors.HexColor("#cbd5e1")
        if status_val == "COMPLIANT":
            bg_summary = colors.HexColor("#ecfdf5")
            border_summary = colors.HexColor("#10b981")
        elif status_val == "NON_COMPLIANT":
            bg_summary = colors.HexColor("#fef2f2")
            border_summary = colors.HexColor("#ef4444")
        elif status_val == "MANUAL_REVIEW":
            bg_summary = colors.HexColor("#fffbeb")
            border_summary = colors.HexColor("#f59e0b")
        elif status_val == "FAILED":
            bg_summary = colors.HexColor("#fef2f2")
            border_summary = colors.HexColor("#dc2626")

        summary_box = Table(
            [
                [
                    Paragraph(
                        f"<b>Executive Finding:</b> {summary_text}",
                        body_style
                    )
                ]
            ],
            colWidths=[523]
        )
        summary_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_summary),
            ("BOX", (0, 0), (-1, -1), 1, border_summary),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_box)
        story.append(Spacer(1, 10))

        # =========================================================================
        # 4. Embedded Original Image & Evidence Reference
        # =========================================================================
        story.append(Paragraph("<b>Uploaded Package Label & Visual Evidence</b>", section_title_style))

        package_img = inspection.images[0] if inspection.images else None
        image_flowable = self._create_image_flowable(package_img)

        if image_flowable:
            img_table = Table(
                [
                    [
                        image_flowable,
                        Paragraph(
                            f"<b>Image Metadata:</b><br/>"
                            f"• Filename: {package_img.original_filename if package_img else 'N/A'}<br/>"
                            f"• Dimensions: {package_img.width} × {package_img.height} px<br/>"
                            f"• File Size: {(package_img.file_size / 1024):.1f} KB<br/>"
                            f"• MIME Type: {package_img.mime_type if package_img else 'image/jpeg'}<br/><br/>"
                            f"<i>Visual evidence regions referenced in the regulatory tables correspond to pixel coordinate bounding boxes mapped to this image.</i>",
                            body_style
                        )
                    ]
                ],
                colWidths=[240, 283]
            )
            img_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(img_table)
        else:
            story.append(Paragraph("<i>No package image available in storage for this inspection session.</i>", body_style))

        story.append(Spacer(1, 10))

        # =========================================================================
        # 5. Regulatory Violations & Compliance Findings
        # =========================================================================
        violations_count = len(inspection.violations)
        story.append(Paragraph(f"<b>Regulatory Compliance Findings ({violations_count})</b>", section_title_style))

        if violations_count == 0:
            if status_val == "COMPLIANT":
                comp_box = Table(
                    [[
                        Paragraph(
                            "✓ <b>All mandatory Legal Metrology (Packaged Commodities) Rules, 2011 declarations are present and compliant.</b> "
                            "No statutory violations or irregularities were detected on the inspected label.",
                            ParagraphStyle("CompBox", parent=body_style, textColor=colors.HexColor("#065f46"))
                        )
                    ]],
                    colWidths=[523]
                )
                comp_box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d1fae5")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#10b981")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(comp_box)
            elif status_val == "FAILED":
                fail_box = Table(
                    [[
                        Paragraph(
                            "❌ <b>Inspection Processing Failure:</b> An internal pipeline processing failure occurred (e.g. storage or database error). "
                            "This status is distinct from a regulatory non-compliance finding.",
                            ParagraphStyle("FailBox", parent=body_style, textColor=colors.HexColor("#991b1b"))
                        )
                    ]],
                    colWidths=[523]
                )
                fail_box.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#ef4444")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(fail_box)
            else:
                story.append(Paragraph("<i>No specific rule violations detected.</i>", body_style))
        else:
            viol_headers = [
                Paragraph("<b>Rule ID / Ver</b>", bold_body),
                Paragraph("<b>Title & Violation Explanation</b>", bold_body),
                Paragraph("<b>Severity</b>", bold_body),
                Paragraph("<b>Confidence</b>", bold_body),
                Paragraph("<b>Evidence / Region</b>", bold_body),
            ]
            viol_rows = [viol_headers]

            for v in inspection.violations:
                rule_id_str = f"<b>{v.rule_id}</b><br/>v{v.rule_version}"
                title_expl_str = f"<b>{v.title}</b><br/>{v.explanation}"

                if v.expected_value or v.measured_value:
                    title_expl_str += f"<br/><i>Expected:</i> {v.expected_value or 'N/A'} | <i>Observed:</i> {v.measured_value or 'N/A'}"

                conf_val = f"{(v.confidence * 100):.0f}%" if v.confidence is not None else "N/A"
                sev_val = v.severity.value if hasattr(v.severity, "value") else str(v.severity)

                # Visual Evidence Region
                evidence_box = self._format_bbox(v.evidence_bounding_box)
                if not evidence_box:
                    evidence_box = "Declaration Absent / Not Visible"

                viol_rows.append([
                    Paragraph(rule_id_str, body_style),
                    Paragraph(title_expl_str, body_style),
                    Paragraph(f"<b>{sev_val}</b>", body_style),
                    Paragraph(conf_val, body_style),
                    Paragraph(evidence_box, body_style),
                ])

            viol_table = Table(viol_rows, colWidths=[105, 183, 55, 55, 125])
            viol_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(viol_table)

        story.append(Spacer(1, 10))

        # =========================================================================
        # 6. Extracted Statutory Declarations Table
        # =========================================================================
        decl_count = len(inspection.declarations)
        story.append(Paragraph(f"<b>Extracted Package Declarations ({decl_count})</b>", section_title_style))

        if decl_count == 0:
            story.append(Paragraph("<i>No declarations were detected or extracted from this image.</i>", body_style))
        else:
            decl_headers = [
                Paragraph("<b>Declaration Type</b>", bold_body),
                Paragraph("<b>Extracted Value</b>", bold_body),
                Paragraph("<b>Confidence</b>", bold_body),
                Paragraph("<b>Bounding Box Coordinate</b>", bold_body),
            ]
            decl_rows = [decl_headers]

            for d in inspection.declarations:
                decl_label = DECLARATION_LABELS.get(d.declaration_type, d.declaration_type.replace("_", " ").title())
                conf_val = f"{(d.confidence * 100):.0f}%" if d.confidence is not None else "N/A"
                bbox_str = self._format_bbox(d.bounding_box) or "N/A"

                decl_rows.append([
                    Paragraph(f"<b>{decl_label}</b>", body_style),
                    Paragraph(d.extracted_value or "<i>Missing / Not Detected</i>", body_style),
                    Paragraph(conf_val, body_style),
                    Paragraph(bbox_str, body_style),
                ])

            decl_table = Table(decl_rows, colWidths=[150, 203, 60, 110])
            decl_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(decl_table)

        story.append(Spacer(1, 14))

        # =========================================================================
        # 7. Statutory Disclaimer & Regulatory Notice
        # =========================================================================
        disclaimer_text = (
            "<b>STATUTORY PROTOTYPE DISCLAIMER:</b> This automated inspection report was generated by AlgoForge Prototype - MK I "
            "for screening compliance under the Legal Metrology Act, 2009 and the Legal Metrology (Packaged Commodities) Rules, 2011. "
            "This report is an AI-assisted screening assessment and does <b>NOT</b> constitute legal certification, statutory sanction, "
            "or final enforcement action. Any regulatory proceedings require independent physical verification and corroboration by an "
            "authorized Legal Metrology Inspector. 2D computer vision assessments cannot verify physical net weight/volume scale contents."
        )

        disclaimer_box = Table(
            [[Paragraph(disclaimer_text, disclaimer_style)]],
            colWidths=[523]
        )
        disclaimer_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(KeepTogether([disclaimer_box]))

        # Build document using NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()

    def _create_image_flowable(self, package_image: Optional[PackageImage]) -> Optional[RLImage]:
        """
        Creates a ReportLab Image flowable scaled proportionally within bounds.
        """
        if not package_image:
            return None

        file_bytes: Optional[bytes] = None
        # Try local filesystem path first
        local_path = self.storage.get_file_path(package_image.file_path)
        if local_path and Path(local_path).exists():
            try:
                with open(local_path, "rb") as f:
                    file_bytes = f.read()
            except Exception as e:
                logger.warning(f"Failed to read local image path {local_path}: {e}")

        if not file_bytes:
            return None

        try:
            pil_img = PILImage.open(io.BytesIO(file_bytes))
            orig_w, orig_h = pil_img.size

            # Target bounds: max width 230pt, max height 180pt
            max_w, max_h = 230.0, 180.0
            scale = min(max_w / orig_w, max_h / orig_h, 1.0)
            target_w = orig_w * scale
            target_h = orig_h * scale

            img_buf = io.BytesIO(file_bytes)
            return RLImage(img_buf, width=target_w, height=target_h)
        except Exception as e:
            logger.warning(f"Error preparing ReportLab image: {e}")
            return None

    def _format_bbox(self, bbox_raw: Optional[str]) -> Optional[str]:
        """
        Formats bounding box coordinates into a clean string.
        """
        if not bbox_raw:
            return None
        try:
            data = json.loads(bbox_raw)
            if isinstance(data, dict):
                x = data.get("x", "?")
                y = data.get("y", "?")
                w = data.get("width", "?")
                h = data.get("height", "?")
                return f"[{x}, {y}, {w}×{h}]"
            elif isinstance(data, list):
                return f"[{', '.join(str(v) for v in data)}]"
            return str(bbox_raw)
        except Exception:
            return str(bbox_raw)


_pdf_report_service: Optional[PDFReportService] = None


def get_pdf_report_service() -> PDFReportService:
    global _pdf_report_service
    if _pdf_report_service is None:
        _pdf_report_service = PDFReportService()
    return _pdf_report_service
