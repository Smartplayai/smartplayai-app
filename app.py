# app.py — SmartPlay AI (Streamlit)

import random
from io import BytesIO
from typing import List, Tuple

import pandas as pd
import streamlit as st

# PDF exports (themed)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# -----------------------------------------------------------
# Page config
# -----------------------------------------------------------
st.set_page_config(page_title="SmartPlay AI", page_icon="🎯", layout="centered")

# -----------------------------------------------------------
# Secrets / links (with safe fallbacks)
# -----------------------------------------------------------
STRIPE_LINK = st.secrets.get("STRIPE_LINK", "https://buy.stripe.com/your-real-checkout-link")
SAMPLE_REPORT_URL = st.secrets.get(
    "SAMPLE_REPORT_URL",
    # fallback to your landscape sample in GitHub if secrets missing
    "https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/smartplayai-sample-report_landscape.pdf",
)
PASSCODE = st.secrets.get("PASSCODE", "premium2025")

# -----------------------------------------------------------
# Demo “latest results” (placeholder)
# -----------------------------------------------------------
LOTTO_TODAY = {"main": (2, 4, 5, 12, 33, 37), "bonus": 10}
SUPER_TODAY = {"main": (3, 14, 18, 24, 28), "sb": 9}
PB_TODAY = {"whites": (11, 22, 33, 44, 55), "pb": 4}

# -----------------------------------------------------------
# Default frequency sets (placeholder)
# -----------------------------------------------------------
DEFAULT_HOT = (8, 12, 13, 21, 27, 30, 33, 38)
DEFAULT_COLD = (1, 2, 4, 5, 6, 9, 10, 16, 19, 37)
CLUSTER = (2, 4, 5, 37)  # overdue cluster we sometimes nudge toward


# -----------------------------------------------------------
# Utility: ticket generation for each game
# -----------------------------------------------------------
def gen_lotto(n: int) -> List[List[int]]:
    """Jamaica Lotto 6/38 (no bonus in ticket)."""
    tickets = []
    for _ in range(n):
        nums = sorted(random.sample(range(1, 39), 6))
        tickets.append(nums)
    return tickets


def gen_super(n: int) -> List[Tuple[List[int], int]]:
    """Super Lotto 5/35 + Super Ball 1–10."""
    tickets = []
    for _ in range(n):
        mains = sorted(random.sample(range(1, 36), 5))
        sb = random.randint(1, 10)
        tickets.append((mains, sb))
    return tickets


def gen_powerball(n: int) -> List[Tuple[List[int], int]]:
    """Powerball 5/69 + PB 1–26."""
    tickets = []
    for _ in range(n):
        whites = sorted(random.sample(range(1, 70), 5))
        pb = random.randint(1, 26)
        tickets.append((whites, pb))
    return tickets


# -----------------------------------------------------------
# Strategy nudges (very light-touch demo logic)
# -----------------------------------------------------------
def nudge_blend(nums: List[int], hot=DEFAULT_HOT, cold=DEFAULT_COLD) -> List[int]:
    """Ensure at least ~2 hot and ~2 cold when possible (Lotto)."""
    pool_hot = [n for n in nums if n in hot]
    pool_cold = [n for n in nums if n in cold]
    if len(pool_hot) < 2:
        # inject some hot numbers if available
        needed = 2 - len(pool_hot)
        choices = [h for h in hot if h not in nums]
        nums = sorted((set(nums) - set(pool_cold)).union(set(random.sample(choices, min(needed, len(choices))))) | set(pool_cold))
        nums = sorted(list(nums))[:6]
    if len(pool_cold) < 2:
        needed = 2 - len(pool_cold)
        choices = [c for c in cold if c not in nums]
        nums = sorted((set(nums) - set(pool_hot)).union(set(random.sample(choices, min(needed, len(choices))))) | set(pool_hot))
        nums = sorted(list(nums))[:6]
    return sorted(nums)


def apply_strategy(game: str, tickets, strategy: str):
    """Apply very simple strategy hints to tickets."""
    if strategy == "blend":
        if game == "lotto":
            out = []
            for row in tickets:
                nudged = nudge_blend(row)
                # small chance to include overdue cluster
                if random.random() < 0.25:
                    picks = set(nudged)
                    need = 6 - len(picks.intersection(CLUSTER))
                    picks = sorted(list((picks | set(CLUSTER)) if need > 0 else picks))[:6]
                    nudged = sorted(picks)
                out.append(nudged)
            return out
        # for super/powerball just leave as generated (demo)
        return tickets
    elif strategy == "cold":
        # tilt slightly toward cold by replacing 1-2 spots (Lotto only, demo)
        if game == "lotto":
            out = []
            for row in tickets:
                candidates = [c for c in DEFAULT_COLD if c not in row]
                replace_count = 1 + (random.random() < 0.35)
                for _ in range(int(replace_count)):
                    pos = random.randrange(0, 6)
                    if candidates:
                        row[pos] = random.choice(candidates)
                out.append(sorted(row))
            return out
        return tickets
    else:
        return tickets


# -----------------------------------------------------------
# PDF generator (themed, portrait/landscape)
# -----------------------------------------------------------
def make_print_slip_pdf(game: str, tickets, title="SmartPlay AI — Print Slip", orientation="landscape") -> bytes:
    """Create a print-ready ticket slip PDF with SmartPlay AI theme."""
    page_size = landscape(A4) if orientation.lower() == "landscape" else A4
    PAGE_W, PAGE_H = page_size
    MARGIN = 36
    CONTENT_W = PAGE_W - 2 * MARGIN

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "Header",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=26,
        textColor=colors.HexColor("#FFFFFF"),
        backColor=colors.HexColor("#0d0d0d"),
        alignment=1,
        spaceAfter=14,
        leading=30,
    )
    note_style = ParagraphStyle(
        "Note",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=colors.HexColor("#666666"),
        leading=13,
    )

    story = []
    story.append(Paragraph(title, header_style))
    story.append(Spacer(1, 6))

    # Build rows
    rows = []
    if game == "powerball":
        rows.append(["Ticket", "Numbers (whites)", "PB"])
        for i, t in enumerate(tickets, 1):
            rows.append([f"PB {i}", ", ".join(map(str, t[0])), str(t[1])])
        col_widths = [90, CONTENT_W - 90 - 70, 70]
    elif game == "super":
        rows.append(["Ticket", "Numbers (main)", "SB"])
        for i, t in enumerate(tickets, 1):
            rows.append([f"Super {i}", ", ".join(map(str, t[0])), str(t[1])])
        col_widths = [90, CONTENT_W - 90 - 70, 70]
    else:
        rows.append(["Ticket", "Numbers"])
        for i, nums in enumerate(tickets, 1):
            rows.append([f"Lotto {i}", ", ".join(map(str, nums))])
        col_widths = [90, CONTENT_W - 90]

    table = Table(rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d0d0d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Analytics only • No guaranteed outcomes • 18+ • Play responsibly.", note_style))

    doc.build(story)
    return buf.getvalue()


# -----------------------------------------------------------
# UI — Sidebar
# -----------------------------------------------------------
st.sidebar.header("Generator")
game = st.sidebar.selectbox("Game", ["lotto", "super", "powerball"])
strategy = st.sidebar.selectbox("Strategy", ["blend", "cold", "none"], index=0)
n_tickets = st.sidebar.number_input("Tickets", min_value=1, max_value=20, value=7, step=1)
seed = st.sidebar.number_input("Seed (reproducible)", value=20250831, step=1)

st.sidebar.subheader("Premium Access (optional)")
entered = st.sidebar.text_input("Subscriber passcode", type="password")
is_premium = bool(entered.strip()) and (entered.strip() == str(PASSCODE))

pdf_layout = st.sidebar.radio("PDF layout", ["Landscape", "Portrait"], index=0)

# -----------------------------------------------------------
# Main — Header & links
# -----------------------------------------------------------
st.title("SmartPlay AI 🎯")
st.caption("Jamaica Lotto • Super Lotto • Powerball")

st.markdown(
    f'New here? 👉 **[Download Sample Report]({SAMPLE_REPORT_URL})** · **[Subscribe for Premium Packs]({STRIPE_LINK})**'
)

st.markdown("---")
st.caption("Analytics only • No guaranteed outcomes • 18+ • Play responsibly.")

# -----------------------------------------------------------
# Generate button
# -----------------------------------------------------------
if st.button("Generate", type="primary"):
    # Fix seed for reproducibility
    random.seed(int(seed))

    # 1) Generate base tickets
    if game == "lotto":
        tickets = gen_lotto(n_tickets)
    elif game == "super":
        tickets = gen_super(n_tickets)
    else:
        tickets = gen_powerball(n_tickets)

    # 2) Apply simple strategy nudges
    tickets = apply_strategy(game, tickets, strategy)

    # 3) Premium bonus pack
    if is_premium:
        # add 3 extra tickets with same seed stream
        extra = 3
        if game == "lotto":
            tickets += gen_lotto(extra)
        elif game == "super":
            tickets += gen_super(extra)
        else:
            tickets += gen_powerball(extra)
        st.success("Premium unlocked: added 3 bonus tickets.")

    # 4) Show table and downloads
    if game == "lotto":
        df = pd.DataFrame(tickets, columns=[f"N{i}" for i in range(1, 7)])
    elif game == "super":
        df = pd.DataFrame(
            [{"N1": *t[0][:1], "N2": t[0][1], "N3": t[0][2], "N4": t[0][3], "N5": t[0][4], "SB": t[1]} for t in tickets]
        )
        # The above unpack trick is a bit messy; clearer approach:
        df = pd.DataFrame(
            [{"N1": t[0][0], "N2": t[0][1], "N3": t[0][2], "N4": t[0][3], "N5": t[0][4], "SB": t[1]} for t in tickets]
        )
    else:
        df = pd.DataFrame(
            [{"W1": t[0][0], "W2": t[0][1], "W3": t[0][2], "W4": t[0][3], "W5": t[0][4], "PB": t[1]} for t in tickets]
        )

    st.dataframe(df, use_container_width=True)

    # CSV download
    csv_buf = BytesIO()
    df.to_csv(csv_buf, index=False)
    st.download_button("Download CSV", csv_buf.getvalue(), "tickets.csv", "text/csv")

    # Themed PDF download (landscape by default)
    orientation = "landscape" if pdf_layout == "Landscape" else "portrait"
    pdf_bytes = make_print_slip_pdf(game, tickets, orientation=orientation)
    st.download_button("Download Print Slip (PDF)", pdf_bytes, "slip.pdf", "application/pdf")

else:
    st.info("Select a game and strategy, then click **Generate** to create ticket sets.")
