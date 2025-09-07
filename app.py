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
st.set_page_config(page_title="SmartPlay AI", page_icon="🎯", layout="centered")


# -----------------------------------------------------------
# Secrets / links (with safe fallbacks)
#   Set these in Streamlit Cloud → Settings → Secrets (TOML)
#   STRIPE_LINK = "https://buy.stripe.com/..."
#   SAMPLE_REPORT_URL = "https://github.com/.../raw/main/smartplayai-sample-report_landscape.pdf"
#   PASSCODE = "premium2025"
# -----------------------------------------------------------
STRIPE_LINK = st.secrets.get("STRIPE_LINK", "https://buy.stripe.com/your-real-checkout-link")
SAMPLE_REPORT_URL = st.secrets.get(
    "SAMPLE_REPORT_URL",
    "https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/smartplayai-sample-report_landscape.pdf",
)
PASSCODE = st.secrets.get("PASSCODE", "premium2025")


# -----------------------------------------------------------
# Demo “latest results” (placeholders)
# -----------------------------------------------------------
LOTTO_TODAY = {"main": (2, 4, 5, 12, 33, 37), "bonus": 10}
SUPER_TODAY = {"main": (3, 14, 18, 24, 28), "sb": 9}
PB_TODAY = {"whites": (11, 22, 33, 44, 55), "pb": 4}


# -----------------------------------------------------------
# Default frequency sets (placeholder)
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
    out = []
    for _ in range(n):
        mains = sorted(random.sample(range(1, 36), 5))
        sb = random.randint(1, 10)
        out.append((mains, sb))
    return out


def gen_powerball(n: int) -> List[Tuple[List[int], int]]:
    """Powerball 5/69 + PB 1–26."""
    out = []
    for _ in range(n):
        whites = sorted(random.sample(range(1, 70), 5))
        pb = random.randint(1, 26)
        out.append((whites, pb))
    return out


# -----------------------------------------------------------
# Strategy nudges (light demo)
# -----------------------------------------------------------
def nudge_blend(nums: List[int], hot=DEFAULT_HOT, cold=DEFAULT_COLD) -> List[int]:
    """Aim for ≥2 hot and ≥2 cold when possible (Lotto only)."""
    pool_hot = [n for n in nums if n in hot]
    pool_cold = [n for n in nums if n in cold]

    if len(pool_hot) < 2:
        needed = 2 - len(pool_hot)
        choices = [h for h in hot if h not in nums]
        add = random.sample(choices, min(needed, len(choices))) if choices else []
        nums = sorted(list(set(nums) | set(add)))[:6]

    if len(pool_cold) < 2:
        needed = 2 - len(pool_cold)
        choices = [c for c in cold if c not in nums]
        add = random.sample(choices, min(needed, len(choices))) if choices else []
        nums = sorted(list(set(nums) | set(add)))[:6]

    return sorted(nums)


def apply_strategy(game: str, tickets, strategy: str):
    if strategy == "blend":
        if game == "lotto":
            out = []
            for row in tickets:
                nudged = nudge_blend(row)
                # small nudge toward overdue cluster
                if random.random() < 0.25:
                    picks = set(nudged) | set(CLUSTER)
                    nudged = sorted(list(picks))[:6]
                out.append(nudged)
            return out
        return tickets
    elif strategy == "cold":
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
