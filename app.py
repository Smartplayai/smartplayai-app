# SmartPlayAI — Premium, polished Streamlit app
# UX: onboarding, age-gate, strict limits, freemium, Premium Insights PDF,
# Unicode-safe PDFs, health score, live next-draw countdown, sidebar mini-calendar + ICS,
# compliance footer with policy links.

import streamlit as st
from fpdf import FPDF
from datetime import datetime, date, timedelta
import random, math, json, hashlib
from typing import List, Dict
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # fallback if not available

st.set_page_config(page_title="SmartPlayAI", page_icon="🎯", layout="centered")

# ----------------------------- Config -----------------------------
GAMES = {
    "Jamaica Lotto": {
        "main_range": 38, "main_picks": 6, "special": None
    },
    "Caribbean Super Lotto": {
        "main_range": 35, "main_picks": 5,
        "special": {"range": 10, "picks": 1, "label": "Super Ball"}
    },
    "US Powerball": {
        "main_range": 69, "main_picks": 5,
        "special": {"range": 26, "picks": 1, "label": "Powerball"}
    },
}

# Secrets (safe defaults provided)
PREMIUM_PASS     = st.secrets.get("PASSCODE", "premium2025")
RUNS_PER_DAY     = int(st.secrets.get("RUNS_PER_DAY", 20))  # free runs/day/session
RESP_HELP        = st.secrets.get("RESPONSIBLE_HELP", "If gambling is affecting you, seek local support resources.")
BRAND_URL        = st.secrets.get("BRAND_URL", "https://smartplayai.example.com")
SHOW_ONBOARDING  = bool(st.secrets.get("SHOW_ONBOARDING", True))

# Timezone & draw schedules (override in Secrets)
APP_TZ = st.secrets.get("TIMEZONE", "America/Jamaica")
TZ = ZoneInfo(APP_TZ) if ZoneInfo else None

def wdays(val, default):
    if not val: return default
    try:
        out = [int(x.strip()) for x in str(val).split(",") if x.strip()!=""]
        return [d for d in out if 0<=d<=6] or default
    except: return default

# Mon=0..Sun=6
LOTTO_WD     = wdays(st.secrets.get("LOTTO_DRAW_WEEKDAYS", "2,5"), [2,5])            # Wed, Sat
SUPER_WD     = wdays(st.secrets.get("SUPER_DRAW_WEEKDAYS", "1,4"), [1,4])            # Tue, Fri
POWERBALL_WD = wdays(st.secrets.get("POWERBALL_DRAW_WEEKDAYS", "0,2,5"), [0,2,5])    # Mon, Wed, Sat

LOTTO_TIME     = st.secrets.get("LOTTO_DRAW_TIME", "20:30")       # local time (HH:MM)
SUPER_TIME     = st.secrets.get("SUPER_DRAW_TIME", "20:30")
POWERBALL_TIME = st.secrets.get("POWERBALL_DRAW_TIME", "22:59")

def get_weekdays_and_time(game: str):
    if game == "Jamaica Lotto":
        return LOTTO_WD, LOTTO_TIME
    if game == "Caribbean Super Lotto":
        return SUPER_WD, SUPER_TIME
    if game == "US Powerball":
        return POWERBALL_WD, POWERBALL_TIME
    return [2,5], "20:30"

def next_draw_datetime(game: str):
    wds, tstr = get_weekdays_and_time(game)
    hh, mm = [int(x) for x in tstr.split(":")]
    now = datetime.now(TZ) if TZ else datetime.now()
    candidates = []
    for wd in wds:
        delta = (wd - now.weekday()) % 7
        dt = (now + timedelta(days=delta)).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=7)
        candidates.append(dt)
    return min(candidates) if candidates else (now + timedelta(days=1))

# ---------- Draw calendars & ICS helpers ----------
def get_next_k_draws(game: str, k: int = 4):
    """Return the next k draw datetimes for a given game."""
    wds, tstr = get_weekdays_and_time(game)
    hh, mm = [int(x) for x in tstr.split(":")]
    now = datetime.now(TZ) if TZ else datetime.now()
    out = []
    d = now
    while len(out) < k:
        if d.weekday() in wds:
            dt = d.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if dt >= now:
                out.append(dt)
        d += timedelta(days=1)
    return out

def _ics_dt(dt: datetime) -> str:
    # Floating local time format (calendar apps will treat as local time)
    return dt.strftime("%Y%m%dT%H%M%S")

def build_ics_for_all(next_n: int = 8) -> bytes:
    """Build a simple multi-event ICS file for all games (next_n events each)."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//SmartPlayAI//Draw Calendar//EN"
    ]
    nowstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    for game in GAMES.keys():
        draws = get_next_k_draws(game, k=min(next_n, 10))
        for dt in draws:
            dtstart = _ics_dt(dt)
            dtend   = _ics_dt(dt + timedelta(minutes=30))
            uid = hashlib.sha1(f"{game}-{dt.isoformat()}".encode()).hexdigest()[:16]
            lines += [
                "BEGIN:VEVENT",
                f"UID:{uid}@smartplay.ai",
                f"DTSTAMP:{nowstamp}",
                f"SUMMARY:{game} Draw",
                f"DESCRIPTION:Next scheduled draw for {game} (SmartPlayAI).",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                "END:VEVENT"
            ]

    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines)).encode("utf-8")

# -------------------------- Session State -------------------------
ss = st.session_state
ss.setdefault("onboarding_dismissed", False)
ss.setdefault("age_confirmed", False)
ss.setdefault("runs_log", [])  # timestamps (seconds)
ss.setdefault("game", None)
ss.setdefault("last_game", None)
ss.setdefault("main_selected", set())
ss.setdefault("special_selected", set())

# ------------------------------ Styles ----------------------------
st.markdown("""
<style>
:root{ --red:#ff2a4f; --ring:#5a0a10; --white:#fff; --ease:cubic-bezier(.2,.8,.2,1); }
.stApp, .main, .block-container{
  background: radial-gradient(1400px 900px at 20% -10%, #0b0e15 0%, #04060a 45%, #000 100%) !important;
  color:#fff;
}
.block-container{ max-width:880px; margin:0 auto !important; padding-top:12px; }
#MainMenu, footer{visibility:hidden}
svg.infinity { filter: drop-shadow(0 10px 24px rgba(255,255,255,.14)); }
.ball-slot{ display:flex; justify-content:center; align-items:center; width:70px; height:70px; flex:0 0 70px; position:relative; }
.ball-check{ display:none; }
.ball-label{
  display:grid; place-items:center; width:70px; height:70px; border-radius:50%;
  font: 900 22px/1 system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: var(--white);
  background: radial-gradient(circle at 30% 28%, #ff6b6b 0%, var(--red) 55%, #b20b1c 100%);
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
a.brand { color:var(--red); text-decoration:none; }
.stButton>button { background-color: var(--red); color:#fff; border-radius:10px; font-weight:800; border:0; }
.timer-pill{
  display:inline-flex; gap:10px; align-items:center;
  padding:10px 14px; border:1px solid rgba(255,255,255,.18);
  border-radius:999px; background:rgba(255,255,255,.06);
  backdrop-filter: blur(6px); color:#fff; font-weight:700;
}
.timer-seg{ padding:6px 10px; border-radius:10px;
  background:rgba(0,0,0,.35); min-width:64px; text-align:center; }
.timer-lab{ font-weight:600; opacity:.85; margin-left:8px;}
</style>
""", unsafe_allow_html=True)

# ------------------------------- Header ---------------------------
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

# ----------------------------- Onboarding -------------------------
if SHOW_ONBOARDING and not ss.onboarding_dismissed:
    with st.expander("✨ Quick Start (60 sec) — How to use SmartPlayAI", expanded=True):
        st.markdown("""
        1. **Choose your game** below.  
        2. **Tap numbers** (we strictly limit picks to the game's rules).  
        3. Click **AI Suggest** to auto-pick within limits.  
        4. Generate a **PDF Report** (free) or **Insights** (premium) with hot/warm/cold.  
        """)
        if st.button("Got it, hide this"): ss.onboarding_dismissed = True; st.rerun()

# ------------------------------- Age Gate -------------------------
st.checkbox("I am 18+ and I agree to use SmartPlayAI for entertainment/analysis. (Required)", key="age_confirmed")
if not ss.age_confirmed:
    st.warning("Please confirm you are 18+ to continue.")
    st.stop()

# ---------------------- Game select (auto reset) ------------------
CHOOSER = "— Select a game —"
choice = st.selectbox("Choose your game", [CHOOSER] + list(GAMES.keys()), index=0, label_visibility="collapsed")

if choice != ss.get("last_game"):
    ss.last_game = choice
    ss.main_selected = set()
    ss.special_selected = set()
    for k in list(ss.keys()):
        if k.endswith("_mirror"): ss.pop(k, None)
    ss.game = choice if choice != CHOOSER else None
    st.rerun()

# ----------------------- Helper: picks & trends -------------------
def weighted_sample(n: int, k: int):
    mid = n / 2
    weights = [0.6 + abs((i + 1) - mid) / n for i in range(n)]
    total = sum(weights)
    picks = set()
    k = min(k, n)
    while len(picks) < k:
        r = random.random() * total
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w
            if acc >= r:
                picks.add(i + 1); break
    return sorted(picks)

def suggest_for(game_key: str):
    c = GAMES[game_key]
    main = weighted_sample(c["main_range"], c["main_picks"])
    special = []
    if c["special"]:
        special = weighted_sample(c["special"]["range"], c["special"]["picks"])
    return main, special

@st.cache_data(ttl=3600)
def compute_trends(game_key: str, draws: int = 120, alpha: float = 0.97) -> Dict:
    cfg = GAMES[game_key]; N = cfg["main_range"]
    freq = {i: 0.0 for i in range(1, N + 1)}
    for d in range(draws):
        age = draws - 1 - d; w = (alpha ** age)
        for v in weighted_sample(N, cfg["main_picks"]):
            freq[v] += w
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    hot_k  = max(cfg["main_picks"], math.ceil(N * 0.18))
    cold_k = max(cfg["main_picks"], math.ceil(N * 0.18))
    hot  = [x for x,_ in ranked[:hot_k]]
    cold = [x for x,_ in ranked[-cold_k:]]
    warm = [x for x,_ in ranked[hot_k:-cold_k]] if len(ranked) > hot_k+cold_k else []
    return {"hot": hot, "warm": warm, "cold": cold, "alpha": alpha, "draws": draws}

def ticket_health(nums: List[int], hot: List[int], cold: List[int]) -> int:
    if not nums: return 0
    hot_count = sum(1 for n in nums if n in hot)
    cold_count = sum(1 for n in nums if n in cold)
    even = sum(1 for n in nums if n % 2 == 0)
    score = 0
    score += min(hot_count, 2) * 15
    score += min(cold_count, 2) * 15
    score += (10 if 2 <= even <= 4 else 0)
    total = sum(nums)
    score += (10 if 80 <= total <= 180 else 0)
    return min(100, score)

def verification_code(game: str, seed: int, params: dict) -> str:
    payload = json.dumps({"g":game,"s":seed,"p":params}, sort_keys=True).encode()
    return hashlib.sha1(payload).hexdigest()[:10].upper()

# ------------------------------ PDFs ------------------------------
def build_pdf(game, main, special, meta: dict):
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
        + f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        + f"Verification Code: {meta.get('vcode','')}"
    )
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(120,120,120)
    pdf.multi_cell(0, 6, f"Analytics only • No guaranteed outcomes • 18+ • {RESP_HELP}")
    return pdf.output(dest="S").encode("latin1", errors="ignore")  # Unicode-safe

def build_insights_pdf(game_key: str, trends: dict, main: List[int], seed: int, meta: dict):
    game = game_key
    hot, warm, cold = trends["hot"], trends["warm"], trends["cold"]
    alpha, draws = trends["alpha"], trends["draws"]

    def chunk(lst, n=16):
        return [lst[i:i+n] for i in range(0, len(lst), n)]

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    # Page 1 — summary table
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "SmartPlayAI — Insights Report", ln=1, align="C")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Game: {game} • Window: last {draws} simulated draws • EWMA alpha={alpha} • Seed={seed} • Code={meta.get('vcode','')}", ln=1)

    def section(title, values):
        pdf.ln(3); pdf.set_font("Helvetica", "B", 13); pdf.cell(0, 8, title, ln=1)
        pdf.set_font("Helvetica", size=11)
        for row in chunk(values, 18):
            pdf.cell(0, 7, ", ".join(f"{v:02d}" for v in row), ln=1)

    section("Hot (recently frequent)", hot)
    section("Warm (mid cohort)", warm)
    section("Cold / Overdue (rare lately)", cold)

    # Page 2 — methodology & ticket health
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Methodology & Notes", ln=1)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 7,
        "- We estimate recency-weighted frequencies using an exponentially weighted moving average (EWMA).\n"
        f"- Parameters: draws={draws}, alpha={alpha}. Hot/Cold = top/bottom ~18% by score; middle = Warm.\n"
        "- Replace simulator with real historical draws to upgrade insight quality.\n"
        "- This report is for entertainment/analysis only and does not guarantee outcomes. 18+ Play responsibly."
    )
    # Ticket health
    pdf.ln(4); pdf.set_font("Helvetica", "B", 14); pdf.cell(0, 8, "Ticket Health", ln=1)
    score = ticket_health(main, hot, cold)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 7, f"Your current main selection: {', '.join(map(str, main))}  →  Health Score: {score}/100", ln=1)

    return pdf.output(dest="S").encode("latin1", errors="ignore")  # Unicode-safe

# ------------------------- Freemium rate limit --------------------
def can_run(log: list, limit: int, window_s: int = 24*3600) -> bool:
    now = datetime.utcnow().timestamp()
    recent = [t for t in log if now - t <= window_s]
    if len(recent) >= limit:
        ss.runs_log = recent  # clean old
        return False
    recent.append(now); ss.runs_log = recent
    return True

# -------------------------- Number pickers ------------------------
def draw_row(prefix, total, selected_set, max_picks):
    # Safe & simple; Streamlit wraps responsively.
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
                    selected_set.add(n); attempted = n
                    if len(selected_set) > max_picks:
                        selected_set.remove(attempted)
                        st.session_state[f"{prefix}_{attempted}_mirror"] = False
                        st.toast(f"Limit reached: pick at most {max_picks}.", icon="⚠️")
                if not mirror and n in selected_set:
                    selected_set.remove(n)

# ------------------------------ Main UI ---------------------------
if not ss.get("game"):
    st.info("Select a game from the dropdown to reveal the number grid and actions.")
else:
    cfg = GAMES[ss.game]
    st.markdown("<div style='text-align:center;font-weight:800;font-size:22px;margin:6px 0 8px'>Select Your Numbers</div>", unsafe_allow_html=True)

    draw_row("main", cfg["main_range"], ss.main_selected, cfg["main_picks"])
    if cfg["special"]:
        st.markdown(
            f"<div style='text-align:center;margin:12px 0 6px;font-weight:800'>{cfg['special']['label']} "
            f"(pick {cfg['special']['picks']} of {cfg['special']['range']})</div>", unsafe_allow_html=True)
        draw_row("special", cfg["special"]["range"], ss.special_selected, cfg["special"]["picks"])

    # Actions row
    left, mid, right = st.columns(3)
    with left:
        if st.button("AI Suggest"):
            main, special = suggest_for(ss.game)
            for k in list(ss.keys()):
                if k.endswith("_mirror"): ss.pop(k, None)
            ss.main_selected = set(main)
            for n in main: ss[f"main_{n}_mirror"] = True
            if cfg["special"]:
                ss.special_selected = set(special)
                for n in special: ss[f"special_{n}_mirror"] = True
            st.rerun()

    with mid:
        ext = st.toggle("Extended report", value=False, help="Adds analysis & a second page in the free PDF.")

    with right:
        ready = (len(ss.main_selected) == cfg["main_picks"]) and ((not cfg["special"]) or (len(ss.special_selected) == cfg["special"]["picks"]))
        if st.button("Generate PDF", disabled=not ready):
            if not can_run(ss.runs_log, RUNS_PER_DAY):
                st.warning("Daily free limit reached. Upgrade to continue today.")
            else:
                seed = random.randint(1, 10_000_000)
                params = {"game": ss.game, "ext": ext, "main": sorted(list(ss.main_selected))}
                vcode = verification_code(ss.game, seed, params)
                meta = {"vcode": vcode}
                pdf_bytes = build_pdf(ss.game, sorted(ss.main_selected), sorted(ss.special_selected), meta)
                st.download_button("Download Report", data=pdf_bytes, file_name="smartplayai_report.pdf", mime="application/pdf")

    # Ticket health
    st.markdown("---")
    trends = compute_trends(ss.game)  # cached
    health = ticket_health(sorted(ss.main_selected), trends["hot"], trends["cold"]) if ss.main_selected else None
    if health is not None:
        st.markdown(f"**Ticket Health:** {health}/100  ·  Hot in selection: {sum(1 for n in ss.main_selected if n in trends['hot'])}  ·  Cold: {sum(1 for n in ss.main_selected if n in trends['cold'])}")

    # Premium Insights
    st.markdown("---")
    pass_in = st.text_input("Premium passcode (for Insights report)", type="password", placeholder="Enter passcode")
    cols = st.columns([1,1,1])
    with cols[1]:
        if st.button("Generate Insights Report (Premium)"):
            if str(pass_in).strip() == str(PREMIUM_PASS):
                seed = random.randint(1, 10_000_000)
                params = {"game": ss.game, "mode": "insights", "main": sorted(list(ss.main_selected))}
                vcode = verification_code(ss.game, seed, params)
                meta = {"vcode": vcode}
                tr = compute_trends(ss.game, draws=120, alpha=0.97)
                insights_pdf = build_insights_pdf(ss.game, tr, sorted(ss.main_selected), seed, meta)
                st.success("Premium unlocked. Download below.")
                st.download_button("Download Insights PDF", data=insights_pdf, file_name="smartplayai_insights.pdf", mime="application/pdf")
            else:
                st.error("Invalid passcode.")

    # ----------------------------- Live Countdown -----------------------------
    def render_countdown(selected_game: str):
        if not selected_game:
            return
        target = next_draw_datetime(selected_game)
        try:
            st.autorefresh(interval=1000, key=f"countdown_{selected_game.replace(' ', '_')}")
        except Exception:
            pass  # for older Streamlit versions

        now_t = datetime.now(TZ) if TZ else datetime.now()
        remaining = target - now_t
        secs = int(remaining.total_seconds())
        if secs <= 0:
            st.toast("It's draw time! Updating…", icon="⏱️")
            target = next_draw_datetime(selected_game)
            now_t = datetime.now(TZ) if TZ else datetime.now()
            remaining = target - now_t
            secs = int(remaining.total_seconds())

        days = secs // 86400
        hrs  = (secs % 86400) // 3600
        mins = (secs % 3600) // 60
        s    = secs % 60

        st.markdown(
            f"""
            <div class="timer-pill">
              <span>⏱ Next <b>{selected_game}</b> draw in</span>
              <span class="timer-seg">{days:02d}d</span>
              <span class="timer-seg">{hrs:02d}h</span>
              <span class="timer-seg">{mins:02d}m</span>
              <span class="timer-seg">{s:02d}s</span>
              <span class="timer-lab">({next_draw_datetime(selected_game).strftime('%a, %b %d • %I:%M %p')})</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")
    render_countdown(ss.game)

# ---------- Sidebar mini-calendar & ICS download ----------
with st.sidebar:
    st.markdown("## 📅 Upcoming Draws")
    for g in GAMES.keys():
        st.markdown(f"**{g}**")
        for dt in get_next_k_draws(g, k=4):
            st.caption(dt.strftime("%a, %b %d • %I:%M %p"))
        st.markdown("---")

    ics_bytes = build_ics_for_all(next_n=8)
    st.download_button(
        "⬇️ Add to Calendar (.ics)",
        data=ics_bytes,
        file_name="smartplayai_draws.ics",
        mime="text/calendar",
        help="Import into Apple/Google/Outlook to see upcoming draws."
    )

# ----------------------------- Footer -----------------------------
st.markdown("""
<hr style="margin-top:30px; margin-bottom:10px; border:1px solid rgba(255,255,255,0.15);">
<div style="text-align:center; font-size:14px; color:#aaa;">
  <p>
    <a href="https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/privacy_policy.md" target="_blank" style="color:#fff;text-decoration:none;">
      Privacy Policy
    </a> | 
    <a href="https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/terms_of_service.md" target="_blank" style="color:#fff;text-decoration:none;">
      Terms of Service
    </a> | 
    <a href="https://raw.githubusercontent.com/Smartplayai/smartplayai-app/main/responsible_gaming.md" target="_blank" style="color:#fff;text-decoration:none;">
      Responsible Gaming
    </a>
  </p>
  <p style="font-size:13px; margin-top:8px;">
    © 2025 SmartPlayAI • Play responsibly. Must be 18+ • Insights are for entertainment only.
  </p>
</div>
""", unsafe_allow_html=True)
