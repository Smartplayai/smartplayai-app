# app.py
import streamlit as st
from datetime import datetime
from fpdf import FPDF
import random

st.set_page_config(page_title="SmartPlayAI", page_icon="🎯", layout="centered")

# --- CONFIG ---
GAMES = {
    "Jamaica Lotto":   {"main_range": 38, "main_picks": 6, "special": None},
    "Caribbean Super": {"main_range": 35, "main_picks": 5,
                        "special": {"range": 10, "picks": 1, "label": "Super Ball"}},
    "US Powerball":    {"main_range": 69, "main_picks": 5,
                        "special": {"range": 26, "picks": 1, "label": "Powerball"}},
}

def weighted_sample(range_max: int, k: int):
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
    pdf.multi_cell(0, 8, text)
    return pdf.output(dest="S").encode("latin1")

# --- SESSION STATE ---
if "game" not in st.session_state:
    st.session_state.game = None
if "main_selected" not in st.session_state:
    st.session_state.main_selected = set()
if "special_selected" not in st.session_state:
    st.session_state.special_selected = set()
if "last_game_choice" not in st.session_state:
    st.session_state.last_game_choice = None

# --- CSS: Lotto Ball Look ---
st.markdown("""
<style>
:root {
  --red:#d90000; --blue:#002868;
}
.ball-wrap {
  display:flex; align-items:center; justify-content:center;
  width:70px; height:70px; flex:0 0 70px;
}
.ball-input {
  appearance:none; -webkit-appearance:none;
  width:70px; height:70px; border-radius:50%;
  border:3px solid var(--blue);
  background: radial-gradient(circle at 30% 25%, #fff 0%, #f2f2f2 60%, #dcdcdc 100%);
  box-shadow: 0 4px 10px rgba(0,0,0,.35), inset 0 5px 10px rgba(0,0,0,.08);
  display:flex; align-items:center; justify-content:center;
  font-weight:900; font-size:22px; color:var(--red);
  cursor:pointer; transition:all .2s ease;
}
.ball-input:checked {
  background: radial-gradient(circle at 30% 25%, #fff 0%, #dde9ff 70%, #c4d5ff 100%);
  box-shadow: 0 6px 14px rgba(0,0,0,.55), inset 0 4px 10px rgba(255,255,255,.4);
  transform: scale(1.08);
  color:#8d0000;
}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("""
<div style="text-align:center; margin-top:6px;">
  <h1 style="font-size:48px; font-weight:900;">SmartPlay<span style="color:#ff2a4f;">AI</span></h1>
  <p style="font-size:22px; font-weight:600;">Let AI Unlock Your Next Big Win.</p>
</div>
""", unsafe_allow_html=True)

# --- GAME SELECT + AUTO RESET ---
CHOOSER_LABEL = "— Select a game —"
game_choice = st.selectbox("Choose your game", [CHOOSER_LABEL] + list(GAMES.keys()), index=0, label_visibility="collapsed")

if game_choice != st.session_state.last_game_choice:
    st.session_state.last_game_choice = game_choice
    st.session_state.main_selected = set()
    st.session_state.special_selected = set()
    for k in list(st.session_state.keys()):
        if k.endswith("_mirror"):
            st.session_state.pop(k, None)
    st.session_state.game = game_choice if game_choice != CHOOSER_LABEL else None
    st.rerun()

if st.session_state.game:
    cfg = GAMES[st.session_state.game]

    # --- MAIN BALLS ---
    cols_per_row = 8
    total = cfg["main_range"]
    rows = (total + cols_per_row - 1) // cols_per_row

    for r in range(rows):
        cols = st.columns(cols_per_row)
        for i, c in enumerate(cols):
            n = r * cols_per_row + i + 1
            if n > total:
                continue
            with c:
                checked = (n in st.session_state.main_selected)
                html = f"""
                <div class="ball-wrap">
                  <input type="checkbox" class="ball-input" id="main_{n}" {'checked' if checked else ''} 
                    onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));" />
                  <label for="main_{n}">{n}</label>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
                mirror = st.checkbox("", value=checked, key=f"main_{n}_mirror", label_visibility="collapsed")
                if mirror and n not in st.session_state.main_selected:
                    if len(st.session_state.main_selected) >= cfg["main_picks"]:
                        first = sorted(st.session_state.main_selected)[0]
                        st.session_state.main_selected.remove(first)
                        st.session_state.pop(f"main_{first}_mirror", None)
                    st.session_state.main_selected.add(n)
                if not mirror and n in st.session_state.main_selected:
                    st.session_state.main_selected.remove(n)

    # --- SPECIAL BALLS ---
    if cfg["special"]:
        st.markdown(f"<h4 style='text-align:center;'>{cfg['special']['label']}</h4>", unsafe_allow_html=True)
        total = cfg["special"]["range"]
        rows = (total + cols_per_row - 1) // cols_per_row
        for r in range(rows):
            cols = st.columns(cols_per_row)
            for i, c in enumerate(cols):
                n = r * cols_per_row + i + 1
                if n > total:
                    continue
                with c:
                    checked = (n in st.session_state.special_selected)
                    html = f"""
                    <div class="ball-wrap">
                      <input type="checkbox" class="ball-input" id="special_{n}" {'checked' if checked else ''} 
                        onclick="this.dispatchEvent(new Event('change', {{bubbles:true}}));" />
                      <label for="special_{n}">{n}</label>
                    </div>
                    """
                    st.markdown(html, unsafe_allow_html=True)
                    mirror = st.checkbox("", value=checked, key=f"special_{n}_mirror", label_visibility="collapsed")
                    if mirror and n not in st.session_state.special_selected:
                        if len(st.session_state.special_selected) >= cfg["special"]["picks"]:
                            first = next(iter(st.session_state.special_selected))
                            st.session_state.special_selected.remove(first)
                            st.session_state.pop(f"special_{first}_mirror", None)
                        st.session_state.special_selected.add(n)
                    if not mirror and n in st.session_state.special_selected:
                        st.session_state.special_selected.remove(n)

    # --- BUTTONS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("AI Suggest"):
            main, special = suggest_for_game(st.session_state.game)
            for k in list(st.session_state.keys()):
                if k.endswith("_mirror"):
                    st.session_state.pop(k, None)
            st.session_state.main_selected = set(main)
            for n in main:
                st.session_state[f"main_{n}_mirror"] = True
            if cfg["special"]:
                st.session_state.special_selected = set(special)
                for n in special:
                    st.session_state[f"special_{n}_mirror"] = True
            st.rerun()
    with c2:
        st.button("Submit")
    with c3:
        ready = (len(st.session_state.main_selected) == cfg["main_picks"]) and (
            (not cfg["special"]) or (len(st.session_state.special_selected) == cfg["special"]["picks"])
        )
        if st.button("Generate PDF", disabled=not ready):
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
