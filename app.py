# --- REPLACE your existing make_full_report with this version ---

from reportlab.platypus import KeepTogether  # add at top with other imports if not present

def make_full_report(game: str, tickets, strategy: str) -> bytes:
    """
    Full 3-section themed Insights Report (landscape):
      • Page 1: Cover + Hot/Cold/Strategy summary table
      • Page 2: Methodology, Disclaimer, Run Details (seed, game, strategy, counts)
      • Page 3: Generated Ticket Pack table
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "Header", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=28, textColor=colors.white, backColor=colors.HexColor("#0d0d0d"),
        alignment=1, spaceAfter=18, leading=34
    )
    subheader = ParagraphStyle("Subheader", parent=styles["Heading3"], fontSize=15, fontName="Helvetica-Bold")
    normal = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=11, leading=15)
    muted = ParagraphStyle("Muted", parent=styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#666666"), leading=13)

    PAGE_W, PAGE_H = landscape(A4)
    CONTENT_W = PAGE_W - 72  # 36+36 margins

    story = []

    # ---------------- Page 1: Cover + Summary table ----------------
    story.append(Paragraph("SmartPlay AI — Insights Report", header_style))
    story.append(Paragraph(datetime.utcnow().strftime("Generated %Y-%m-%d (UTC)"), muted))
    story.append(Spacer(1, 10))

    intro = (
        "<strong>SmartPlay AI</strong> highlights hot and cold number trends and produces balanced ticket sets. "
        "This report summarizes current guidance for <em>Jamaica Lotto</em>, <em>Super Lotto</em>, and <em>Powerball</em>."
    )
    story.append(Paragraph(intro, normal))
    story.append(Spacer(1, 12))

    # Hot/Cold/Strategy table (same look as your sample)
    w1, w2, w3, w4 = 150, 230, 230, CONTENT_W - (150 + 230 + 230)
    summary_rows = [
        ["Game", "Suggested Hot Numbers", "Suggested Cold/Overdue", "Recommended Strategy"],
        ["Jamaica Lotto (6/38 + Bonus)", "8, 12, 13, 21, 30, 33, 38", "1, 2, 4, 5, 6, 9, 10, 16, 19, 37", "Blend (≥2 hot, ≥2 cold)"],
        ["Super Lotto (5/35 + SB 1–10)", "3, 14, 18, 24, 28", "5, 9, 19, 27, 33", "Cold emphasis + SB spread"],
        ["Powerball (5/69 + PB 1–26)", "11, 22, 33, 44, 55", "9, 16, 37, 48", "Blend whites, random PB"],
    ]
    summary_tbl = Table(summary_rows, colWidths=[w1, w2, w3, w4])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d0d0d")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 11),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(summary_tbl)

    story.append(PageBreak())

    # ---------------- Page 2: Methodology + Disclaimer + Run details ----------------
    section = []

    section.append(Paragraph("Methodology (Overview)", subheader))
    section.append(Paragraph(
        "We compute recency-weighted frequencies to classify numbers into <strong>hot</strong> (recently common), "
        "<strong>cold/overdue</strong> (rare lately), and <strong>neutral</strong>. We then generate tickets using "
        "controlled randomness with constraints (e.g., minimum hot/cold counts) and optional clustering "
        "(e.g., overdue cluster 2–4–5–37).", normal
    ))
    section.append(Spacer(1, 8))

    section.append(Paragraph("Disclaimer", subheader))
    section.append(Paragraph(
        "This report is for entertainment and analysis only. It does not guarantee outcomes. Must be 18+. "
        "Play responsibly.", muted
    ))
    section.append(Spacer(1, 12))

    # Run details (adds substance and reproducibility)
    nice_game = {"lotto": "Lotto", "super": "Super Lotto", "powerball": "Powerball"}.get(game, game.title())
    run_rows = [
        ["Run Details", "Value"],
        ["Game", nice_game],
        ["Strategy", strategy],
        ["Tickets generated", str(len(tickets))],
        ["Seed", str(st.session_state.get("seed", "—"))],
        ["Report version", "v1.2 (demo templates)"],
    ]
    run_tbl = Table(run_rows, colWidths=[180, CONTENT_W - 180])
    run_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d0d0d")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
    ]))
    section.append(run_tbl)

    story.append(KeepTogether(section))
    story.append(PageBreak())

    # ---------------- Page 3: Generated ticket pack ----------------
    story.append(Paragraph(f"Example Ticket Pack ({nice_game}, Strategy: {strategy})", subheader))

    if game == "lotto":
        rows = [["Ticket", "Numbers"]]
        for i, nums in enumerate(tickets, 1):
            rows.append([f"Lotto {i}", ", ".join(map(str, nums))])
        col_widths = [180, CONTENT_W - 180]
    elif game == "super":
        rows = [["Ticket", "Numbers", "SB"]]
        for i, (mains, sb) in enumerate(tickets, 1):
            rows.append([f"Super {i}", ", ".join(map(str, mains)), str(sb)])
        col_widths = [180, CONTENT_W - 180 - 80, 80]
    else:  # powerball
        rows = [["Ticket", "Numbers", "PB"]]
        for i, (whites, pb) in enumerate(tickets, 1):
            rows.append([f"Powerball {i}", ", ".join(map(str, whites)), str(pb)])
        col_widths = [180, CONTENT_W - 180 - 80, 80]

    t2 = Table(rows, colWidths=col_widths)
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d0d0d")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t2)

    doc.build(story)
    return buf.getvalue()
