import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "generated_cvs")

def build_pdf_cv(cv_text, candidate_name, job_id):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = "".join(c for c in candidate_name if c.isalnum() or c in " _-").strip()
    filename = f"CV_{safe_name}_{job_id[:8]}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    accent = colors.HexColor("#1A56DB")

    style_name = ParagraphStyle("name", fontSize=22, textColor=accent, leading=26, alignment=TA_CENTER, fontName="Helvetica-Bold")
    style_section = ParagraphStyle("section", fontSize=11, textColor=accent, leading=16, fontName="Helvetica-Bold", spaceBefore=12)
    style_body = ParagraphStyle("body", fontSize=9.5, leading=14, fontName="Helvetica", textColor=colors.HexColor("#333333"))
    style_bullet = ParagraphStyle("bullet", fontSize=9.5, leading=14, fontName="Helvetica", leftIndent=14, bulletIndent=4, textColor=colors.HexColor("#333333"))

    story = []
    lines = cv_text.split("\n")
    first_line = True

    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        if first_line:
            story.append(Paragraph(line, style_name))
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=1.5, color=accent))
            story.append(Spacer(1, 6))
            first_line = False
            continue

        # Détecter les titres de section (tout en majuscules ou ligne courte en caps)
        if line.isupper() and len(line) < 40:
            story.append(Spacer(1, 6))
            story.append(Paragraph(line, style_section))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
            story.append(Spacer(1, 4))
        elif line.startswith("•") or line.startswith("-") or line.startswith("*"):
            clean = line.lstrip("•-* ").strip()
            story.append(Paragraph(f"• {clean}", style_bullet))
        else:
            story.append(Paragraph(line, style_body))

    doc.build(story)
    print(f"📄 CV PDF généré : {filepath}")
    return filepath
