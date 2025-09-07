from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def make_theme_pdf(filename="sample-report.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()

    # Custom header style (like your WP theme)
    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#FFFFFF"),
        backColor=colors.HexColor("#0d0d0d"),
        alignment=1,  # center
        spaceAfter=20
    )

    normal = ParagraphStyle(
        "Normal",
        parent=styles["Normal"],
        fontSize=12,
        leading=16
    )

    story = []

    # Header
    story.append(Paragraph("SmartPlay AI – Insights Report", header_style))
    story.append(Spacer(1, 20))

    # Intro
    intro = """
    Harness the power of AI-driven analysis to optimize your lotto play. 
    This sample report demonstrates how SmartPlay AI highlights hot and cold numbers, 
    blends strategies, and delivers actionable insights for Jamaica Lotto, Super Lotto, and Powerball.
    """
    story.append(Paragraph(intro, normal))
    story.append(Spacer(1, 15))

    # Example table
    data = [
        ["Game", "Hot Numbers", "Cold Numbers", "Strategy"],
        ["Lotto", "8, 12, 30, 33", "2, 4, 5, 37", "Blend"],
        ["Super Lotto", "3, 14, 18", "5, 19, 27", "Cold"],
        ["Powerball", "11, 22, 44", "9, 16, 37", "Blend"]
    ]

    table = Table(data, colWidths=[100, 150, 150, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d0d0d")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke)
    ]))

    story.append(table)
    story.append(Spacer(1, 30))

    # Outro
    outro = """
    Upgrade to Premium to unlock weekly reports, extended predictions, and print-ready slips 
    tailored for your game of choice. Stay ahead with SmartPlay AI.
    """
    story.append(Paragraph(outro, normal))

    # Build PDF
    doc.build(story)

if __name__ == "__main__":
    make_theme_pdf()
