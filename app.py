# app.py
# SmartPlayAI – centered layout, top header with app name + tagline,
# clean joined-zeros infinity symbol, dropdown-driven UI, AI suggest & PDF.

import streamlit as st
from datetime import datetime
from fpdf import FPDF
import random

# -----------------------
# PAGE CONFIG
# -----------------------
st.set_page_config(page_title="SmartPlayAI", page_icon="🎯", layout="centered")

# -----------------------
# CONFIG & BACKGROUND HELPERS
# -----------------------
GAMES = {
    "Jamaica Lotto":   {"main_range": 38, "main_picks": 6, "special": None},
    "Caribbean Super": {"main_range": 35, "main_picks": 5, "special": {"range": 10, "picks": 1, "label": "Super Ball"}},
    "US Powerball":    {"main_range": 69, "main_picks": 5, "special": {"range": 26, "picks": 1, "label": "Powerball"}},
}

def weighted_sample(range_max: int, k: int):
    """Demo sampler (swap with your production AI)."""
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
    st.session_state.game = None
if "main_selected" not in st.session_state:
    st.session_state.main_selected = set()
if "special_selected" not in st.session_state:
    st.session_state.special_selected = set()
if "show_more_main" not in st.session_state:
    st.session_state.show_more_main = False
if "show_more_special" not in st.session_state:
    st.session_state.show_more_special = False
if "last_game_choice" not in st.session_state:
    st.session_state.last_game_choice = None

# -----------------------
# THEME CSS (centered + starfield + fixed balls + hide mirror checkboxes)
# -----------------------
st.markdown(
    """
    <style>
      :root{
        --flag-blue:#002868; --flag-red:#bf0a30; --white:#ffffff;
        --ease:cubic-bezier(.2,.8,.2,1);
      }
      .stApp, .main, .block-container {
        background: radial-gradient(1400px 900px at 20% -10%, #0b0e15 0%, #04060a 45%, #000 100%) !important;
        color: #fff !important;
      }
      .block-container{
        padding-top:16px; max-width: 880px; margin: 0 auto !important;
      }
      [data-testid="stVerticalBlock"]{ align-items:center; }
      #MainMenu, footer {visibility: hidden;}

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

      .hero-title{ font-size:48px; font-weight:900; margin-bottom:0; color:white; letter-spacing:1px; }
      .hero-tag{ font-size:22px; font-weight:600; color:#f7f7f7; text-shadow:0 0 8px rgba(255,255,255,0.25); }

      .ball-wrap{ display:flex; align-items:center; justify-content:center; width:64px; height:64px; flex:0 0 64px; }
      .ball{
        box-sizing:border-box; width:64px; height:64px; border-radius:50%;
        border:3.5px solid var(--flag-blue);
        background: radial-gradient(120% 120% at 30% 25%, #ffffff 0%, #f2f2f2 55%, #e1e1e1 100%);
        box-shadow: 0 8px 18px rgba(0,0,0,.35), 0 0 0 8px rgba(0,40,104,.12), inset 0 10px 18px rgba(0,0,0,.08);
        display:grid; place-items:center; cursor:pointer; position: relative;
        transition: transform .18s var(--ease), box-shadow .18s var(--ease), border-color .18s var(--ease);
      }
      .ball:hover{ transform: translateY(-2px) scale(1.04); border-color: var(--flag-red); }
      .ball:checked{
        border-color: var(--flag-blue);
        background: radial-gradient(120% 120% at 30% 25%, #ffffff 0%, #dfe9ff 55%, #c8daff 100%);
        box-shadow: 0 10px 26px rgba(0,0,0,.55), 0 0 0 12px rgba(0,40,104,.12), inset 0 10px 16px rgba(255,255,255,.35);
      }
      .ball-label{ position:absolute; inset:0; display:grid; place-items:center; font-weight:900; color: var(--flag-blue); }
      .ball:checked + .ball-label{ color:#0b1020; }

      /* Hide mirror checkboxes completely */
      div[data-testid="stCheckbox"]{ height:0!important; overflow:hidden!important; margin:0!important; padding:0!important; visibility:hidden!important; }

      .stButton > button { border-radius: 999px; padding: 12px 20px; font-weight: 900; }
      .btn-primary > button{ background: linear-gradient(180deg, var(--flag-red), #e11c3f); color:#fff; border:0; }
      .btn-secondary > button{ background: rgba(255,255,255,.08); color:#fff; border:1px solid rgba(255,255,255,.15); }
    </style>
    <div class="spa-stars"></div>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# HEADER: App Name + Tagline
# -----------------------
st.markdown(
    """
    <div style="text-align:center; margin-top:6px; position:relative; z-index:1;">
      <h1 class="hero-title">SmartPlay<span style="color:#ff2a4f;">AI</span></h1>
      <div style="margin-top:6px;">
        <span class="hero-tag">Let AI Unlock Your Next Big Win.</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# HEADER: Infinity (two joined zeros, thick, with center pinch)
# -----------------------
st.components.v1.html(
    """
    <div style="display:flex;justify-content:center;margin-top:12px; position:relative; z-index:1;">
      <svg viewBox="0 0 1100 360" style="width:min(1100px,96vw); height:360px; overflow:visible;">
        <defs>
          <!-- centerline curve -->
          <path id="centerline"
                d="M180,180
                   C300,40 460,40 550,180
                   C640,320 800,320 920,180
                   C800,40 640,40 550,180
                   C460,320 300,320 180,180" />

          <!-- mask that carves a slim waist at the crossing -->
          <mask id="pinchMask">
            <rect x="0" y="0" width="1100" height="360" fill="white"/>
            <!-- two rotated ellipses remove material to create the pinch -->
            <ellipse cx="550" cy="180" rx="38" ry="120" fill="black" transform="rotate(45 550 180)"/>
            <ellipse cx="550" cy="180" rx="38" ry="120" fill="black" transform="rotate(-45 550 180)"/>
          </mask>
        </defs>

        <!-- silhouette: change stroke to any color if desired -->
        <use href="#centerline"
             stroke="black" stroke-width="140"
             stroke-linecap="round" stroke-linejoin="round" fill="none"
             mask="url(#pinchMask)"/>
      </svg>
    </div>
    """,
    height=380,
)

# -----------------------
# GAME SELECTION (dropdown + lazy reveal)
# -----------------------
st.markdown("<div style='text-align:center;margin-top:-4px;'><h3>Select Your Game</h3></div>", unsafe_allow_html=True)

CHOOSER_LABEL = "— Select a game —"
game_choice = st.selectbox("Choose your game", [CHOOSER_LABEL] + list(GAMES.keys()), index=0, label_visibility="collapsed")

# Reset state when switching games or clearing selection
if game_choice != st.session_state.last_game_choice:
    st.session_state.last_game_choice = game_choice
    st.session_state.main_selected = set()
    st.session_state.special_selected = set()
    st.session_state.show_more_main = False
    st.session_state.show_more_special = False

# Only proceed if a real game is chosen
if game_choice != CHOOSER_LABEL:
    st.session_state.game = game_choice
    cfg = GAMES[st.session_state.game]

    # -----------------------
    # NUMBER GRID (only after game chosen)
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
                st.markdown(
                    f"""
                    <div class="ball-wrap">
                      <input type="checkbox" id="{key}" {'checked' if checked else ''} class="ball" onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));">
                      <label for="{key}" class="ball-label">{n}</label>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                # mirror state
                mirror = st.checkbox("", value=checked, key=f"{key}_mirror", label_visibility="collapsed")
                if mirror and n not in st.session_state.main_selected:
                    if len(st.session_state.main_selected) >= cfg["main_picks"]:
                        first = sorted(st.session_state.main_selected)[0]
                        st.session_state.main_selected.remove(first)
                        mk = f"main_{first}_mirror"
                        if mk in st.session_state: st.session_state[mk] = False
                    st.session_state.main_selected.add(n)
                if not mirror and n in st.session_state.main_selected:
                    st.session_state.main_selected.remove(n)

    # Show more / less
    cta_cols = st.columns([1,1,1])
    with cta_cols[1]:
        if cfg["main_range"] > preview:
            if not st.session_state.show_more_main:
                if st.button(f"Show {cfg['main_range'] - preview} more", key="main_more"):
                    st.session_state.show_more_main = True; st.rerun()
            else:
                if st.button("Show less", key="main_less"):
                    st.session_state.show_more_main = False; st.rerun()

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
                        st.session_state.show_more_special = True; st.rerun()
                else:
                    if st.button("Show less", key="sp_less"):
                        st.session_state.show_more_special = False; st.rerun()

    # -----------------------
    # ACTIONS (only after game chosen)
    # -----------------------
    a1, a2, a3 = st.columns(3)

    with a1:
        if st.button("AI Suggest", key="ai_suggest", help="Let SmartPlayAI choose a set"):
            main, special = suggest_for_game(st.session_state.game)
            # reset mirrors and apply picks
            for n in range(1, cfg["main_range"] + 1):
                mk = f"main_{n}_mirror"
                if mk in st.session_state: st.session_state[mk] = False
            st.session_state.main_selected = set(main)
            for n in main:
                st.session_state[f"main_{n}_mirror"] = True

            if cfg["special"]:
                for n in range(1, cfg["special"]["range"] + 1):
                    sk = f"special_{n}_mirror"
                    if sk in st.session_state: st.session_state[sk] = False
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

    # Status line
    st.markdown(
        f"""
        <div style="text-align:center;opacity:.85;margin-top:10px;">
          {st.session_state.game}: Main picks selected ({len(st.session_state.main_selected)}/{cfg['main_picks']})
          {(" | " + GAMES[st.session_state.game]["special"]["label"] + f" selected ({len(st.session_state.special_selected)}/{cfg['special']['picks']})") if cfg["special"] else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("Select a game from the dropdown to reveal the number grid and actions.")
