"""
Professional PDF Report Generator (English)
"""
import io
import datetime
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak,
)

from .models import MetadataResult
from .formatters import dedup_entries, humanize_value
from .editor import compute_privacy_score


# ---------- Styles ----------

def _make_styles():
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontName="Helvetica-Bold", fontSize=22, leading=28,
            textColor=colors.HexColor("#0e2a44"),
            alignment=TA_CENTER, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontName="Helvetica", fontSize=10, leading=14,
            textColor=colors.HexColor("#666"),
            alignment=TA_CENTER, spaceAfter=20,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=14, leading=20,
            textColor=colors.HexColor("#1e40af"),
            alignment=TA_LEFT, spaceBefore=14, spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontName="Helvetica", fontSize=10, leading=14,
            textColor=colors.black, alignment=TA_LEFT,
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Normal"],
            fontName="Courier", fontSize=8, leading=11,
            textColor=colors.HexColor("#333"), alignment=TA_LEFT,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontName="Helvetica-Oblique", fontSize=8, leading=12,
            textColor=colors.HexColor("#888"), alignment=TA_CENTER,
        ),
        "score_big": ParagraphStyle(
            "score_big", parent=base["Normal"],
            fontName="Helvetica-Bold", fontSize=18, leading=24,
            alignment=TA_CENTER, spaceAfter=8,
        ),
    }


# ---------- Main ----------

def generate_pdf_report(
    result: MetadataResult,
    geo_info: Optional[dict] = None,
    include_full_table: bool = True,
    max_tags: int = 200,
) -> bytes:
    """
    Build a professional PDF report and return as bytes.
    """
    styles = _make_styles()
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Alborz Report - {result.filename}",
        author="Alborz",
        subject="Metadata Report",
    )

    story = []
    deduped = dedup_entries(result.entries)
    privacy = compute_privacy_score(deduped)

    # ---------- Header ----------
    story.append(Paragraph("Alborz Report", styles["title"]))
    story.append(Paragraph(
        f"File: <b>{_escape(result.filename)}</b> &nbsp;|&nbsp; "
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["subtitle"],
    ))

    # ---------- File Information ----------
    story.append(Paragraph("File Information", styles["h2"]))

    file_rows = [
        ["Field", "Value"],
        ["Filename", _escape(result.filename)],
        ["Size", f"{result.filesize:,} bytes"],
        ["MIME Type", result.mime_type],
        ["MD5", result.file_hash_md5],
        ["SHA256", result.file_hash_sha256],
    ]

    file_table = Table(file_rows, colWidths=[40 * mm, 120 * mm])
    file_table.setStyle(_table_style())
    story.append(file_table)

    # ---------- Privacy Score ----------
    story.append(Paragraph("Privacy Score", styles["h2"]))

    privacy_color = {
        "safe":   colors.HexColor("#16a34a"),
        "medium": colors.HexColor("#ca8a04"),
        "danger": colors.HexColor("#dc2626"),
    }.get(privacy["level"], colors.gray)

    level_en = {
        "safe": "SAFE",
        "medium": "MEDIUM RISK",
        "danger": "HIGH RISK",
    }.get(privacy["level"], privacy["level"].upper())

    score_style = styles["score_big"].clone("score_dyn")
    score_style.textColor = privacy_color

    story.append(Paragraph(
        f"{level_en} &mdash; {privacy['score']} / 100",
        score_style,
    ))

    if privacy["risks"]:
        risk_rows = [["Level", "Risk"]]
        for r in privacy["risks"]:
            lvl = "HIGH" if r["level"] == "high" else "MEDIUM"
            risk_rows.append([
                lvl,
                f"{_escape(r['label'])}: {_escape(r['detail'])}",
            ])
        risk_table = Table(risk_rows, colWidths=[20 * mm, 140 * mm])
        risk_table.setStyle(_table_style())
        story.append(risk_table)
    else:
        story.append(Paragraph("No specific privacy risks found.",
                                styles["body"]))

    # ---------- Summary ----------
    summary = _build_summary_for_pdf(deduped)
    if summary:
        story.append(Paragraph("Key Metadata Summary", styles["h2"]))
        summary_rows = [["Field", "Value"]]
        for label, value in summary:
            summary_rows.append([_escape(label), _escape(value)])

        sum_table = Table(summary_rows, colWidths=[50 * mm, 110 * mm])
        sum_table.setStyle(_table_style())
        story.append(sum_table)

    # ---------- GPS ----------
    if geo_info and geo_info.get("lat") is not None:
        story.append(Paragraph("GPS Location", styles["h2"]))
        lat = geo_info["lat"]
        lon = geo_info["lon"]

        gps_rows = [
            ["Field", "Value"],
            ["Latitude",  f"{lat:.6f}"],
            ["Longitude", f"{lon:.6f}"],
        ]
        if geo_info.get("alt") is not None:
            gps_rows.append(["Altitude", f"{geo_info['alt']:.1f} m"])
        if geo_info.get("city"):
            gps_rows.append(["City", _escape(geo_info["city"])])
        if geo_info.get("country"):
            gps_rows.append(["Country", _escape(geo_info["country"])])
        if geo_info.get("place"):
            gps_rows.append(["Full Address", _escape(geo_info["place"])])

        gps_table = Table(gps_rows, colWidths=[40 * mm, 120 * mm])
        gps_table.setStyle(_table_style())
        story.append(gps_table)

        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            f'<link href="https://www.openstreetmap.org/?mlat={lat}&mlon={lon}'
            f'#map=14/{lat}/{lon}">'
            f'View on OpenStreetMap &rarr;</link>',
            styles["body"],
        ))

    # ---------- Full Tag Table ----------
    if include_full_table:
        story.append(PageBreak())
        story.append(Paragraph("Complete Metadata Tags", styles["h2"]))

        rows = [["Group", "Tag", "Value"]]
        for e in deduped[:max_tags]:
            v = str(humanize_value(e.tag, e.value))
            if len(v) > 90:
                v = v[:87] + "..."
            rows.append([
                Paragraph(_escape(e.group), styles["mono"]),
                Paragraph(_escape(e.tag), styles["mono"]),
                Paragraph(_escape(v), styles["mono"]),
            ])

        full_table = Table(
            rows,
            colWidths=[25 * mm, 55 * mm, 80 * mm],
            repeatRows=1,
        )
        full_table.setStyle(_table_style(font_size=8))
        story.append(full_table)

        if len(deduped) > max_tags:
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(
                f"... and {len(deduped) - max_tags} more tags not shown "
                f"(limit: {max_tags}).",
                styles["body"],
            ))

    # ---------- Footer ----------
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "Generated by Alborz &mdash; Free &amp; open-source metadata toolkit",
        styles["footer"],
    ))

    doc.build(story, onFirstPage=_draw_page_footer, onLaterPages=_draw_page_footer)
    return buffer.getvalue()


# ---------- Helpers ----------

def _escape(text) -> str:
    """Escape HTML special chars"""
    s = str(text)
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def _table_style(font_size: int = 10):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), font_size),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f1f5f9")]),
    ])


def _draw_page_footer(canvas, doc):
    """Page number footer"""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888"))
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.drawCentredString(A4[0] / 2, 10 * mm, text)
    canvas.restoreState()


# ---------- English summary tags ----------

SUMMARY_TAGS_EN = {
    "Camera Model":     ["Model"],
    "Manufacturer":     ["Make"],
    "Software":         ["Software"],
    "Lens":             ["LensModel", "Lens"],
    "Capture Time":     ["DateTimeOriginal", "DateTimeDigitized"],
    "Last Modified":    ["DateTime"],
    "ISO":              ["ISOSpeedRatings", "PhotographicSensitivity"],
    "Aperture":         ["FNumber", "ApertureValue"],
    "Shutter Speed":    ["ExposureTime", "ShutterSpeedValue"],
    "Focal Length":     ["FocalLength"],
    "Flash":            ["Flash"],
    "Exposure Mode":    ["ExposureProgram", "ExposureMode"],
    "Resolution":       ["ExifImageWidth", "ImageWidth"],
    "Latitude":         ["DecimalLatitude"],
    "Longitude":        ["DecimalLongitude"],
    "Altitude":         ["GPSAltitude"],
}


def _build_summary_for_pdf(entries):
    """Build key summary (English labels) for PDF"""
    rows = []
    for label, tags in SUMMARY_TAGS_EN.items():
        for tag in tags:
            found = next((e for e in entries if e.tag.lower() == tag.lower()), None)
            if found and str(found.value).strip() not in ("", "None"):
                v = str(humanize_value(tag, found.value)).strip()
                # Translate humanize_value Persian output to plain numbers
                v = _strip_persian(v)
                if len(v) > 60:
                    v = v[:57] + "..."
                rows.append((label, v))
                break
    return rows


def _strip_persian(text: str) -> str:
    """
    Convert humanized Persian values back to plain English for PDF.
    Example: "افقی (نرمال) (1)" -> "(1)"
    """
    import re
    # Extract the number in parentheses at the end, if present
    m = re.search(r"\(([^()]+)\)\s*$", text)
    if m:
        return f"({m.group(1)})"
    return text