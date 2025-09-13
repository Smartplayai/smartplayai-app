# SmartPlayAI — infinity header, red lotto balls (limited picks), AI Suggest,
# Standard PDF (selection) + Premium Insights PDF (Hot/Warm/Cold + methodology)

import streamlit as st
from fpdf import FPDF
from datetime import datetime
import random
import math

st.set_page_config(page_title="SmartPlayAI", page_icon="🎯", layout="centered")

# ----------------------------- Config -----------------------------
GAMES = {
    "Jamaica Lotto":   {"main_range": 38, "main_picks": 6, "special": None},
    "Caribbean Super": {"main_range": 35, "main_picks": 5,
                        "special": {"range": 10, "picks": 1, "label": "Super Ball"}},
    "US Powerball":    {"main_range": 69, "main_picks": 5,
                        "special": {"range": 26, "picks": 1, "label": "Powerball"}},
}

PREMIUM_PASS = st.secrets.get("PASSCODE", "premium2025")

# ----------------------- Helpers / Suggestion ----------------------
def weighted_sample(n: int, k: int):
    """Simple demo weighting: mild bias toward mid/high values."""
    mid = n / 2
    weights = [0.6 + abs((i + 1) - mid) / n for i in range(n)]
    total = sum(weights)
    picks = set()
    # guard: if k > n
    k = min(k, n)
    while len(picks) < k:
        r = random.random() * total
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w
            if acc >= r:
                picks.add(i + 1)
                break
    return sorted(picks)

def suggest_for(game_key: str):
    c = GAMES[game_key]
    main = weighted_sample(c["main_range"], c["main_picks"])
    special = []
    if c["special"]:
        special = weighted_sample(c["special"]["range"], c["special"]["picks"])
    return main, special

# ------------------------- Trend Estimation ------------------------
def compute_trends(game_key: str, draws: int = 120, alpha: float = 0.97):
    """
    Demo 'hot/warm/cold' without external data: simulate recent draws with
    weighted_sample and compute an EWMA frequency. You can later plug in real
    history to replace this.
    """
    cfg = GAMES[game_key]
    N = cfg["main_range"]
    freq = {i: 0.0 for i in range(1, N + 1)}

    # Simulate draws and apply recency weight
    for d in range(draws):
        age = draws - 1 - d  # 0 = newest
        w = (alpha ** age)
        for v in weighted_sample(N, cfg["main_picks"]):
            freq[v] += w

    # Rank
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    # Buckets (18% hot, 18% cold, middle = warm) with minimum reasonable sizes
    hot_k = max(cfg["main_picks"], math.ceil(N * 0.18))
    cold_k = max(cfg["main_picks"], math.ceil(N * 0.18))
    hot = [x for x, _ in ranked[:hot_k]]
    cold = [x for x, _ in ranked[-cold_k:]]
    warm = [x for x, _ in ranked[hot_k:-cold_k]] if len(ranked) > hot_k + cold_k else []
    return {"hot": hot, "warm": warm, "cold": cold, "alpha": alpha, "draws": draws}

# ------------------------------ PDFs -------------------------------
def build_pdf(game, main, special, extended=False):
    c = GAMES[game]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "SmartPlayAI Number Report", ln=1, align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(
        0, 8,
        f"Game: {game}\n"
        f"Main Picks ({c['main_picks']} of {c['main_range']}): {', '.join(map(str, main)) if main else '—'}\n"
        + (f"{c['special']['label']}: {', '.join(map(str, special)) if special else '—'}\n" if c["special"] else "")
        + f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    if extended:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, "Extended Analysis", ln=1)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 7,
            "- Demo heuristic favors mid/high values slightly.\n"
            "- Replace with your production AI for real weights.\n"
            "- Selections are unique within each set.\n"
            f"- Export time: {datetime.now().strftime('%c')}")
        # quick visual row
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12); pdf.cell(0, 8, "Your Numbers", ln=1)
        def draw_row(title, arr):
            pdf.set_font("Helvetica", size=11); pdf.cell(28, 7, f"{title}:", border=0)
            for v in arr:
                pdf.cell(12, 7, str(v), border=1, align="C")
            pdf.ln(8)
        draw_row("Main", main)
        if c["special"]: draw_row(c["special"]["label"], special)
    return pdf.output(dest="S").encode("latin1")

def build_insights_pdf(game_key: str, trends: dict):
    """
    Premium Insights PDF: Hot / Warm / Cold + methodology + disclaimer.
    """
    game = game_key
    cfg = GAMES[game]
    hot = trends["hot"]; warm = trends["warm"]; cold = trends["cold"]
    alpha = trends["alpha"]; draws = trends["draws"]

    def chunk(lst, n=16):
        return [lst[i:i+n] for i in range(0, len(lst), n)]

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    # Page 1 — summary table
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "SmartPlayAI — Insights Report", ln=1, align="C")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Game: {game} • Computation window: last {draws} simulated draws • EWMA α = {alpha}", ln=1)

    # Hot/Warm/Cold sections
    def section(title, color_hex, values):
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(0,0,0)
        pdf.cell(0, 8, title, ln=1)
        pdf.set_draw_color(200,200,200)
        pdf.set_font("Helvetica", size=11)
        rows = chunk(values, 16)
        for row in rows:
            line = ", ".join(f"{v:02d}" for v in row)
            pdf.cell(0, 7, line, ln=1)
    section("🔥 Hot (recently frequent)", "#e74c3c", hot)
    section("🌤️ Warm (mid cohort)", "#3498db", warm)
    section("🧊 Cold / Overdue (rare lately)", "#2ecc71", cold)

    # Page 2 — methodology & disclaimer
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Methodology & Notes", ln=1)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7,
        "- We estimate recency-weighted frequencies using an exponentially weighted moving average (EWMA).\n"
        f"- Parameters used: draws={draws}, alpha={alpha}. Hot/cold buckets are the top/bottom ~18% by score.\n"
        "- Replace this simulator with real historical draws for production-grade insights.\n"
        "- This report is for entertainment/analysis only and does not guarantee outcomes. 18+ Play responsibly."
    )
    return pdf.output(dest="S").encode("latin1")

# ------------------------- Session State --------------------------
ss = st.session_state
ss.setdefault("game", None)
ss.setdefault("last_game", None)
ss.setdefault("main_selected", set())
ss.setdefault("special_selected", set())

# ----------------------------- Styles -----------------------------
st.markdown("""
<style>
:root{ --red:#d81324; --ring:#5a0a10; --white:#fff; --ease:cubic-bezier(.2,.8,.2,1); }
.stApp, .main, .block-container{
  background: radial-gradient(1400px 900px at 20% -10%, #0b0e15 0%, #04060a 45%, #000 100%) !important;
  color:#fff;
}
.block-container{ max-width:880px; margin:0 auto !important; padding-top:12px; }
#MainMenu, footer{visibility:hidden}
svg.infinity { filter: drop-shadow(0 10px 24px rgba(255,255,255,.14)); }
.ball-row { display:flex; gap:8px; }
.ball-slot{ display:flex; justify-content:center; align-items:center; width:70px; height:70px; flex:0 0 70px; position:relative; }
.ball-check{ display:none; }
.ball-label{
  display:grid; place-items:center; width:70px; height:70px; border-radius:50%;
  font: 900 22px/1 system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--white);
  background: radial-gradient(circle at 30% 28%, #ff6b6b 0%, #e3162d 55%, #bf0d1f 100%);
  border: 4px solid var(--ring);
  box-shadow: 0 6px 14px rgba(0,0,0,.55), inset 0 6px 12px rgba(255,255,255,.23);
  cursor:pointer;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease), filter .18s var(--ease), color .18s var(--ease);
}
.ball-label:hover{ transform:translateY(-2px) scale(1.04); }
@keyframes selectPulse {
  0%{ transform: scale(0.96); box-shadow:0 10px 22px rgba(0,0,0,.65),0 0 0 0 rgba(255,255,255,1), inset 0 10px 18px rgba(255,255,255,.35); }
  55%{ transform: scale(1.10); box-shadow:0 16px 30px rgba(0,0,0,.8),0 0 0 14px rgba(255,255,255,.55), inset 0 12px 20px rgba(255,255,255,.45); }
  100%{ transform: scale(1.08); box-shadow:0 12px 26px rgba(0,0,0,.75),0 0 0 6px rgba(255,255,255,.9), inset 0 10px 18px rgba(255,255,255,.35); }
}
.ball-check:checked + .ball-label{
  background: radial-gradient(circle at 32% 26%, #ffdede 0%, #ff3a43 50%, #b20b1c 100%);
  color: black; border-color: #fff; transform: scale(1.08);
  box-shadow: 0 12px 26px rgba(0,0,0,.75), 0 0 0 6px rgba(255,255,255,.9), inset 0 10px 18px rgba(255,255,255,.35);
  animation: selectPulse 900ms ease-out;
}
div[data-testid="stCheckbox"]{ height:0!important; overflow:hidden!important; margin:0!important; padding:0!important; visibility:hidden!important; }
@media (prefers-reduced-motion: reduce){ .ball-label, .ball-check:checked + .ball-label{ transition:none !important; animation:none !important; } }
</style>
""", unsafe_allow_html=True)

# ----------------------------- Header -----------------------------
st.markdown("""
<div style="text-align:center">
  <h1 style="font-size:48px; font-weight:900; margin:0;">SmartPlay<span style="color:#ff2a4f;">AI</span></h1>
  <div style="font-size:22px; font-weight:700; color:#fff; text-shadow:0 0 12px rgba(255,255,255,.35);">
    Let AI Unlock Your Next Big Win.
  </div>
</div>
""", unsafe_allow_html=True)

st.components.v1.html("""
<div style="display:flex;justify-content:center;margin-top:10px">
  <svg class="infinity" viewBox="0 0 1100 360" style="width:min(1100px,96vw);height:180px">
    <defs>
      <path id="centerline" d="M180,180 C300,40 460,40 550,180 C640,320 800,320 920,180
               C800,40 640,40 550,180 C460,320 300,320 180,180"/>
      <mask id="pinch">
        <rect x="0" y="0" width="1100" height="360" fill="white"/>
        <ellipse cx="550" cy="180" rx="38" ry="120" fill="black" transform="rotate(45 550 180)"/>
        <ellipse cx="550" cy="180" rx="38" ry="120" fill="black" transform="rotate(-45 550 180)"/>
      </mask>
      <linearGradient id="rbw" x1="0%" y1="50%" x2="100%" y2="50%">
        <stop offset="0%" stop-color="#ff2a4f"/><stop offset="50%" stop-color="#ffffff"/><stop offset="100%" stop-color="#0a3ca6"/>
      </linearGradient>
    </defs>
    <use href="#centerline" stroke="url(#rbw)" stroke-width="140" stroke-linecap="round" stroke-linejoin="round"
         fill="none" mask="url(#pinch)"/>
  </svg>
</div>
""", height=200)

# ---------------------- Game select (auto reset) -------------------
CHOOSER = "— Select a game —"
choice = st.selectbox("Choose your game", [CHOOSER] + list(GAMES.keys()), index=0, label_visibility="collapsed")

# reset state on game change
if choice != st.session_state.get("last_game"):
    st.session_state.last_game = choice
    st.session_state.main_selected = set()
    st.session_state.special_selected = set()
    for k in list(st.session_state.keys()):
        if k.endswith("_mirror"): st.session_state.pop(k, None)
    st.session_state.game = choice if choice != CHOOSER else None
    st.rerun()

# -------------------------- Number pickers -------------------------
def enforce_limit(prefix: str, selected_set: set, max_picks: int, attempted: int):
    """
    If user tries to exceed the allowed amount, immediately revert that mirror
    checkbox to False and show a toast, preserving existing choices.
    """
    if len(selected_set) > max_picks:
        # remove the most recent attempted number
        if attempted is not None and attempted in selected_set:
            selected_set.remove(attempted)
            st.session_state[f"{prefix}_{attempted}_mirror"] = False
        st.toast(f"Limit reached: pick at most {max_picks}.", icon="⚠️")

if st.session_state.get("game"):
    cfg = GAMES[st.session_state.game]

    st.markdown("<div style='text-align:center;font-weight:800;font-size:22px;margin:6px 0 8px'>Select Your Numbers</div>", unsafe_allow_html=True)

    def draw_row(prefix, total, selected_set, max_picks):
        cols_per_row = 8
        rows = (total + cols_per_row - 1) // cols_per_row
        for r in range(rows):
            cols = st.columns(cols_per_row, gap="small")
            for i, c in enumerate(cols):
                n = r * cols_per_row + i + 1
                if n > total: continue
                checked = (n in selected_set)
                attempted = None
                with c:
                    st.markdown(
f"""
<div class="ball-slot">
  <input id="{prefix}_{n}" class="ball-check" type="checkbox" {'checked' if checked else ''} 
         onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));">
  <label class="ball-label" for="{prefix}_{n}">{n}</label>
</div>
""", unsafe_allow_html=True)
                    mirror = st.checkbox("", value=checked, key=f"{prefix}_{n}_mirror", label_visibility="collapsed")
                    if mirror and n not in selected_set:
                        selected_set.add(n)
                        attempted = n
                        enforce_limit(prefix, selected_set, max_picks, attempted)
                    if not mirror and n in selected_set:
                        selected_set.remove(n)

    # main balls
    draw_row("main", cfg["main_range"], st.session_state.main_selected, cfg["main_picks"])

    # special balls (if any)
    if cfg["special"]:
        st.markdown(
            f"<div style='text-align:center;margin:12px 0 6px;font-weight:800'>{cfg['special']['label']} "
            f"(pick {cfg['special']['picks']} of {cfg['special']['range']})</div>", unsafe_allow_html=True)
        draw_row("special", cfg["special"]["range"], st.session_state.special_selected, cfg["special"]["picks"])

    # --------------------------- Actions ---------------------------
    left, mid, right = st.columns(3)
    with left:
        if st.button("AI Suggest"):
            main, special = suggest_for(st.session_state.game)
            # clean mirror keys
            for k in list(st.session_state.keys()):
                if k.endswith("_mirror"): st.session_state.pop(k, None)
            st.session_state.main_selected = set(main)
            for n in main: st.session_state[f"main_{n}_mirror"] = True
            if cfg["special"]:
                st.session_state.special_selected = set(special)
                for n in special: st.session_state[f"special_{n}_mirror"] = True
            st.rerun()

    with mid:
        ext = st.toggle("Extended report", value=False, help="Adds analysis & a second page in the PDF.")

    with right:
        ready = (len(st.session_state.main_selected) == cfg["main_picks"]) and (
            (not cfg["special"]) or (len(st.session_state.special_selected) == cfg["special"]["picks"])
        )
        if st.button("Generate PDF", disabled=not ready):
            pdf_bytes = build_pdf(
                st.session_state.game,
                sorted(st.session_state.main_selected),
                sorted(st.session_state.special_selected),
                extended=ext
            )
            st.download_button("Download Report", data=pdf_bytes, file_name="smartplayai_report.pdf", mime="application/pdf")

    # Premium Insights
    st.markdown("---")
    pass_in = st.text_input("Premium passcode (for Insights report)", type="password", placeholder="Enter passcode")
    cols = st.columns([1,1,1])
    with cols[1]:
        if st.button("Generate Insights Report (Premium)"):
            if str(pass_in).strip() == str(PREMIUM_PASS):
                trends = compute_trends(st.session_state.game, draws=120, alpha=0.97)
                insights_pdf = build_insights_pdf(st.session_state.game, trends)
                st.success("Premium unlocked. Download below.")
                st.download_button(
                    "Download Insights PDF",
                    data=insights_pdf,
                    file_name="smartplayai_insights.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Invalid passcode.")

    # Status line
    st.markdown(
        f"<div style='text-align:center;opacity:.9;margin-top:10px;'>{st.session_state.game}: "
        f"Main picks ({len(st.session_state.main_selected)}/{cfg['main_picks']})"
        + (f" | {cfg['special']['label']} ({len(st.session_state.special_selected)}/{cfg['special']['picks']})" if cfg['special'] else "")
        + "</div>", unsafe_allow_html=True
    )
else:
    st.info("Select a game from the dropdown to reveal the number grid and actions.")
