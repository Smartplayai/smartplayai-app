# SmartPlayAI — infinity header, red lotto balls (number inside), pulse-on-select,
# auto-reset on game change, AI Suggest, Extended PDF report.

import streamlit as st
from fpdf import FPDF
from datetime import datetime
import random

st.set_page_config(page_title="SmartPlayAI", page_icon="🎯", layout="centered")

# ----------------------------- Config -----------------------------
GAMES = {
    "Jamaica Lotto":   {"main_range": 38, "main_picks": 6, "special": None},
    "Caribbean Super": {"main_range": 35, "main_picks": 5,
                        "special": {"range": 10, "picks": 1, "label": "Super Ball"}},
    "US Powerball":    {"main_range": 69, "main_picks": 5,
                        "special": {"range": 26, "picks": 1, "label": "Powerball"}},
}

def weighted_sample(n: int, k: int):
    mid = n / 2
    weights = [0.6 + abs((i + 1) - mid) / n for i in range(n)]
    total = sum(weights)
    picks = set()
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

# ------------------------- Session State --------------------------
ss = st.session_state
ss.setdefault("game", None)
ss.setdefault("last_game", None)
ss.setdefault("main_selected", set())
ss.setdefault("special_selected", set())

# ----------------------------- Styles -----------------------------
st.markdown("""
<style>
:root{
  --red:#d81324; --ring:#5a0a10; --white:#fff;
  --ease:cubic-bezier(.2,.8,.2,1);
}
.stApp, .main, .block-container{
  background: radial-gradient(1400px 900px at 20% -10%, #0b0e15 0%, #04060a 45%, #000 100%) !important;
  color:#fff;
}
.block-container{ max-width:880px; margin:0 auto !important; padding-top:12px; }
#MainMenu, footer{visibility:hidden}

/* Infinity symbol shows above the grid */
svg.infinity { filter: drop-shadow(0 10px 24px rgba(255,255,255,.14)); }

/* Lotto balls (label acts as the ball; checkbox hidden) */
.ball-row { display:flex; gap:8px; }
.ball-slot{
  display:flex; justify-content:center; align-items:center;
  width:70px; height:70px; flex:0 0 70px; position:relative;
}
.ball-check{ display:none; }
.ball-label{
  display:grid; place-items:center;
  width:70px; height:70px; border-radius:50%;
  font: 900 22px/1 system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--white);
  background: radial-gradient(circle at 30% 28%, #ff6b6b 0%, #e3162d 55%, #bf0d1f 100%);
  border: 4px solid var(--ring);
  box-shadow: 0 6px 14px rgba(0,0,0,.55), inset 0 6px 12px rgba(255,255,255,.23);
  cursor:pointer;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease), filter .18s var(--ease), color .18s var(--ease);
}
.ball-label:hover{ transform:translateY(-2px) scale(1.04); }

/* Selected: brighter, black numbers, white glow ring + pulse */
@keyframes selectPulse {
  0%   { transform: scale(0.96); box-shadow:
          0 10px 22px rgba(0,0,0,.65),
          0 0 0 0 rgba(255,255,255,1),
          inset 0 10px 18px rgba(255,255,255,.35); }
  55%  { transform: scale(1.10); box-shadow:
          0 16px 30px rgba(0,0,0,.8),
          0 0 0 14px rgba(255,255,255,.55),
          inset 0 12px 20px rgba(255,255,255,.45); }
  100% { transform: scale(1.08); box-shadow:
          0 12px 26px rgba(0,0,0,.75),
          0 0 0 6px rgba(255,255,255,.9),
          inset 0 10px 18px rgba(255,255,255,.35); }
}
.ball-check:checked + .ball-label{
  background: radial-gradient(circle at 32% 26%, #ffdede 0%, #ff3a43 50%, #b20b1c 100%);
  color: black;
  border-color: #fff;
  transform: scale(1.08);
  box-shadow:
    0 12px 26px rgba(0,0,0,.75),
    0 0 0 6px rgba(255,255,255,.9),
    inset 0 10px 18px rgba(255,255,255,.35);
  animation: selectPulse 900ms ease-out;
}

/* Hide Streamlit mirror checkboxes (state only) */
div[data-testid="stCheckbox"]{
  height:0!important; overflow:hidden!important; margin:0!important;
  padding:0!important; visibility:hidden!important;
}

/* Reduced motion accessibility */
@media (prefers-reduced-motion: reduce){
  .ball-label,
  .ball-check:checked + .ball-label{ transition:none !important; animation:none !important; }
}
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

# Infinity (joined zeros) — bright enough to show on dark bg
st.components.v1.html("""
<div style="display:flex;justify-content:center;margin-top:10px">
  <svg class="infinity" viewBox="0 0 1100 360" style="width:min(1100px,96vw);height:180px">
    <defs>
      <path id="centerline"
            d="M180,180 C300,40 460,40 550,180 C640,320 800,320 920,180
               C800,40 640,40 550,180 C460,320 300,320 180,180"/>
      <mask id="pinch">
        <rect x="0" y="0" width="1100" height="360" fill="white"/>
        <ellipse cx="550" cy="180" rx="38" ry="120" fill="black" transform="rotate(45 550 180)"/>
        <ellipse cx="550" cy="180" rx="38" ry="120" fill="black" transform="rotate(-45 550 180)"/>
      </mask>
      <linearGradient id="rbw" x1="0%" y1="50%" x2="100%" y2="50%">
        <stop offset="0%" stop-color="#ff2a4f"/>
        <stop offset="50%" stop-color="#ffffff"/>
        <stop offset="100%" stop-color="#0a3ca6"/>
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

if choice != ss.last_game:
    ss.last_game = choice
    ss.main_selected = set(); ss.special_selected = set()
    for k in list(ss.keys()):
        if k.endswith("_mirror"): ss.pop(k, None)
    ss.game = choice if choice != CHOOSER else None
    st.rerun()

# -------------------------- Number pickers -------------------------
if ss.game:
    cfg = GAMES[ss.game]

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
                with c:
                    st.markdown(
f"""
<div class="ball-slot">
  <input id="{prefix}_{n}" class="ball-check" type="checkbox" {'checked' if checked else ''} 
         onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));">
  <label class="ball-label" for="{prefix}_{n}">{n}</label>
</div>
""", unsafe_allow_html=True)
                    # Mirror state to Streamlit (hidden checkbox)
                    mirror = st.checkbox("", value=checked, key=f"{prefix}_{n}_mirror", label_visibility="collapsed")
                    if mirror and n not in selected_set:
                        if len(selected_set) >= max_picks:
                            first = sorted(selected_set)[0]
                            selected_set.remove(first)
                            ss.pop(f"{prefix}_{first}_mirror", None)
                        selected_set.add(n)
                    if not mirror and n in selected_set:
                        selected_set.remove(n)

    # main balls
    draw_row("main", cfg["main_range"], ss.main_selected, cfg["main_picks"])

    # special balls (if any)
    if cfg["special"]:
        st.markdown(
            f"<div style='text-align:center;margin:12px 0 6px;font-weight:800'>{cfg['special']['label']} "
            f"(pick {cfg['special']['picks']} of {cfg['special']['range']})</div>", unsafe_allow_html=True)
        draw_row("special", cfg["special"]["range"], ss.special_selected, cfg["special"]["picks"])

    # --------------------------- Actions ---------------------------
    left, mid, right = st.columns(3)
    with left:
        if st.button("AI Suggest"):
            main, special = suggest_for(ss.game)
            # clean mirror keys
            for k in list(ss.keys()):
                if k.endswith("_mirror"): ss.pop(k, None)
            ss.main_selected = set(main)
            for n in main: ss[f"main_{n}_mirror"] = True
            if cfg["special"]:
                ss.special_selected = set(special)
                for n in special: ss[f"special_{n}_mirror"] = True
            st.rerun()

    with mid:
        ext = st.toggle("Extended report", value=False, help="Adds analysis & a second page in the PDF.")

    with right:
        ready = (len(ss.main_selected) == cfg["main_picks"]) and (
            (not cfg["special"]) or (len(ss.special_selected) == cfg["special"]["picks"])
        )
        if st.button("Generate PDF", disabled=not ready):
            pdf_bytes = build_pdf(ss.game, sorted(ss.main_selected), sorted(ss.special_selected), extended=ext)
            st.download_button("Download Report", data=pdf_bytes, file_name="smartplayai_report.pdf", mime="application/pdf")

    # Status line
    st.markdown(
        f"<div style='text-align:center;opacity:.9;margin-top:10px;'>{ss.game}: "
        f"Main picks ({len(ss.main_selected)}/{cfg['main_picks']})"
        + (f" | {cfg['special']['label']} ({len(ss.special_selected)}/{cfg['special']['picks']})" if cfg['special'] else "")
        + "</div>", unsafe_allow_html=True
    )
else:
    st.info("Select a game from the dropdown to reveal the number grid and actions.")
