# app.py
# SmartPlayAI – Streamlit app with USA-themed “wormhole infinity” header and clean number picker UI

import streamlit as st
from datetime import datetime
from fpdf import FPDF
import random

# -----------------------
# PAGE CONFIG
# -----------------------
st.set_page_config(page_title="SmartPlayAI", page_icon="🎯", layout="centered")

# -----------------------
# CONFIG & BACKGROUND HELPERS (not shown to users directly)
# -----------------------
GAMES = {
    "Jamaica Lotto":   {"main_range": 38, "main_picks": 6, "special": None},
    "Caribbean Super": {"main_range": 35, "main_picks": 5, "special": {"range": 10, "picks": 1, "label": "Super Ball"}},
    "US Powerball":    {"main_range": 69, "main_picks": 5, "special": {"range": 26, "picks": 1, "label": "Powerball"}},
}

def weighted_sample(range_max: int, k: int):
    """Slight bias to mid-high values (placeholder for your real model)."""
    mid = range_max / 2
    weights = [0.6 + abs((i + 1) - mid) / range_max for i in range(range_max)]
    total = sum(weights)
    picks = set()
    while len(picks) < k:
        r = random.random() * total
        acc = 0.0
        choice = 1
        for i, w in enumerate(weights):
            acc += w
            if acc >= r:
                choice = i + 1
                break
        picks.add(choice)
    return sorted(picks)

def suggest_for_game(game_key: str):
    cfg = GAMES[game_key]
    main = weighted_sample(cfg["main_range"], cfg["main_picks"])
    special = []
    if cfg["special"]:
        special = weighted_sample(cfg["special"]["range"], cfg["special"]["picks"])
    return main, special

def pdf_report(game_key: str, main_picks, special_picks):
    cfg = GAMES[game_key]
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=18)
    pdf.cell(0, 12, "SmartPlayAI Number Report", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", size=12)
    text = f"Game: {game_key}\n"
    text += f"Main Picks ({cfg['main_picks']} of {cfg['main_range']}): {', '.join(map(str, main_picks)) if main_picks else '—'}\n"
    if cfg["special"]:
        text += f"{cfg['special']['label']}: {', '.join(map(str, special_picks)) if special_picks else '—'}\n"
    text += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    text += "Notes: This is a demo report. Replace the suggestion logic with your production AI model."
    pdf.multi_cell(0, 8, text)
    return pdf.output(dest="S").encode("latin1")

# -----------------------
# SESSION STATE
# -----------------------
if "game" not in st.session_state:
    st.session_state.game = "US Powerball"
if "main_selected" not in st.session_state:
    st.session_state.main_selected = set()
if "special_selected" not in st.session_state:
    st.session_state.special_selected = set()
if "show_more_main" not in st.session_state:
    st.session_state.show_more_main = False
if "show_more_special" not in st.session_state:
    st.session_state.show_more_special = False

# -----------------------
# THEME CSS + STARFIELD + COMPONENT STYLES
# -----------------------
st.markdown(
    """
    <style>
      :root{
        --flag-blue:#002868; --flag-blue-bright:#0a3ca6;
        --flag-red:#bf0a30;  --flag-red-strong:#ff2a4f;
        --flag-white:#ffffff;
        --ease:cubic-bezier(.2,.8,.2,1);
      }
      /* Global background */
      .stApp, .main, .block-container {
        background: radial-gradient(1400px 900px at 20% -10%, #0b0e15 0%, #04060a 45%, #000 100%) !important;
        color: #fff !important;
      }
      /* Hide Streamlit menubar/footer for app-like polish */
      #MainMenu, footer {visibility: hidden;}
      /* Star field overlay */
      .spa-stars, .spa-stars:before, .spa-stars:after{
        content:""; position: fixed; inset: -10%; pointer-events:none; opacity:.28; z-index: 0;
        background:
          radial-gradient(2px 2px at 10% 20%, rgba(255,255,255,.95) 40%, transparent 41%),
          radial-gradient(2px 2px at 80% 30%, rgba(255,255,255,.8) 40%, transparent 41%),
          radial-gradient(1.5px 1.5px at 40% 60%, rgba(255,255,255,.6) 40%, transparent 41%),
          radial-gradient(1.5px 1.5px at 70% 80%, rgba(255,255,255,.6) 40%, transparent 41%);
        animation: spaTwinkle 9s linear infinite;
      }
      .spa-stars:before{ animation-duration:13s; opacity:.22; }
      .spa-stars:after{ animation-duration:17s; opacity:.18; }
      @keyframes spaTwinkle{ 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }

      /* Banner pill */
      .spa-banner {
        display: inline-flex; align-items:center; justify-content:center;
        padding: 14px 30px; border-radius: 999px;
        background: linear-gradient(180deg, #083382, var(--flag-blue));
        color: var(--flag-white); font-weight: 900; font-size: 38px; letter-spacing: .04em;
        text-transform: uppercase; box-shadow: 0 10px 40px rgba(0,40,104,.45), 0 0 0 10px rgba(255,255,255,.06);
      }

      /* Number balls (we build them as custom HTML inputs) */
      .ball-wrap{ display:flex; align-items:center; justify-content:center; }
      .ball {
        appearance: none;
        width: 58px; height: 58px; border-radius: 50%;
        border: 3.5px solid var(--flag-blue);
        background: radial-gradient(120% 120% at 30% 25%, #ffffff 0%, #f2f2f2 55%, #e1e1e1 100%);
        box-shadow: 0 8px 18px rgba(0,0,0,.35), 0 0 0 8px rgba(0,40,104,.12), inset 0 10px 18px rgba(0,0,0,.08);
        display:grid; place-items:center; cursor:pointer; position: relative;
        transition: transform .18s var(--ease), box-shadow .18s var(--ease), border-color .18s var(--ease);
      }
      .ball:hover{
        transform: translateY(-2px) scale(1.04);
        border-color: var(--flag-red);
        box-shadow: 0 10px 24px rgba(0,0,0,.45), 0 0 0 12px rgba(191,10,48,.18);
      }
      .ball:checked{
        border-color: var(--flag-blue);
        background: radial-gradient(120% 120% at 30% 25%, #ffffff 0%, #dfe9ff 55%, #c8daff 100%);
        box-shadow: 0 10px 26px rgba(0,0,0,.55), 0 0 0 12px rgba(0,40,104,.12), inset 0 10px 16px rgba(255,255,255,.35);
      }
      .ball-label{
        position:absolute; inset:0; display:grid; place-items:center;
        font-weight:900; color: var(--flag-blue);
      }
      .ball:checked + .ball-label{ color:#0b1020; }

      /* CTA buttons */
      .stButton > button {
        border-radius: 999px; padding: 12px 20px; font-weight: 900;
        box-shadow: 0 14px 40px rgba(191,10,48,.25);
      }
      .btn-primary > button{
        background: linear-gradient(180deg, var(--flag-red), #e11c3f); color: #fff; border:0;
      }
      .btn-secondary > button{
        background: rgba(255,255,255,.08); color:#fff; border:1px solid rgba(255,255,255,.15);
      }

      /* Tighten Streamlit container padding slightly */
      .block-container { padding-top: 16px; }
    </style>
    <div class="spa-stars"></div>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# ANIMATED WORMHOLE INFINITY HEADER (SVG)
# -----------------------
st.components.v1.html(
    """
    <div style="display:flex;justify-content:center;margin:8px 0 4px; position:relative; z-index:1;">
      <div class="spa-banner">LOTTERY</div>
    </div>
    <div style="display:flex;justify-content:center;margin-top:4px; position:relative; z-index:1;">
      <svg viewBox="0 0 1100 360" style="width:min(1100px,96vw); height:360px; overflow:visible;">
        <defs>
          <!-- rounder infinity -->
          <path id="path∞" d="M140,180 C240,60 360,60 500,180 C640,300 760,300 960,180 C760,60 640,60 500,180 C360,300 240,300 140,180Z" />
          <!-- tube gradients -->
          <linearGradient id="gradRB" x1="0%" y1="50%" x2="100%" y2="50%">
            <stop offset="0%"  stop-color="#bf0a30"/>
            <stop offset="48%" stop-color="#ff2a4f"/>
            <stop offset="52%" stop-color="#0a3ca6"/>
            <stop offset="100%" stop-color="#002868"/>
          </linearGradient>
          <linearGradient id="innerLight" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="rgba(255,255,255,.95)"/>
            <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
          </linearGradient>
          <filter id="outerGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="12" result="b"/>
            <feColorMatrix in="b" type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.85 0" result="m"/>
            <feBlend in="SourceGraphic" in2="m" mode="screen"/>
          </filter>
          <filter id="innerGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="7" result="b"/>
            <feComposite in="b" in2="SourceAlpha" operator="in" result="i"/>
            <feBlend in="SourceGraphic" in2="i" mode="screen"/>
          </filter>
          <!-- circular whirl paths for inner spin -->
          <path id="whirlL" d="M350,180 m-120,0 a120,120 0 1,0 240,0 a120,120 0 1,0 -240,0" />
          <path id="whirlR" d="M750,180 m-120,0 a120,120 0 1,0 240,0 a120,120 0 1,0 -240,0" />
        </defs>

        <!-- triple-thick glassy tube -->
        <use href="#path∞" stroke="url(#gradRB)" stroke-width="78" fill="none" stroke-linecap="round" stroke-linejoin="round" filter="url(#outerGlow)"/>
        <use href="#path∞" stroke="url(#gradRB)" stroke-width="66" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity=".9"/>
        <use href="#path∞" stroke="url(#innerLight)" stroke-width="40" fill="none" stroke-linecap="round" stroke-linejoin="round" filter="url(#innerGlow)" opacity=".85"/>

        <!-- flowing numbers along main infinity -->
        <g font-weight="900" font-size="22" fill="#ffffff" filter="url(#innerGlow)">
          <text>
            <textPath href="#path∞" startOffset="0%">
              1 2 3 4 5 6 7 8 9 0 • 1 2 3 4 5 6 7 8 9 0 • 1 2 3 4 5 6 7 8 9 0 • 1 2 3 4 5 6 7 8 9 0 •
              <animate attributeName="startOffset" values="0%;30%;0%" dur="12s" repeatCount="indefinite"/>
            </textPath>
          </text>
          <text opacity=".7">
            <textPath href="#path∞" startOffset="50%">
              0 9 8 7 6 5 4 3 2 1 • 0 9 8 7 6 5 4 3 2 1 • 0 9 8 7 6 5 4 3 2 1 •
              <animate attributeName="startOffset" values="50%;80%;50%" dur="14s" repeatCount="indefinite"/>
            </textPath>
          </text>
        </g>

        <!-- inner whirlwinds (counter-rotating) -->
        <g font-weight="900" font-size="18" fill="#ffffff">
          <text>
            <textPath href="#whirlL" startOffset="0%">1 2 3 4 5 6 7 8 9 0 • 1 2 3 4 5 6 7 8 9 0 •</textPath>
            <animateTransform attributeName="transform" type="rotate" from="0 350 180" to="360 350 180" dur="6s" repeatCount="indefinite"/>
          </text>
          <text opacity=".75">
            <textPath href="#whirlL" startOffset="50%">5 4 3 2 1 0 9 8 7 6 • 5 4 3 2 1 0 9 8 7 6 •</textPath>
            <animateTransform attributeName="transform" type="rotate" from="0 350 180" to="-360 350 180" dur="9s" repeatCount="indefinite"/>
          </text>
          <text>
            <textPath href="#whirlR" startOffset="0%">1 2 3 4 5 6 7 8 9 0 • 1 2 3 4 5 6 7 8 9 0 •</textPath>
            <animateTransform attributeName="transform" type="rotate" from="0 750 180" to="-360 750 180" dur="6.5s" repeatCount="indefinite"/>
          </text>
          <text opacity=".75">
            <textPath href="#whirlR" startOffset="50%">5 4 3 2 1 0 9 8 7 6 • 5 4 3 2 1 0 9 8 7 6 •</textPath>
            <animateTransform attributeName="transform" type="rotate" from="0 750 180" to="360 750 180" dur="10s" repeatCount="indefinite"/>
          </text>
        </g>
      </svg>
    </div>
    """,
    height=420,
)

# -----------------------
# GAME SELECTION (user-facing)
# -----------------------
st.markdown("<div style='text-align:center;margin-top:-8px;'><h3>Select Your Game</h3></div>", unsafe_allow_html=True)
game = st.radio(
    " ",
    list(GAMES.keys()),
    horizontal=True,
    label_visibility="collapsed",
    index=list(GAMES.keys()).index(st.session_state.game),
)
if game != st.session_state.game:
    st.session_state.game = game
    st.session_state.main_selected = set()
    st.session_state.special_selected = set()
    st.session_state.show_more_main = False
    st.session_state.show_more_special = False

cfg = GAMES[st.session_state.game]

# -----------------------
# NUMBER GRID (user-facing)
# -----------------------
st.markdown("<div style='text-align:center; margin: 6px 0 8px; font-weight: 800; font-size: 22px;'>Select Your Numbers</div>", unsafe_allow_html=True)

preview = min(28, cfg["main_range"])
show_count = cfg["main_range"] if st.session_state.show_more_main else preview
cols_per_row = 8
rows = (show_count + cols_per_row - 1) // cols_per_row

for r in range(rows):
    cols = st.columns(cols_per_row, gap="small")
    for i, c in enumerate(cols):
        n = r * cols_per_row + i + 1
        if n > show_count:
            continue
        key = f"main_{n}"
        checked = (n in st.session_state.main_selected)
        with c:
            # Render a visually styled ball (HTML input) and a hidden Streamlit checkbox to mirror state
            st.markdown(
                f"""
                <div class="ball-wrap">
                  <input type="checkbox" id="{key}" {'checked' if checked else ''} class="ball" onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));">
                  <label for="{key}" class="ball-label">{n}</label>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Hidden mirror checkbox captures state changes for Streamlit
            mirror = st.checkbox("", value=checked, key=f"{key}_mirror", label_visibility="collapsed")
            if mirror and n not in st.session_state.main_selected:
                # limit to max picks: remove oldest
                if len(st.session_state.main_selected) >= cfg["main_picks"]:
                    first = sorted(st.session_state.main_selected)[0]
                    st.session_state.main_selected.remove(first)
                    mk = f"main_{first}_mirror"
                    if mk in st.session_state: st.session_state[mk] = False
                st.session_state.main_selected.add(n)
            if not mirror and n in st.session_state.main_selected:
                st.session_state.main_selected.remove(n)

# Show more / less controls
cta_cols = st.columns([1,1,1])
with cta_cols[1]:
    if cfg["main_range"] > preview:
        if not st.session_state.show_more_main:
            if st.button(f"Show {cfg['main_range'] - preview} more", key="main_more", help="Reveal the full number range"):
                st.session_state.show_more_main = True
                st.rerun()
        else:
            if st.button("Show less", key="main_less"):
                st.session_state.show_more_main = False
                st.rerun()

# Special ball section
if cfg["special"]:
    st.markdown(
        f"<div style='text-align:center; margin: 12px 0 6px; font-weight: 800;'>"
        f"{cfg['special']['label']} (pick {cfg['special']['picks']} of {cfg['special']['range']})</div>",
        unsafe_allow_html=True,
    )
    sp_preview = min(28, cfg["special"]["range"])
    sp_show_count = cfg["special"]["range"] if st.session_state.show_more_special else sp_preview
    rows = (sp_show_count + cols_per_row - 1) // cols_per_row
    for r in range(rows):
        cols = st.columns(cols_per_row, gap="small")
        for i, c in enumerate(cols):
            n = r * cols_per_row + i + 1
            if n > sp_show_count:
                continue
            key = f"special_{n}"
            checked = (n in st.session_state.special_selected)
            with c:
                st.markdown(
                    f"""
                    <div class="ball-wrap">
                      <input type="checkbox" id="{key}" {'checked' if checked else ''} class="ball" onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));">
                      <label for="{key}" class="ball-label">{n}</label>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # mirror to state (limit to exactly cfg['special']['picks'])
                mirror = st.checkbox("", value=checked, key=f"{key}_mirror", label_visibility="collapsed")
                if mirror and n not in st.session_state.special_selected:
                    if len(st.session_state.special_selected) >= cfg["special"]["picks"]:
                        first = next(iter(st.session_state.special_selected))
                        st.session_state.special_selected.remove(first)
                        sk = f"special_{first}_mirror"
                        if sk in st.session_state: st.session_state[sk] = False
                    st.session_state.special_selected.add(n)
                if not mirror and n in st.session_state.special_selected:
                    st.session_state.special_selected.remove(n)

    with cta_cols[1]:
        if cfg["special"]["range"] > sp_preview:
            if not st.session_state.show_more_special:
                if st.button(f"Show {cfg['special']['range'] - sp_preview} more", key="sp_more"):
                    st.session_state.show_more_special = True
                    st.rerun()
            else:
                if st.button("Show less", key="sp_less"):
                    st.session_state.show_more_special = False
                    st.rerun()

# -----------------------
# ACTIONS (user-facing)
# -----------------------
a1, a2, a3 = st.columns(3)

with a1:
    if st.button("AI Suggest", key="ai_suggest", help="Let SmartPlayAI choose a set"):
        main, special = suggest_for_game(st.session_state.game)

        # reset mirrors
        for n in range(1, cfg["main_range"] + 1):
            mk = f"main_{n}_mirror"
            if mk in st.session_state:
                st.session_state[mk] = False
        st.session_state.main_selected = set(main)
        for n in main:
            st.session_state[f"main_{n}_mirror"] = True

        if cfg["special"]:
            for n in range(1, cfg["special"]["range"] + 1):
                sk = f"special_{n}_mirror"
                if sk in st.session_state:
                    st.session_state[sk] = False
            st.session_state.special_selected = set(special)
            for n in special:
                st.session_state[f"special_{n}_mirror"] = True

        st.success(f"AI Suggested {main}" + (f" | {cfg['special']['label']}: {special}" if cfg["special"] else ""))
        st.rerun()

with a2:
    if st.button("Submit", key="submit", help="Validate your selection"):
        errors = []
        if len(st.session_state.main_selected) != cfg["main_picks"]:
            errors.append(f"Pick exactly {cfg['main_picks']} main numbers.")
        if cfg["special"] and len(st.session_state.special_selected) != cfg["special"]["picks"]:
            errors.append(f"Pick exactly {cfg['special']['picks']} {cfg['special']['label']}.")
        if errors:
            st.error(" ".join(errors))
        else:
            st.success("Selection looks good! You can generate your PDF report below.")

with a3:
    ready = (len(st.session_state.main_selected) == cfg["main_picks"]) and (
        (not cfg["special"]) or (len(st.session_state.special_selected) == cfg["special"]["picks"])
    )
    if st.button("Generate PDF", key="pdf", help="Download your selection as a PDF", disabled=not ready):
        pdf_bytes = pdf_report(
            st.session_state.game,
            sorted(st.session_state.main_selected),
            sorted(st.session_state.special_selected),
        )
        st.download_button(
            "Download Report",
            data=pdf_bytes,
            file_name="smartplayai_report.pdf",
            mime="application/pdf",
        )

# META LINE
st.markdown(
    f"""
    <div style="text-align:center;opacity:.85;margin-top:10px;">
      {st.session_state.game}: Main picks selected ({len(st.session_state.main_selected)}/{cfg['main_picks']})
      {(" | " + GAMES[st.session_state.game]["special"]["label"] + f" selected ({len(st.session_state.special_selected)}/{cfg['special']['picks']})") if cfg["special"] else ""}
    </div>
    """,
    unsafe_allow_html=True,
)

