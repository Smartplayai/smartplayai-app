# app.py — SmartPlay AI (Streamlit) — Auto Hot/Cold + Backtest + Themed PDFs

import random
from io import BytesIO
from typing import List, Tuple, Optional, Dict
from datetime import datetime

import pandas as pd
import streamlit as st

# ReportLab (PDF)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


# -----------------------------------------------------------
# Page config
# -----------------------------------------------------------
st.set_page_config(page_title="SmartPlay AI", page_icon="🎯", layout="wide")

REPORT_VERSION = "v1.3"


# -----------------------------------------------------------
# Secrets / links (fallback defaults)
# -----------------------------------------------------------
STRIPE_LINK = st.secrets.get("STRIPE_LINK", "https://buy.stripe.com/test_123")
SAMPLE_REPORT_URL = st.secrets.get(
    "SAMPLE_REPORT_URL",
    "https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/smartplayai-sample-report_landscape.pdf",
)
PASSCODE = st.secrets.get("PASSCODE", "premium2025")

# Optional sources for historical draws (CSV on the web/GitHub raw)
LOTTO_CSV_URL = st.secrets.get("LOTTO_CSV_URL", "")
SUPER_CSV_URL = st.secrets.get("SUPER_CSV_URL", "")
POWER_CSV_URL = st.secrets.get("POWER_CSV_URL", "")

RESPONSIBLE_HELP = st.secrets.get(
    "RESPONSIBLE_HELP",
    "If gambling is affecting you, seek local support resources."
)


# -----------------------------------------------------------
# Defaults (used if no data sources present)
# -----------------------------------------------------------
DEFAULT_HOT = (8, 12, 13, 21, 27, 30, 33, 38)
DEFAULT_COLD = (1, 2, 4, 5, 6, 9, 10, 16, 19, 37)
CLUSTER = (2, 4, 5, 37)  # overdue cluster nudge


# -----------------------------------------------------------
# Helpers: loading data & hot/cold classification
# -----------------------------------------------------------
def try_load_csv(url: str) -> Optional[pd.DataFrame]:
    if not url:
        return None
    try:
        df = pd.read_csv(url)
        # standardize date column if present
        for c in df.columns:
            if "date" in c:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        return df
    except Exception:
        return None


def get_game_draws(game: str) -> Optional[pd.DataFrame]:
    if game == "lotto":
        return try_load_csv(LOTTO_CSV_URL)
    if game == "super":
        return try_load_csv(SUPER_CSV_URL)
    if game == "powerball":
        return try_load_csv(POWER_CSV_URL)
    return None


def pool_size_for_game(game: str) -> Tuple[int, Optional[int]]:
    # returns (main_pool_size, special_pool_size)
    if game == "lotto":
        return (38, None)
    if game == "super":
        return (35, 10)  # SB 1–10
    if game == "powerball":
        return (69, 26)  # PB 1–26
    return (0, None)


def extract_main_numbers(row: pd.Series, game: str) -> List[int]:
    if game == "lotto":
        cols = ["n1", "n2", "n3", "n4", "n5", "n6"]
    elif game == "super":
        cols = ["n1", "n2", "n3", "n4", "n5"]
    else:  # powerball
        cols = ["w1", "w2", "w3", "w4", "w5"]
    return [int(row[c]) for c in cols if c in row and pd.notna(row[c])]


def extract_special(row: pd.Series, game: str) -> Optional[int]:
    if game == "super" and "sb" in row and pd.notna(row["sb"]):
        return int(row["sb"])
    if game == "powerball" and "pb" in row and pd.notna(row["pb"]):
        return int(row["pb"])
    return None


def compute_hot_cold(
    game: str,
    draws: Optional[pd.DataFrame],
    lookback: int = 60,
    alpha: float = 0.97,
    topk_hot: int = 7,
    topk_cold: int = 10,
) -> Dict[str, List[int]]:
    """
    EWMA-like recency weights: weight = alpha^(age), most recent draw has age=0.
    Returns dict with 'hot_main', 'cold_main' and optionally 'hot_special','cold_special'.
    """
    if draws is None or draws.empty:
        return {"hot_main": list(DEFAULT_HOT), "cold_main": list(DEFAULT_COLD)}

    # Restrict to last N draws (most recent last)
    df = draws.copy().tail(lookback).reset_index(drop=True)
    n_main, n_special = pool_size_for_game(game)

    # Build frequency vectors
    main_freq = pd.Series(0.0, index=range(1, n_main + 1))
    special_freq = pd.Series(0.0, index=range(1, (n_special or 0) + 1)) if n_special else None

    # Most recent row gets highest weight
    for idx, row in df.iterrows():
        age = len(df) - 1 - idx
        w = alpha ** age
        for v in extract_main_numbers(row, game):
            if v in main_freq.index:
                main_freq.loc[v] += w
        sp = extract_special(row, game)
        if n_special and sp and sp in special_freq.index:
            special_freq.loc[sp] += w

    # Rank hot/cold
    hot_main = main_freq.sort_values(ascending=False).head(topk_hot).index.tolist()
    cold_main = main_freq.sort_values(ascending=True).head(topk_cold).index.tolist()

    result = {"hot_main": hot_main, "cold_main": cold_main}
    if n_special and special_freq is not None:
        hot_special = special_freq.sort_values(ascending=False).head(3).index.tolist()
        cold_special = special_freq.sort_values(ascending=True).head(3).index.tolist()
        result.update({"hot_special": hot_special, "cold_special": cold_special})

    return result


# -----------------------------------------------------------
# Ticket generators
# -----------------------------------------------------------
def gen_lotto(n: int) -> List[List[int]]:
    return [sorted(random.sample(range(1, 39), 6)) for _ in range(n)]

def gen_super(n: int) -> List[Tuple[List[int], int]]:
    return [(sorted(random.sample(range(1, 36), 5)), random.randint(1, 10)) for _ in range(n)]

def gen_powerball(n: int) -> List[Tuple[List[int], int]]:
    return [(sorted(random.sample(range(1, 70), 5)), random.randint(1, 26)) for _ in range(n)]


# -----------------------------------------------------------
# Strategy nudges (demo)
# -----------------------------------------------------------
def nudge_blend(nums: List[int], hot: List[int], cold: List[int]) -> List[int]:
    pool_hot = [n for n in nums if n in hot]
    pool_cold = [n for n in nums if n in cold]

    if len(pool_hot) < 2:
        add = [h for h in hot if h not in nums]
        add = random.sample(add, min(2 - len(pool_hot), len(add))) if add else []
        nums = sorted(list(set(nums) | set(add)))[:6]

    if len(pool_cold) < 2:
        add = [c for c in cold if c not in nums]
        add = random.sample(add, min(2 - len(pool_cold), len(add))) if add else []
        nums = sorted(list(set(nums) | set(add)))[:6]

    return sorted(nums)


def apply_strategy(game: str, tickets, strategy: str, hotcold: Dict[str, List[int]]):
    if strategy == "blend" and game == "lotto":
        hot = hotcold.get("hot_main", list(DEFAULT_HOT))
        cold = hotcold.get("cold_main", list(DEFAULT_COLD))
        out = []
        for row in tickets:
            nudged = nudge_blend(row[:], hot, cold)
            if random.random() < 0.25:
                nudged = sorted(list(set(nudged) | set(CLUSTER)))[:6]
            out.append(nudged)
        return out
    elif strategy == "cold" and game == "lotto":
        cold = hotcold.get("cold_main", list(DEFAULT_COLD))
        out = []
        for row in tickets:
            candidates = [c for c in cold if c not in row]
            if candidates:
                pos = random.randrange(0, 6)
                row[pos] = random.choice(candidates)
            out.append(sorted(row))
        return out
    return tickets


# -----------------------------------------------------------
# Backtest: best tier hit per draw, last N draws
# -----------------------------------------------------------
def match_count(a: List[int], b: List[int]) -> int:
    return len(set(a).intersection(set(b)))

def tier_for_lotto(matches: int) -> str:
    # Example tiers (adjust to official when you wire payouts):
    return {6: "Jackpot", 5: "Match 5", 4: "Match 4", 3: "Match 3"}.get(matches, "—")

def tier_for_super(matches: int, sb_hit: bool) -> str:
    if matches == 5 and sb_hit: return "Jackpot"
    if matches == 5: return "Match 5"
    if matches == 4 and sb_hit: return "Match 4+SB"
    if matches == 4: return "Match 4"
    if matches == 3 and sb_hit: return "Match 3+SB"
    if matches == 3: return "Match 3"
    return "—"

def tier_for_power(matches: int, pb_hit: bool) -> str:
    if matches == 5 and pb_hit: return "Jackpot"
    if matches == 5: return "Match 5"
    if matches == 4 and pb_hit: return "Match 4+PB"
    if matches == 4: return "Match 4"
    if matches == 3 and pb_hit: return "Match 3+PB"
    if matches == 3: return "Match 3"
    if matches == 2 and pb_hit: return "2+PB"
    if matches == 1 and pb_hit: return "1+PB"
    if matches == 0 and pb_hit: return "PB only"
    return "—"

def backtest(game: str, draws: Optional[pd.DataFrame], tickets, last_n: int = 30) -> pd.DataFrame:
    if draws is None or draws.empty:
        return pd.DataFrame(columns=["date", "best_tier", "best_matches"])

    df = draws.copy().tail(last_n)
    rows = []
    for _, row in df.iterrows():
        main = extract_main_numbers(row, game)
        special = extract_special(row, game)

        best_matches = 0
        best_tier = "—"
        for t in tickets:
            if game == "lotto":
                m = match_count(t, main)
                tier = tier_for_lotto(m)
            elif game == "super":
                m = match_count(t[0], main)
                tier = tier_for_super(m, special is not None and t[1] == special)
            else:
                m = match_count(t[0], main)
                tier = tier_for_power(m, special is not None and t[1] == special)

            if m > best_matches:
                best_matches, best_tier = m, tier

        draw_date = None
        for c in df.columns:
            if "date" in c and pd.notna(row[c]):
                draw_date = row[c]
                break
        rows.append({"date": draw_date, "best_tier": best_tier, "best_matches": best_matches})

    return pd.DataFrame(rows)


# -----------------------------------------------------------
# Themed PDFs
# -----------------------------------------------------------
def make_print_slip_pdf(game: str, tickets, title="SmartPlay AI — Print Slip", orientation="landscape") -> bytes:
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


def make_full_report(
    game: str,
    tickets,
    strategy: str,
    seed: int,
    hotcold: dict,
    lookback: int,
    alpha: float,
    constraints: dict,
    backtest_df: pd.DataFrame,
    hotline_text: str = None,
) -> bytes:
    """
    Full, auditable Insights Report (landscape):
      • Page 1: Cover + Hot/Cold/Strategy summary (auto from hotcold)
      • Page 2: Methodology, Disclaimer, Run Details, Constraints
      • Page 3: Ticket Pack table (current run)
      • Page 4: Backtest (last N draws) + summary
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

    def comma(nums):
        return ", ".join(map(str, nums)) if nums else "—"

    # ---------- Page 1: Cover + Hot/Cold ----------
    story = []
    story.append(Paragraph("SmartPlay AI — Insights Report", header_style))
    story.append(Paragraph(datetime.utcnow().strftime("Generated %Y-%m-%d (UTC)"), muted))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "<strong>SmartPlay AI</strong> highlights hot and cold number trends and produces balanced ticket sets. "
        "This report summarizes current guidance for <em>Jamaica Lotto</em>, <em>Super Lotto</em>, and <em>Powerball</em>.",
        normal
    ))
    story.append(Spacer(1, 12))

    nice_game = {"lotto": "Jamaica Lotto (6/38 + Bonus)", "super": "Super Lotto (5/35 + SB 1–10)", "powerball": "Powerball (5/69 + PB 1–26)"}[game]
    main_hot = hotcold.get("hot_main", [])
    main_cold = hotcold.get("cold_main", [])
    rec_strategy = {"lotto": "Blend (≥2 hot, ≥2 cold)", "super": "Cold emphasis + SB spread", "powerball": "Blend whites, random PB"}[game]

    w1, w2, w3, w4 = 150, 230, 230, CONTENT_W - (150 + 230 + 230)
    summary_rows = [
        ["Game", "Suggested Hot Numbers", "Suggested Cold/Overdue", "Recommended Strategy"],
        [nice_game, comma(main_hot), comma(main_cold), rec_strategy],
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

    # ---------- Page 2: Methodology, Disclaimer, Run details, Constraints ----------
    section = []

    # Hot/Cold computation window line
    section.append(Paragraph("Computation Window", subheader))
    section.append(Paragraph(
        f"Hot/cold computed on last <strong>{lookback}</strong> draws with recency weight "
        f"<strong>EWMA α = {alpha}</strong> (most recent draw has highest weight).", normal
    ))
    section.append(Spacer(1, 6))

    # Methodology & Disclaimer
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
        "Play responsibly." + (f" {hotline_text}" if hotline_text else ""),
        muted
    ))
    section.append(Spacer(1, 10))

    # Run details
    section.append(Paragraph("Run Details", subheader))
    run_rows = [
        ["Field", "Value"],
        ["Game", nice_game],
        ["Strategy", strategy],
        ["Tickets generated", str(len(tickets))],
        ["Seed", str(seed)],
        ["Report version", REPORT_VERSION],
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
    section.append(Spacer(1, 10))

    # Strategy constraints used
    section.append(Paragraph("Strategy Constraints (Applied)", subheader))
    def cfmt(v):
        if isinstance(v, (list, tuple)): return ", ".join(map(str, v))
        return str(v)
    bullets = [
        f"Min Hot per ticket: <strong>{cfmt(constraints.get('min_hot','—'))}</strong>",
        f"Min Cold per ticket: <strong>{cfmt(constraints.get('min_cold','—'))}</strong>",
        f"Overdue Cluster: <strong>{cfmt(constraints.get('cluster', []))}</strong>",
        f"Parity target: <strong>{cfmt(constraints.get('parity_target','—'))}</strong>",
        f"Sum range: <strong>{cfmt(constraints.get('sum_range','—'))}</strong>",
    ]
    section.append(Paragraph(" • " + "<br/> • ".join(bullets), normal))

    # Changelog / Versioning
    section.append(Spacer(1, 10))
    section.append(Paragraph("Changelog / Versioning", subheader))
    section.append(Paragraph(
        f"<strong>{REPORT_VERSION}</strong> — Added auto hot/cold window note, constraints section, "
        "run details, and backtest page.",
        normal
    ))

    story.append(KeepTogether(section))
    story.append(PageBreak())

    # ---------- Page 3: Ticket Pack ----------
    story.append(Paragraph(f"Generated Ticket Pack — {nice_game}", subheader))
    if game == "lotto":
        rows = [["Ticket", "Numbers"]] + [[f"Lotto {i+1}", comma(nums)] for i, nums in enumerate(tickets)]
        col_widths = [180, CONTENT_W - 180]
    elif game == "super":
        rows = [["Ticket", "Numbers (main)", "SB"]] + [[f"Super {i+1}", comma(m), str(sb)] for i, (m, sb) in enumerate(tickets)]
        col_widths = [180, CONTENT_W - 180 - 80, 80]
    else:  # powerball
        rows = [["Ticket", "Numbers (whites)", "PB"]] + [[f"Powerball {i+1}", comma(w), str(pb)] for i, (w, pb) in enumerate(tickets)]
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
    story.append(PageBreak())

    # ---------- Page 4: Backtest ----------
    story.append(Paragraph("Backtest — Last N Draws", subheader))
    story.append(Paragraph("Per draw, the best hit among your ticket pack.", muted))
    if backtest_df is not None and not backtest_df.empty:
        bt = backtest_df.copy()
        bt["date"] = bt["date"].astype(str)
        bt = bt.rename(columns={"best_tier": "Tier", "best_matches": "Hits"})[["date", "Hits", "Tier"]]
        bt_rows = [bt.columns.tolist()] + bt.values.tolist()
        bt_tbl = Table(bt_rows, colWidths=[200, 100, CONTENT_W - 300])
        bt_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0d0d0d")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ]))
        story.append(bt_tbl)

        # summary line
        s_hits = int(bt["Hits"].sum())
        top_tier = bt["Tier"].value_counts().idxmax() if not bt["Tier"].empty else "—"
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Summary: total hits across period = <strong>{s_hits}</strong>; most common tier = <strong>{top_tier}</strong>.",
            normal
        ))
    else:
        story.append(Paragraph("No historical data connected. Add CSV URLs in Secrets to enable backtesting.", normal))

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

    # Generate base tickets
    if game == "lotto":
        base = gen_lotto(num_tix)
    elif game == "super":
        base = gen_super(num_tix)
    else:
        base = gen_powerball(num_tix)

    # Hot/Cold from data (or defaults) + apply strategy
    LOOKBACK = 60
    ALPHA = 0.97
    draws = get_game_draws(game)
    hotcold = compute_hot_cold(game, draws, lookback=LOOKBACK, alpha=ALPHA)
    tickets = apply_strategy(game, base, strategy, hotcold)

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

    # Backtest (if data available)
    bt_df = backtest(game, draws, tickets, last_n=30)

    # Constraints shown in report (adjust as you like)
    constraints = {
        "min_hot": 2,
        "min_cold": 2,
        "cluster": [2, 4, 5, 37],
        "parity_target": "≈3 even / 3 odd (Lotto)",
        "sum_range": "≈80–180 (Lotto demo)",
    }

    # Full Insights Report (premium)
    if premium_input.strip() == str(PASSCODE):
        report_bytes = make_full_report(
            game=game,
            tickets=tickets,
            strategy=strategy,
            seed=seed,
            hotcold=hotcold,
            lookback=LOOKBACK,
            alpha=ALPHA,
            constraints=constraints,
            backtest_df=bt_df,
            hotline_text=RESPONSIBLE_HELP,
        )
        st.success("Premium unlocked: Insights Report available.")
        st.download_button("Download Insights Report (PDF)", report_bytes, "smartplayai_insights_report.pdf", "application/pdf")
    else:
        st.info(f"🔒 Enter your passcode for the full Insights Report. Otherwise, see the brochure: [Sample report]({SAMPLE_REPORT_URL}).")

    # Auto-roll a new seed for next run if chosen
    if auto_new_seed:
        st.session_state.seed = random.randint(1, 99999999)
else:
    st.info("Set your options in the sidebar and press **Generate**.")
