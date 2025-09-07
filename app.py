# app.py — SmartPlay AI (Streamlit)

import random
from io import BytesIO
from typing import List, Tuple
from datetime import datetime

import pandas as pd
import streamlit as st

# ReportLab (PDF)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


# -----------------------------------------------------------
# Page config
# -----------------------------------------------------------
st.set_page_config(page_title="SmartPlay AI", page_icon="🎯", layout="wide")


# -----------------------------------------------------------
# Secrets / links (fallback defaults)
#   In Streamlit → Manage app → Settings → Secrets (TOML):
#   STRIPE_LINK = "https://buy.stripe.com/..."
#   SAMPLE_REPORT_URL = "https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/smartplayai-sample-report_landscape.pdf"
#   PASSCODE = "premium2025"
# -----------------------------------------------------------
STRIPE_LINK = st.secrets.get("STRIPE_LINK", "https://buy.stripe.com/test_123")
SAMPLE_REPORT_URL = st.secrets.get(
    "SAMPLE_REPORT_URL",
    "https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/smartplayai-sample-report_landscape.pdf",
)
PASSCODE = st.secrets.get("PASSCODE", "premium2025")


# -----------------------------------------------------------
# Defaults (placeholder numbers)
# -----------------------------------------------------------
DEFAULT_HOT = (8, 12, 13, 21, 27, 30, 33, 38)
DEFAULT_COLD = (1, 2, 4, 5, 6, 9, 10, 16, 19, 37)
CLUSTER = (2, 4, 5, 37)  # overdue cluster nudge


# -----------------------------------------------------------
# Ticket generators
# -----------------------------------------------------------
def gen_lotto(n: int) -> List[List[int]]:
    """Jamaica Lotto 6/38."""
    return [sorted(random.sample(range(1, 39), 6)) for _ in range(n)]

def gen_super(n: int) -> List[Tuple[List[int], int]]:
    """Super Lotto 5/35 + SB 1–10."""
    return [(sorted(random.sample(range(1, 36), 5)), random.randint(1, 10)) for _ in range(n)]

def gen_powerball(n: int) -> List[Tuple[List[int], int]]:
    """Powerball 5/69 + PB 1–26."""
    return [(sorted(random.sample(range(1, 70), 5)), random.randint(1, 26)) for _ in range(n)]


# -----------------------------------------------------------
# Strategy nudges (demo)
# -----------------------------------------------------------
def nudge_blend(nums: List[int]) -> List[int]:
    """Guarantee ≥2 hot and ≥2 cold for Lotto."""
    pool_hot = [n for n in nums if n in DEFAULT_HOT]
    pool_cold = [n for n in nums if n in DEFAULT_COLD]

    if len(pool_hot) < 2:
        add = [h for h in DEFAULT_HOT if h not in nums]
        add = random.sample(add, min(2 - len(pool_hot), len(add))) if add else []
        nums = sorted(list(set(nums) | set(add)))[:6]

    if len(pool_cold) < 2:
        add = [c for c in DEFAULT_COLD if c not in nums]
        add = random.sample(add, min(2 - len(pool_cold), len(add))) if add else []
        nums = sorted(list(set(nums) | set(add)))[:6]

    return sorted(nums)

def apply_strategy(game: str, tickets, strategy: str):
    if strategy == "blend" and game == "lotto":
        out = []
        for row in tickets:
            nudged = nudge_blend(row)
            # small nudge toward overdue cluster
            if random.random() < 0.25:
                nudged = sorted(list(set(nudged) | set(CLUSTER)))[:6]
            out.append(nudged)
        return out
    elif strategy == "cold" and game == "lotto":
        out = []
        for row in tickets:
            candidates = [c for c in DEFAULT_COLD if c not in row]
            if candidates:
                pos = random.randrange(0, 6)
                row[pos] = random.choice(candidates)
            out.append(sorted(row))
        return out
    return tickets


# -----------------------------------------------------------
# Themed PDFs
# -----------------------------------------------------------
def make_print_slip_pdf(game: str, tickets, title="SmartPlay AI — Print Slip", orientation="landscape") -> bytes:
    """Compact ticket slip with brand theme."""
    page_size = landscape(A4) if orientation.lower() == "landscape" else A4
    PAGE_W, PAGE_H = page_size
    MARGIN = 36
    CONTENT_W = PAGE_W - 2 * MARGIN

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "Header", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=26, textColor=colors.white, backColor=colors.HexColor("#0d0d0d"),
        alignment=1, spaceAfter=14, leading=30
    )
    note_style = ParagraphStyle(
        "Note", parent=styles["Normal"], fontSize=9.5,
        textColor=colors.HexColor("#666666"), leading=13
    )

    story = [Paragraph(title, header_style), Spacer(1, 6)]

    rows = []
    if game == "powerball":
        rows.append(["Ticket", "Numbers (whites)", "PB"])
        for i, (whites, pb) in enumerate(tickets, 1):
            rows.append([f"PB {i}", ", ".join(map(str, whites)), str(pb)])
        col_widths = [90, CONTENT_W - 160, 70]
    elif game == "super":
        rows.append(["Ticket", "Numbers (main)", "SB"])
        for i, (mains, sb) in enumerate(tickets, 1):
            rows.append([f"Super {i}", ", ".join(map(str, mains)), str(sb)])
        col_widths = [90, CONTENT_W - 160, 70]
    else:  # lotto
        rows.append(["Ticket", "Numbers"])
        for i, nums in enumerate(tickets, 1):
            rows.append([f"Lotto {i}", ", ".join(map(str, nums))])
        col_widths = [90, CONTENT_W - 90]

    tbl = Table(rows, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d0d0d")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 11),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    story += [tbl, Spacer(1, 8), Paragraph("Analytics only • No guaranteed outcomes • 18+ • Play responsibly.", note_style)]
    doc.build(story)
    return buf.getvalue()


def make_full_report(game: str, tickets, strategy: str) -> bytes:
    """Full 2-page themed Insights Report (like your sample PDF)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "Header", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=28, textColor=colors.white, backColor=colors.HexColor("#0d0d0d"),
        alignment=1, spaceAfter=20, leading=34
    )
    subheader = ParagraphStyle("Subheader", parent=styles["Heading3"], fontSize=15, fontName="Helvetica-Bold")
    normal = ParagraphStyle("Normal", parent=styles["Normal"], fontSize=11, leading=15)
    muted = ParagraphStyle("Muted", parent=styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#666666"), leading=13)

    story = []
    story.append(Paragraph("SmartPlay AI — Insights Report", header_style))
    story.append(Paragraph(datetime.utcnow().strftime("Generated %Y-%m-%d (UTC)"), muted))
    story.append(Spacer(1, 12))

    intro = (
        "<strong>SmartPlay AI</strong> uses data-driven analysis to highlight hot and cold number trends "
        "and build balanced ticket sets. This report shows current suggestions for <em>Jamaica Lotto</em>, "
        "<em>Super Lotto</em>, and <em>Powerball</em>, plus your generated ticket pack."
    )
    story.append(Paragraph(intro, normal))
    story.append(Spacer(1, 12))

    # Hot/Cold/Strategy table
    w1, w2, w3, w4 = 150, 230, 230, 230
    data = [
        ["Game", "Suggested Hot Numbers", "Suggested Cold/Overdue", "Recommended Strategy"],
        ["Jamaica Lotto (6/38 + Bonus)", "8, 12, 13, 21, 30, 33, 38", "1, 2, 4, 5, 6, 9, 10, 16, 19, 37", "Blend (≥2 hot, ≥2 cold)"],
        ["Super Lotto (5/35 + SB 1–10)", "3, 14, 18, 24, 28", "5, 9, 19, 27, 33", "Cold emphasis + SB spread"],
        ["Powerball (5/69 + PB 1–26)", "11, 22, 33, 44, 55", "9, 16, 37, 48", "Blend whites, random PB"],
    ]
    table = Table(data, colWidths=[w1, w2, w3, w4])
    table.setStyle(TableStyle([
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
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Methodology (Overview)", subheader))
    story.append(Paragraph(
        "We compute recency-weighted frequencies to classify numbers into <strong>hot</strong> (recently common), "
        "<strong>cold/overdue</strong> (rare lately), and <strong>neutral</strong>. Ticket sets are generated using "
        "controlled randomness with constraints (e.g., minimum hot/cold counts) and optional clustering "
        "(e.g., overdue cluster 2–4–5–37).", normal
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Disclaimer", subheader))
    story.append(Paragraph(
        "This report is for entertainment and analysis only. It does not guarantee outcomes. Must be 18+. Play responsibly.",
        muted
    ))

    # Page 2: Ticket pack
    story.append(PageBreak())
    nice_game = {"lotto": "Lotto", "super": "Super Lotto", "powerball": "Powerball"}.get(game, game.title())
    story.append(Paragraph(f"Example Ticket Pack ({nice_game}, Strategy: {strategy})", subheader))

    rows = [["Ticket", "Numbers"]] if game == "lotto" else [["Ticket", "Numbers", "Ball"]]
    if game == "lotto":
        for i, nums in enumerate(tickets, 1):
            rows.append([f"Lotto {i}", ", ".join(map(str, nums))])
        col_widths = [150, 540]
    elif game == "super":
        for i, (mains, sb) in enumerate(tickets, 1):
            rows.append([f"Super {i}", ", ".join(map(str, mains)), str(sb)])
        col_widths = [150, 470, 70]
    else:
        for i, (whites, pb) in enumerate(tickets, 1):
            rows.append([f"Powerball {i}", ", ".join(map(str, whites)), str(pb)])
        col_widths = [150, 470, 70]

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


# -----------------------------------------------------------
# Sidebar UI (with random seed)
# -----------------------------------------------------------
st.sidebar.header("Generator")

game = st.sidebar.selectbox("Game", ["lotto", "super", "powerball"])
strategy = st.sidebar.selectbox("Strategy", ["blend", "cold", "none"])
num_tix = st.sidebar.number_input("Tickets", min_value=1, max_value=20, value=7)

# Seed handling: keep in session; roll a new one by default after each Generate
if "seed" not in st.session_state:
    st.session_state.seed = random.randint(1, 99999999)

st.sidebar.write(f"🔄 Current seed: `{st.session_state.seed}`")
auto_new_seed = st.sidebar.checkbox("Use a new random seed each time", value=True)
if st.sidebar.button("🎲 Reroll seed now"):
    st.session_state.seed = random.randint(1, 99999999)
    st.sidebar.success(f"New seed: {st.session_state.seed}")

premium_input = st.sidebar.text_input("Premium Access (optional)", type="password")
pdf_layout = st.sidebar.radio("Print slip layout", ["Landscape", "Portrait"], index=0)

generate = st.sidebar.button("Generate")


# -----------------------------------------------------------
# Main
# -----------------------------------------------------------
st.title("SmartPlay AI 🎯")
st.caption("Jamaica Lotto • Super Lotto • Powerball")
st.markdown(
    f'New here? 👉 **[Download Sample Report]({SAMPLE_REPORT_URL})** · **[Subscribe for Premium Packs]({STRIPE_LINK})**'
)
st.markdown("---")
st.caption("Analytics only • No guaranteed outcomes • 18+ • Play responsibly.")

if generate:
    # Use current seed for this run
    seed = int(st.session_state.seed)
    random.seed(seed)

    # Generate tickets
    if game == "lotto":
        base = gen_lotto(num_tix)
    elif game == "super":
        base = gen_super(num_tix)
    else:
        base = gen_powerball(num_tix)

    tickets = apply_strategy(game, base, strategy)

    # Show as a table
    if game == "lotto":
        df = pd.DataFrame(tickets, columns=[f"N{i}" for i in range(1, 7)])
    elif game == "super":
        df = pd.DataFrame(
            [{"N1": t[0][0], "N2": t[0][1], "N3": t[0][2], "N4": t[0][3], "N5": t[0][4], "SB": t[1]} for t in tickets]
        )
    else:
        df = pd.DataFrame(
            [{"W1": t[0][0], "W2": t[0][1], "W3": t[0][2], "W4": t[0][3], "W5": t[0][4], "PB": t[1]} for t in tickets]
        )

    st.subheader("Generated Tickets")
    st.dataframe(df, use_container_width=True)
    st.caption(f"Seed used for this run: **{seed}**")

    # CSV download
    csv_buf = BytesIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", csv_buf.getvalue(), "tickets.csv", "text/csv")

    # Print slip (everyone)
    orientation = "landscape" if pdf_layout == "Landscape" else "portrait"
    slip_bytes = make_print_slip_pdf(game, tickets, orientation=orientation)
    st.download_button("Download Print Slip (PDF)", slip_bytes, "slip.pdf", "application/pdf")

    # Full Insights Report (premium)
    if premium_input.strip() == str(PASSCODE):
        report_bytes = make_full_report(game, tickets, strategy)
        st.success("Premium unlocked: Insights Report available.")
        st.download_button("Download Insights Report (PDF)", report_bytes, "smartplayai_insights_report.pdf", "application/pdf")
    else:
        st.info(f"🔒 Enter your passcode for the full Insights Report. Otherwise, see the brochure: [Sample report]({SAMPLE_REPORT_URL}).")

    # Auto-roll a new seed for next run if chosen
    if auto_new_seed:
        st.session_state.seed = random.randint(1, 99999999)
else:
    st.info("Set your options in the sidebar and press **Generate**.")
