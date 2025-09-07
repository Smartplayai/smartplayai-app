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
    if game == "super" and "sb" in row:
        return int(row["sb"])
    if game == "powerball" and "pb" in row:
        return int(row["pb"])
    return None


def compute_hot_cold(
    game: str,
    draws: pd.DataFrame,
    lookback: int = 60,
    alpha: float = 0.97,
    topk_hot: int = 7,
    topk_cold: int = 10,
) -> Dict[str, List[int]]:
    """
    EWMA-like recency weights: weight = alpha^(age), most recent draw has age=0.
    Returns dict with 'hot_main', 'cold_main', and optionally 'hot_special','cold_special'.
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
    # Example: SB can improve tier. Customize as needed.
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

def backtest(game: str, draws: pd.DataFrame, tickets, last_n: int = 30) -> pd.DataFrame:
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
        rows.append(["Ticket", "Numbers (main)", "SB
