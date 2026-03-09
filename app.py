"""
HabitTrack Pro — HabitKit UI Clone
Streamlit + Google Sheets backend
No streamlit-extras dependency
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import pytz
from st_gsheets_connection import GSheetsConnection
import uuid
import calendar as cal_module

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

MAX_PIN_ATTEMPTS = 5

ACCENT_COLORS = [
    "#22c55e", "#3b82f6", "#a855f7", "#f97316",
    "#ef4444", "#eab308", "#06b6d4", "#ec4899",
]

DEFAULT_HABITS = [
    {"HabitID": "h1", "Name": "Morning Exercise", "Icon": "🏃", "Color": "#22c55e", "Target": "daily", "Active": 1, "SortOrder": 1},
    {"HabitID": "h2", "Name": "Read 30 Minutes",  "Icon": "📚", "Color": "#3b82f6", "Target": "daily", "Active": 1, "SortOrder": 2},
    {"HabitID": "h3", "Name": "Meditate",          "Icon": "🧘", "Color": "#a855f7", "Target": "daily", "Active": 1, "SortOrder": 3},
    {"HabitID": "h4", "Name": "Drink Water (2L)",  "Icon": "💧", "Color": "#06b6d4", "Target": "daily", "Active": 1, "SortOrder": 4},
]

SHEET_LOG      = "Log"
SHEET_HABITS   = "Habits"
SHEET_SECURITY = "Security"

TABS = [
    ("📅", "Today"),
    ("📊", "Dashboard"),
    ("📆", "Calendar"),
    ("📈", "Stats"),
    ("🏷️", "Habits"),
    ("⚙️", "Manage"),
]

# ──────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="HabitTrack Pro",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# GLOBAL CSS  (no streamlit-extras needed)
# ──────────────────────────────────────────────

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .block-container {
    background: #0f0f0f !important;
    color: #f0f0f0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="collapsedControl"] { display: none !important; }

.block-container {
    padding: 1rem 0.75rem 120px !important;
    max-width: 430px !important;
    margin: 0 auto !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: #0f0f0f; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

/* ── FIXED BOTTOM NAV ── */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    max-width: 430px;
    background: rgba(13,13,13,0.97);
    border-top: 1px solid #1e1e1e;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    z-index: 9999;
    display: flex;
    padding: 0;
}
/* Buttons inside nav get hidden default border */
.bottom-nav [data-testid="stButton"] button {
    background: transparent !important;
    border: none !important;
    border-top: 2px solid transparent !important;
    border-radius: 0 !important;
    color: #555 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: .58rem !important;
    font-weight: 600 !important;
    height: 56px !important;
    width: 100% !important;
    padding: 4px 2px 2px !important;
    line-height: 1.3 !important;
    cursor: pointer !important;
}
.bottom-nav [data-testid="stButton"] button:hover {
    color: #888 !important;
    background: transparent !important;
}

/* Active nav tab — injected dynamically via data-active attr trick */
.nav-active button {
    color: #3b82f6 !important;
    border-top: 2px solid #3b82f6 !important;
}

/* ── HABIT CARD ── */
.habit-card {
    background: #161616;
    border: 1px solid #222;
    border-radius: 16px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.habit-name  { font-size: .92rem; font-weight: 600; color: #f0f0f0; }
.habit-meta  { font-size: .64rem; color: #555; margin-top: 2px; }
.streak-badge {
    display: inline-flex; align-items: center; gap: 3px;
    background: #1a1a1a; border-radius: 20px; padding: 3px 9px;
    font-size: .72rem; font-weight: 700; color: #f97316;
}
.icon-badge {
    width: 32px; height: 32px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; flex-shrink: 0;
}

/* ── PROGRESS BAR ── */
.prog-bar-wrap { background: #1e1e1e; border-radius: 99px; height: 6px; margin: 6px 0 14px; }
.prog-bar-fill { border-radius: 99px; height: 6px; background: #3b82f6; }

/* ── SECTION TITLE ── */
.section-title {
    font-size: .68rem; font-weight: 700; color: #444;
    letter-spacing: .12em; text-transform: uppercase; margin: 16px 0 8px;
}

/* ── STAT CARD ── */
.stat-card {
    background: #161616; border: 1px solid #222; border-radius: 14px;
    padding: 14px;
}
.stat-value { font-size: 1.5rem; font-weight: 800; color: #f0f0f0; line-height: 1; }
.stat-label { font-size: .64rem; color: #555; margin-top: 4px; }

/* ── CALENDAR ── */
.cal-day {
    background: #161616; border: 1px solid #1e1e1e; border-radius: 8px;
    padding: 5px 3px; min-height: 50px; font-size: .7rem; color: #555;
    text-align: center;
}
.cal-day-today { border-color: #2563eb !important; }
.cal-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin: 1px; }
.cal-header { font-size: .63rem; color: #444; text-align: center; padding: 3px 0; font-weight: 700; letter-spacing: .06em; }

/* ── TODAY ── */
.date-header { font-size: 1.25rem; font-weight: 700; color: #2e2e2e; margin-bottom: 12px; }
.all-done-msg { text-align: center; padding: 40px 20px; color: #555; font-size: .9rem; }

/* ── COMPLETE BUTTON OVERRIDES ── */
.btn-complete button {
    border-radius: 50% !important;
    width: 36px !important;
    height: 36px !important;
    min-height: 36px !important;
    padding: 0 !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    line-height: 1 !important;
}
.btn-done button {
    background: var(--done-color, #22c55e) !important;
    border: none !important;
    color: #fff !important;
}
.btn-pending button {
    background: transparent !important;
    border: 2px solid var(--done-color, #22c55e) !important;
    color: var(--done-color, #22c55e) !important;
}

/* ── MISC BUTTONS ── */
[data-testid="stButton"] > button {
    font-family: 'DM Sans', sans-serif !important;
    border-radius: 10px !important;
    transition: opacity .15s;
}
[data-testid="stButton"] > button:active { opacity: .7; }

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #1a1a1a !important;
    color: #f0f0f0 !important;
    border-color: #2a2a2a !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #1a1a1a !important;
    color: #f0f0f0 !important;
    border-color: #2a2a2a !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Expander */
details summary { color: #888 !important; font-size: .8rem !important; }
[data-testid="stExpander"] {
    background: #161616 !important;
    border: 1px solid #222 !important;
    border-radius: 12px !important;
}

hr { border-color: #1e1e1e !important; margin: 10px 0 !important; }

/* PIN pad */
.pin-key button {
    background: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 12px !important;
    color: #f0f0f0 !important;
    font-size: 1.3rem !important;
    font-weight: 600 !important;
    height: 54px !important;
    font-family: 'DM Sans', sans-serif !important;
}

</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# GOOGLE SHEETS
# ──────────────────────────────────────────────

@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def read_sheet(worksheet: str) -> pd.DataFrame:
    try:
        df = get_conn().read(worksheet=worksheet, ttl=0)
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def write_sheet(worksheet: str, df: pd.DataFrame):
    get_conn().update(worksheet=worksheet, data=df)
    st.cache_data.clear()


# ──────────────────────────────────────────────
# BOOTSTRAP
# ──────────────────────────────────────────────

def bootstrap_session():
    # Habits
    habits_df = read_sheet(SHEET_HABITS)
    if habits_df.empty or "HabitID" not in habits_df.columns:
        habits_df = pd.DataFrame(DEFAULT_HABITS)
        write_sheet(SHEET_HABITS, habits_df)
    st.session_state.habits_df = habits_df

    # Log
    log_df = read_sheet(SHEET_LOG)
    if log_df.empty or "Date" not in log_df.columns:
        log_df = pd.DataFrame(columns=["Date","Habit","Completed","Note","TimestampLogged"])
    else:
        log_df["Date"] = pd.to_datetime(log_df["Date"]).dt.date
        log_df["Completed"] = pd.to_numeric(log_df["Completed"], errors="coerce").fillna(0).astype(int)
    st.session_state.log_df = log_df

    # Security
    sec_df = read_sheet(SHEET_SECURITY)
    if sec_df.empty or "PIN" not in sec_df.columns:
        sec_df = pd.DataFrame({"PIN": [""]})
        write_sheet(SHEET_SECURITY, sec_df)
    st.session_state.pin_hash = str(sec_df["PIN"].iloc[0]) if len(sec_df) > 0 else ""

    auto_miss()
    st.session_state.bootstrapped = True


def auto_miss():
    yesterday = date.today() - timedelta(days=1)
    habits_df = st.session_state.habits_df
    log_df    = st.session_state.log_df
    active_daily = habits_df[
        (habits_df["Active"].astype(str) == "1") &
        (habits_df["Target"].str.lower() == "daily")
    ]
    new_rows = []
    for _, h in active_daily.iterrows():
        already = log_df[
            (log_df["Date"] == yesterday) & (log_df["Habit"] == h["HabitID"])
        ] if not log_df.empty else pd.DataFrame()
        if already.empty:
            new_rows.append({
                "Date": yesterday, "Habit": h["HabitID"],
                "Completed": 0, "Note": "",
                "TimestampLogged": datetime.now().isoformat()
            })
    if new_rows:
        log_df = pd.concat([log_df, pd.DataFrame(new_rows)], ignore_index=True)
        st.session_state.log_df = log_df
        write_sheet(SHEET_LOG, log_df)


# ──────────────────────────────────────────────
# DATA HELPERS
# ──────────────────────────────────────────────

def today_date() -> date:
    return date.today()

def get_streak(habit_id: str) -> int:
    log_df = st.session_state.log_df
    if log_df.empty:
        return 0
    done = log_df[(log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]
    if done.empty:
        return 0
    dates = sorted(done["Date"].unique(), reverse=True)
    streak, check = 0, today_date()
    for d in dates:
        if d == check:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak

def get_best_streak(habit_id: str) -> int:
    log_df = st.session_state.log_df
    if log_df.empty:
        return 0
    done = log_df[(log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]
    if done.empty:
        return 0
    dates = sorted(done["Date"].unique())
    best = cur = 1
    for i in range(1, len(dates)):
        if dates[i] == dates[i-1] + timedelta(days=1):
            cur += 1
            best = max(best, cur)
        else:
            cur = 1
    return best

def get_completion_pct(habit_id: str, days: int = 30) -> float:
    log_df = st.session_state.log_df
    if log_df.empty:
        return 0.0
    start = today_date() - timedelta(days=days - 1)
    sub = log_df[
        (log_df["Habit"] == habit_id) &
        (log_df["Date"] >= start) &
        (log_df["Date"] <= today_date())
    ]
    return sub["Completed"].sum() / days * 100

def is_done_today(habit_id: str) -> bool:
    log_df = st.session_state.log_df
    if log_df.empty:
        return False
    return not log_df[
        (log_df["Date"] == today_date()) &
        (log_df["Habit"] == habit_id) &
        (log_df["Completed"] == 1)
    ].empty

def toggle_habit_today(habit_id: str, note: str = ""):
    log_df = st.session_state.log_df
    today  = today_date()
    existing = log_df[(log_df["Date"] == today) & (log_df["Habit"] == habit_id)] if not log_df.empty else pd.DataFrame()
    if existing.empty:
        new_row = pd.DataFrame([{
            "Date": today, "Habit": habit_id, "Completed": 1,
            "Note": note, "TimestampLogged": datetime.now().isoformat()
        }])
        log_df = pd.concat([log_df, new_row], ignore_index=True)
    else:
        idx = existing.index[0]
        cur = int(log_df.at[idx, "Completed"])
        log_df.at[idx, "Completed"] = 0 if cur == 1 else 1
        if note:
            log_df.at[idx, "Note"] = note
    st.session_state.log_df = log_df
    write_sheet(SHEET_LOG, log_df)

def active_habits() -> pd.DataFrame:
    df = st.session_state.habits_df.copy()
    df["Active"] = pd.to_numeric(df["Active"], errors="coerce").fillna(0).astype(int)
    return df[df["Active"] == 1].sort_values("SortOrder", ignore_index=True)


# ──────────────────────────────────────────────
# TILE GRID
# ──────────────────────────────────────────────

def render_habit_grid(habit_id: str, color: str, weeks: int = 18) -> str:
    log_df = st.session_state.log_df
    today  = today_date()
    total_days = weeks * 7
    start_date = today - timedelta(days=total_days - 1)
    pad_start  = start_date - timedelta(days=start_date.weekday())

    habit_done: set = set()
    if not log_df.empty:
        habit_done = set(
            log_df[(log_df["Habit"] == habit_id) & (log_df["Completed"] == 1)]["Date"].tolist()
        )

    all_dates = []
    d = pad_start
    while d <= today:
        all_dates.append(d)
        d += timedelta(days=1)
    while len(all_dates) % 7:
        all_dates.append(all_dates[-1] + timedelta(days=1))

    tiles = []
    for d in all_dates:
        in_range = d >= start_date and d <= today
        if not in_range:
            bg, outline = "transparent", ""
        elif d in habit_done:
            bg, outline = color, ""
        else:
            bg, outline = "#1e1e1e", ""
        if d == today and in_range:
            outline = "outline:1px solid rgba(255,255,255,0.55);outline-offset:1px;"
        tiles.append(
            f"<div style='width:9px;height:9px;border-radius:2px;"
            f"background:{bg};{outline}'></div>"
        )

    return (
        "<div style='display:grid;grid-template-rows:repeat(7,9px);"
        "grid-auto-flow:column;gap:3px;overflow:hidden;'>"
        + "".join(tiles)
        + "</div>"
    )


# ──────────────────────────────────────────────
# BOTTOM NAV  (pure CSS — no streamlit-extras)
# ──────────────────────────────────────────────

def render_nav():
    active = st.session_state.get("active_tab", 0)

    # Inject the fixed nav container via HTML
    st.markdown("<div class='bottom-nav' id='bnav'>", unsafe_allow_html=True)

    cols = st.columns(6)
    for i, (icon, label) in enumerate(TABS):
        is_active = (active == i)
        active_css = (
            "color:#3b82f6!important;border-top:2px solid #3b82f6!important;"
            if is_active else
            "color:#555!important;border-top:2px solid transparent!important;"
        )
        # Inject per-button style override via unique key + CSS
        st.markdown(f"""
        <style>
        div[data-testid="column"]:nth-child({i+1}) .stButton button {{
            {active_css}
        }}
        </style>
        """, unsafe_allow_html=True)
        with cols[i]:
            if st.button(f"{icon}\n{label}", key=f"nav_{i}"):
                st.session_state.active_tab = i
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# PIN GATE
# ──────────────────────────────────────────────

def show_pin_gate():
    pin_hash = st.session_state.get("pin_hash", "")
    if not pin_hash or st.session_state.get("authenticated"):
        st.session_state.authenticated = True
        return

    attempts = st.session_state.get("pin_attempts", 0)
    if attempts >= MAX_PIN_ATTEMPTS:
        st.error("Too many failed attempts. Restart the app.")
        st.stop()

    entered = st.session_state.get("pin_entered", "")

    dots_html = "<div style='display:flex;justify-content:center;gap:14px;margin:16px 0;'>"
    for i in range(4):
        bg = "#f0f0f0" if i < len(entered) else "#333"
        dots_html += f"<div style='width:13px;height:13px;border-radius:50%;background:{bg};'></div>"
    dots_html += "</div>"

    st.markdown(f"""
    <div style='background:#161616;border:1px solid #222;border-radius:20px;
         padding:28px 20px;max-width:280px;margin:40px auto 0;text-align:center;'>
        <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;margin-bottom:4px;'>🔐 Enter PIN</div>
        <div style='font-size:.72rem;color:#555;margin-bottom:4px;'>Enter your 4-digit PIN</div>
        {dots_html}
    </div>
    """, unsafe_allow_html=True)

    keys_layout = [["1","2","3"],["4","5","6"],["7","8","9"],["←","0","✓"]]
    st.markdown("<div style='max-width:280px;margin:8px auto;'>", unsafe_allow_html=True)
    for row in keys_layout:
        c1, c2, c3 = st.columns(3)
        for col, k in zip([c1,c2,c3], row):
            with col:
                st.markdown("<div class='pin-key'>", unsafe_allow_html=True)
                if st.button(k, key=f"pk_{k}_{row[0]}", use_container_width=True):
                    if k == "←":
                        st.session_state.pin_entered = entered[:-1]
                    elif k == "✓":
                        _check_pin(entered, pin_hash, attempts)
                    else:
                        new = entered + k
                        st.session_state.pin_entered = new
                        if len(new) == 4:
                            _check_pin(new, pin_hash, attempts)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


def _check_pin(entered, pin_hash, attempts):
    if entered == pin_hash:
        st.session_state.authenticated = True
        st.session_state.pin_entered   = ""
    else:
        st.session_state.pin_attempts  = attempts + 1
        st.session_state.pin_entered   = ""
        left = MAX_PIN_ATTEMPTS - attempts - 1
        st.error(f"Wrong PIN. {left} attempt(s) left.")


# ──────────────────────────────────────────────
# TAB 0: TODAY
# ──────────────────────────────────────────────

def tab_today():
    today = today_date()
    st.markdown(f"<div class='date-header'>{today.strftime('%A, %-d %b')}</div>", unsafe_allow_html=True)

    habits = active_habits()
    if habits.empty:
        st.markdown("<div class='all-done-msg'>No habits yet.<br>Add one in the Habits tab 🌱</div>", unsafe_allow_html=True)
        return

    total      = len(habits)
    done_count = sum(1 for _, h in habits.iterrows() if is_done_today(h["HabitID"]))
    pct        = done_count / total if total else 0

    st.markdown(f"""
    <div style='display:flex;justify-content:space-between;font-size:.72rem;color:#555;margin-bottom:4px;'>
        <span>Today's Progress</span>
        <span style='color:#3b82f6;font-weight:700;'>{done_count} / {total}</span>
    </div>
    <div class='prog-bar-wrap'>
        <div class='prog-bar-fill' style='width:{pct*100:.0f}%;'></div>
    </div>
    """, unsafe_allow_html=True)

    if done_count == total and total > 0:
        st.markdown("<div class='all-done-msg'>All done! 🎉<br><span style='font-size:.75rem;color:#2e2e2e;'>Great work today!</span></div>", unsafe_allow_html=True)
        return

    for _, h in habits.iterrows():
        hid   = h["HabitID"]
        color = h.get("Color", "#3b82f6")
        icon  = h.get("Icon", "⭐")
        name  = h["Name"]
        streak = get_streak(hid)
        done   = is_done_today(hid)

        col_left, col_right = st.columns([5, 1])
        with col_left:
            st.markdown(f"""
            <div style='display:flex;align-items:center;gap:10px;padding:4px 0;'>
                <div class='icon-badge' style='background:{color}22;'>{icon}</div>
                <div>
                    <div class='habit-name'>{name}</div>
                    <span class='streak-badge'>🔥 {streak} days</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            btn_lbl = "✓" if done else "○"
            if done:
                st.markdown(f"""
                <style>
                div[data-testid="column"]:last-child .stButton button {{
                    background:{color}!important;border:none!important;color:#fff!important;
                    border-radius:50%!important;width:36px!important;height:36px!important;
                    min-height:36px!important;padding:0!important;font-weight:700!important;
                }}
                </style>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <style>
                div[data-testid="column"]:last-child .stButton button {{
                    background:transparent!important;
                    border:2px solid {color}!important;color:{color}!important;
                    border-radius:50%!important;width:36px!important;height:36px!important;
                    min-height:36px!important;padding:0!important;font-weight:700!important;
                }}
                </style>""", unsafe_allow_html=True)

            if st.button(btn_lbl, key=f"tog_{hid}"):
                toggle_habit_today(hid)
                st.rerun()

        if done:
            with st.expander("Add note", expanded=False):
                note = st.text_area("", key=f"note_{hid}", label_visibility="collapsed", placeholder="How did it go?")
                if st.button("Save note", key=f"savenote_{hid}"):
                    toggle_habit_today(hid, note)
                    st.rerun()

        st.markdown("<div style='height:2px;'></div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 1: DASHBOARD
# ──────────────────────────────────────────────

def tab_dashboard():
    st.markdown("<div class='section-title'>Habit Overview</div>", unsafe_allow_html=True)
    habits = active_habits()
    if habits.empty:
        st.markdown("<div class='all-done-msg'>No habits yet.</div>", unsafe_allow_html=True)
        return

    sort_by = st.selectbox("", ["Streak","Name","Completion %"], key="dash_sort", label_visibility="collapsed")
    rows = habits.to_dict("records")
    if sort_by == "Streak":
        rows.sort(key=lambda h: get_streak(h["HabitID"]), reverse=True)
    elif sort_by == "Name":
        rows.sort(key=lambda h: h["Name"])
    else:
        rows.sort(key=lambda h: get_completion_pct(h["HabitID"]), reverse=True)

    log_df = st.session_state.log_df
    for h in rows:
        hid    = h["HabitID"]
        color  = h.get("Color","#3b82f6")
        streak = get_streak(hid)
        pct30  = get_completion_pct(hid, 30)
        total  = 0 if log_df.empty else int((log_df["Habit"]==hid) & (log_df["Completed"]==1)).sum() if False else (
            len(log_df[(log_df["Habit"]==hid) & (log_df["Completed"]==1)])
        )
        grid   = render_habit_grid(hid, color, 18)

        st.markdown(f"""
        <div class='habit-card'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <div class='icon-badge' style='background:{color}22;'>{h.get("Icon","⭐")}</div>
                <div style='flex:1;'>
                    <div class='habit-name'>{h["Name"]}</div>
                    <div class='habit-meta'>{h.get("Target","daily").capitalize()}</div>
                </div>
                <span class='streak-badge'>🔥 {streak}</span>
            </div>
            <div style='overflow-x:auto;padding-bottom:2px;'>{grid}</div>
            <div style='display:flex;justify-content:space-between;margin-top:8px;'>
                <span class='habit-meta'>{pct30:.0f}% last 30 days</span>
                <span class='habit-meta'>{total} total</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("＋ Add Habit", key="dash_add", use_container_width=True):
        st.session_state.active_tab = 4
        st.rerun()


# ──────────────────────────────────────────────
# TAB 2: CALENDAR
# ──────────────────────────────────────────────

def tab_calendar():
    today = today_date()
    if "cal_year"  not in st.session_state: st.session_state.cal_year  = today.year
    if "cal_month" not in st.session_state: st.session_state.cal_month = today.month
    if "cal_sel"   not in st.session_state: st.session_state.cal_sel   = None

    year, month = st.session_state.cal_year, st.session_state.cal_month

    c1, c2, c3 = st.columns([1,3,1])
    with c1:
        if st.button("‹", key="cal_prev"):
            m, y = month-1, year
            if m < 1: m, y = 12, y-1
            st.session_state.cal_month = m; st.session_state.cal_year = y; st.rerun()
    with c2:
        st.markdown(f"<div style='text-align:center;font-weight:700;font-size:.95rem;color:#f0f0f0;padding:6px 0;'>{date(year,month,1).strftime('%B %Y')}</div>", unsafe_allow_html=True)
    with c3:
        if st.button("›", key="cal_next"):
            m, y = month+1, year
            if m > 12: m, y = 1, y+1
            st.session_state.cal_month = m; st.session_state.cal_year = y; st.rerun()

    day_names = ["Mo","Tu","We","Th","Fr","Sa","Su"]
    hcols = st.columns(7)
    for i, dn in enumerate(day_names):
        with hcols[i]:
            st.markdown(f"<div class='cal-header'>{dn}</div>", unsafe_allow_html=True)

    habits = active_habits()
    log_df = st.session_state.log_df

    def dots_for(d: date) -> str:
        if log_df.empty: return ""
        done_ids = log_df[(log_df["Date"]==d)&(log_df["Completed"]==1)]["Habit"].tolist()
        out = ""
        for hid in done_ids:
            row = habits[habits["HabitID"]==hid]
            if not row.empty:
                out += f"<span class='cal-dot' style='background:{row.iloc[0][\"Color\"]};'></span>"
        return out

    for week in cal_module.monthcalendar(year, month):
        wcols = st.columns(7)
        for i, dn in enumerate(week):
            with wcols[i]:
                if dn == 0:
                    st.markdown("<div style='min-height:50px;'></div>", unsafe_allow_html=True)
                else:
                    d = date(year, month, dn)
                    today_cls = "cal-day-today" if d==today else ""
                    sel_style = "border-color:#f97316!important;" if st.session_state.cal_sel==d else ""
                    day_color = "#f0f0f0" if d==today else "#555"
                    day_w     = "700"     if d==today else "400"
                    dots      = dots_for(d)
                    st.markdown(f"""
                    <div class='cal-day {today_cls}' style='{sel_style}'>
                        <div style='font-size:.7rem;color:{day_color};font-weight:{day_w};'>{dn}</div>
                        <div style='display:flex;flex-wrap:wrap;margin-top:3px;justify-content:center;'>{dots}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(" ", key=f"cd_{dn}_{month}_{year}", help=d.strftime("%b %d")):
                        st.session_state.cal_sel = d; st.rerun()

    sel = st.session_state.cal_sel
    if sel:
        st.markdown(f"<div class='section-title'>{sel.strftime('%A, %B %-d')}</div>", unsafe_allow_html=True)
        if log_df.empty:
            done_day = pd.DataFrame()
        else:
            done_day = log_df[(log_df["Date"]==sel) & (log_df["Completed"]==1)]
        if done_day.empty:
            st.markdown("<div style='color:#555;font-size:.8rem;padding:8px 0;'>Nothing logged.</div>", unsafe_allow_html=True)
        else:
            for _, row in done_day.iterrows():
                hr = habits[habits["HabitID"]==row["Habit"]]
                if hr.empty: continue
                h = hr.iloc[0]
                c = h.get("Color","#3b82f6")
                note_html = f"<span style='font-size:.7rem;color:#555;margin-left:auto;'>{row['Note']}</span>" if row.get("Note") else ""
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #1e1e1e;'>
                    <div class='icon-badge' style='background:{c}22;width:24px;height:24px;font-size:.8rem;'>{h["Icon"]}</div>
                    <span style='font-size:.85rem;color:#f0f0f0;'>{h["Name"]}</span>{note_html}
                </div>
                """, unsafe_allow_html=True)

        # Month completion %
        total_p = len(habits) * cal_module.monthrange(year, month)[1]
        total_done = 0 if log_df.empty else len(log_df[
            (log_df["Date"].apply(lambda d: d.year==year and d.month==month)) &
            (log_df["Completed"]==1)
        ])
        mpct = total_done / total_p * 100 if total_p else 0
        st.markdown(f"""
        <div style='margin-top:14px;text-align:center;'>
            <div style='font-size:2rem;font-weight:800;color:#f0f0f0;'>{mpct:.0f}%</div>
            <div style='font-size:.65rem;color:#555;'>Completion this month</div>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 3: STATS
# ──────────────────────────────────────────────

def tab_stats():
    habits = active_habits()
    log_df = st.session_state.log_df
    today  = today_date()

    perfect_days = 0
    if not log_df.empty and not habits.empty:
        total_h = len(habits)
        daily = log_df[log_df["Completed"]==1].groupby("Date")["Habit"].nunique()
        perfect_days = int((daily >= total_h).sum())

    # Heatmap
    st.markdown("<div class='section-title'>Contribution Heatmap</div>", unsafe_allow_html=True)
    weeks = 26
    start = today - timedelta(days=weeks*7-1)
    pad   = start - timedelta(days=start.weekday())
    heat_dates, d = [], pad
    while d <= today:
        heat_dates.append(d); d += timedelta(days=1)
    while len(heat_dates) % 7: heat_dates.append(heat_dates[-1]+timedelta(days=1))

    th = max(len(habits), 1)
    tiles = []
    for d in heat_dates:
        cnt = 0 if log_df.empty else len(log_df[(log_df["Date"]==d)&(log_df["Completed"]==1)])
        intensity = min(cnt/th, 1.0)
        if d > today:    bg = "transparent"
        elif intensity == 0: bg = "#1e1e1e"
        else:
            g = int(60 + intensity*160)
            bg = f"rgb(0,{g},60)"
        outline = "outline:1px solid rgba(255,255,255,0.5);outline-offset:1px;" if d==today else ""
        tiles.append(f"<div style='width:9px;height:9px;border-radius:2px;background:{bg};{outline}'></div>")

    st.markdown(
        "<div style='overflow-x:auto;'>"
        "<div style='display:grid;grid-template-rows:repeat(7,9px);grid-auto-flow:column;gap:3px;'>"
        + "".join(tiles) + "</div></div>",
        unsafe_allow_html=True
    )

    # Summary
    st.markdown("<div class='section-title'>Summary</div>", unsafe_allow_html=True)
    total_comp = 0 if log_df.empty else len(log_df[log_df["Completed"]==1])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>🏆 {perfect_days}</div><div class='stat-label'>Perfect Days</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card'><div class='stat-value'>✅ {total_comp}</div><div class='stat-label'>Total Completions</div></div>", unsafe_allow_html=True)

    # Per-habit
    st.markdown("<div class='section-title'>Per-Habit Stats</div>", unsafe_allow_html=True)
    for _, h in habits.iterrows():
        hid   = h["HabitID"]
        color = h.get("Color","#3b82f6")
        streak = get_streak(hid); best = get_best_streak(hid)
        pct7 = get_completion_pct(hid,7); pct30 = get_completion_pct(hid,30); pct90 = get_completion_pct(hid,90)
        total = 0 if log_df.empty else len(log_df[(log_df["Habit"]==hid)&(log_df["Completed"]==1)])
        st.markdown(f"""
        <div class='habit-card'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <div class='icon-badge' style='background:{color}22;'>{h["Icon"]}</div>
                <div class='habit-name' style='flex:1;'>{h["Name"]}</div>
                <span class='streak-badge'>🔥 {streak}</span>
            </div>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;'>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;'>{streak}</div>
                    <div class='habit-meta'>Current streak</div>
                </div>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;'>{best}</div>
                    <div class='habit-meta'>Best streak</div>
                </div>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:{color};'>{pct30:.0f}%</div>
                    <div class='habit-meta'>Last 30 days</div>
                </div>
                <div style='background:#1a1a1a;border-radius:8px;padding:8px;'>
                    <div style='font-size:1.1rem;font-weight:700;color:#f0f0f0;'>{total}</div>
                    <div class='habit-meta'>All-time total</div>
                </div>
            </div>
            <div style='margin-top:10px;'>
                <div style='display:flex;justify-content:space-between;font-size:.65rem;color:#555;margin-bottom:3px;'>
                    <span>7d {pct7:.0f}%</span><span>30d {pct30:.0f}%</span><span>90d {pct90:.0f}%</span>
                </div>
                <div style='background:#1e1e1e;border-radius:99px;height:4px;'>
                    <div style='background:{color};border-radius:99px;height:4px;width:{min(pct30,100):.0f}%;'></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Day of week
    st.markdown("<div class='section-title'>Best Day of Week</div>", unsafe_allow_html=True)
    if not log_df.empty:
        lc = log_df[log_df["Completed"]==1].copy()
        lc["dow"] = pd.to_datetime(lc["Date"]).dt.dayofweek
        dow = lc.groupby("dow").size().reindex(range(7), fill_value=0)
    else:
        dow = pd.Series([0]*7)
    mx = max(int(dow.max()), 1)
    for i, label in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
        w = dow.iloc[i] / mx * 100
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>
            <span style='font-size:.72rem;color:#555;width:28px;'>{label}</span>
            <div style='flex:1;background:#1e1e1e;border-radius:99px;height:8px;'>
                <div style='background:#3b82f6;border-radius:99px;height:8px;width:{w:.0f}%;'></div>
            </div>
            <span style='font-size:.65rem;color:#555;width:20px;text-align:right;'>{dow.iloc[i]}</span>
        </div>
        """, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 4: HABITS
# ──────────────────────────────────────────────

def tab_habits():
    habits_df = st.session_state.habits_df

    st.markdown("<div class='section-title'>Active Habits</div>", unsafe_allow_html=True)
    for idx, row in habits_df[habits_df["Active"].astype(str)=="1"].iterrows():
        color = row.get("Color","#3b82f6")
        with st.expander(f"{row['Icon']} {row['Name']}", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                new_name   = st.text_input("Name",        value=row["Name"],   key=f"hn_{idx}")
                new_icon   = st.text_input("Icon (emoji)",value=row["Icon"],   key=f"hi_{idx}", max_chars=2)
            with c2:
                opts = ["daily","3x per week","5x per week"]
                cur_tgt = row["Target"] if row["Target"] in opts else "daily"
                new_target = st.selectbox("Target", opts, index=opts.index(cur_tgt), key=f"ht_{idx}")

            st.markdown("<div style='font-size:.7rem;color:#555;margin:6px 0 4px;'>Color</div>", unsafe_allow_html=True)
            new_color = st.selectbox("Color", ACCENT_COLORS, key=f"hc_{idx}",
                index=ACCENT_COLORS.index(color) if color in ACCENT_COLORS else 0,
                format_func=lambda c: c)
            swatches = "".join([
                f"<div style='width:22px;height:22px;border-radius:50%;background:{c};"
                f"display:inline-block;margin:2px;"
                f"border:2px solid {\"#f0f0f0\" if c==new_color else \"transparent\"};'></div>"
                for c in ACCENT_COLORS
            ])
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:2px;'>{swatches}</div>", unsafe_allow_html=True)

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("💾 Save", key=f"sv_{idx}", use_container_width=True):
                    habits_df.at[idx,"Name"]   = new_name
                    habits_df.at[idx,"Icon"]   = new_icon
                    habits_df.at[idx,"Target"] = new_target
                    habits_df.at[idx,"Color"]  = new_color
                    st.session_state.habits_df = habits_df
                    write_sheet(SHEET_HABITS, habits_df)
                    st.success("Saved!"); st.rerun()
            with bc2:
                if st.button("🗃️ Archive", key=f"ar_{idx}", use_container_width=True):
                    habits_df.at[idx,"Active"] = 0
                    st.session_state.habits_df = habits_df
                    write_sheet(SHEET_HABITS, habits_df); st.rerun()

    # Add new
    st.markdown("<div class='section-title'>Add New Habit</div>", unsafe_allow_html=True)
    st.markdown("<div style='background:#161616;border:1px solid #222;border-radius:16px;padding:14px;'>", unsafe_allow_html=True)
    n_name   = st.text_input("Habit Name",    key="nh_name", placeholder="e.g. Morning Run")
    n_icon   = st.text_input("Icon (emoji)",  key="nh_icon", value="⭐", max_chars=2)
    n_target = st.selectbox("Target",         ["daily","3x per week","5x per week"], key="nh_tgt")
    n_color  = st.selectbox("Color",          ACCENT_COLORS, key="nh_color", format_func=lambda c: c)
    if st.button("➕ Add Habit", key="add_h", use_container_width=True):
        if n_name.strip():
            new_id  = str(uuid.uuid4())[:8]
            max_ord = int(habits_df["SortOrder"].max()) + 1 if not habits_df.empty else 1
            new_row = pd.DataFrame([{"HabitID":new_id,"Name":n_name.strip(),"Icon":n_icon,
                                     "Color":n_color,"Target":n_target,"Active":1,"SortOrder":max_ord}])
            habits_df = pd.concat([habits_df, new_row], ignore_index=True)
            st.session_state.habits_df = habits_df
            write_sheet(SHEET_HABITS, habits_df)
            st.success(f"Added '{n_name}'!"); st.rerun()
        else:
            st.warning("Please enter a habit name.")
    st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# TAB 5: MANAGE
# ──────────────────────────────────────────────

def tab_manage():
    habits_df = st.session_state.habits_df

    st.markdown("<div class='section-title'>Sort Order</div>", unsafe_allow_html=True)
    active = habits_df[habits_df["Active"].astype(str)=="1"].sort_values("SortOrder")
    active_list = list(active.iterrows())
    for i, (idx, row) in enumerate(active_list):
        c1, c2, c3 = st.columns([4,1,1])
        with c1:
            st.markdown(f"<div style='padding:8px 0;font-size:.85rem;color:#f0f0f0;'>{row['Icon']} {row['Name']}</div>", unsafe_allow_html=True)
        with c2:
            if st.button("▲", key=f"up_{idx}") and i > 0:
                pi = active_list[i-1][0]
                habits_df.at[idx,"SortOrder"], habits_df.at[pi,"SortOrder"] = \
                    habits_df.at[pi,"SortOrder"], habits_df.at[idx,"SortOrder"]
                st.session_state.habits_df = habits_df
                write_sheet(SHEET_HABITS, habits_df); st.rerun()
        with c3:
            if st.button("▼", key=f"dn_{idx}") and i < len(active_list)-1:
                ni = active_list[i+1][0]
                habits_df.at[idx,"SortOrder"], habits_df.at[ni,"SortOrder"] = \
                    habits_df.at[ni,"SortOrder"], habits_df.at[idx,"SortOrder"]
                st.session_state.habits_df = habits_df
                write_sheet(SHEET_HABITS, habits_df); st.rerun()

    archived = habits_df[habits_df["Active"].astype(str)=="0"]
    if not archived.empty:
        st.markdown("<div class='section-title'>Archived Habits</div>", unsafe_allow_html=True)
        for idx, row in archived.iterrows():
            c1, c2 = st.columns([4,1])
            with c1:
                st.markdown(f"<div style='padding:8px 0;font-size:.85rem;color:#555;'>{row['Icon']} {row['Name']}</div>", unsafe_allow_html=True)
            with c2:
                if st.button("↩️", key=f"rs_{idx}"):
                    habits_df.at[idx,"Active"] = 1
                    st.session_state.habits_df = habits_df
                    write_sheet(SHEET_HABITS, habits_df); st.rerun()

    st.markdown("<div class='section-title'>Export</div>", unsafe_allow_html=True)
    log_df = st.session_state.log_df
    if not log_df.empty:
        st.download_button("📥 Download Log CSV", data=log_df.to_csv(index=False),
                           file_name="habittrack_log.csv", mime="text/csv", use_container_width=True)

    st.markdown("<div class='section-title'>Security</div>", unsafe_allow_html=True)
    st.markdown("<div style='background:#161616;border:1px solid #222;border-radius:14px;padding:14px;'>", unsafe_allow_html=True)
    new_pin = st.text_input("New PIN (4 digits, blank = disabled)", key="new_pin",
                            type="password", max_chars=4, placeholder="••••")
    if st.button("Set PIN", key="set_pin", use_container_width=True):
        if new_pin and (not new_pin.isdigit() or len(new_pin) != 4):
            st.warning("PIN must be exactly 4 digits.")
        else:
            st.session_state.pin_hash = new_pin
            write_sheet(SHEET_SECURITY, pd.DataFrame({"PIN":[new_pin]}))
            st.success("PIN updated!" if new_pin else "PIN disabled."); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title'>Danger Zone</div>", unsafe_allow_html=True)
    if st.button("🗑️ Clear All Log Data", key="clear_log", use_container_width=True):
        if st.session_state.get("confirm_clear"):
            empty = pd.DataFrame(columns=["Date","Habit","Completed","Note","TimestampLogged"])
            st.session_state.log_df = empty
            write_sheet(SHEET_LOG, empty)
            st.session_state.confirm_clear = False
            st.success("Log cleared."); st.rerun()
        else:
            st.session_state.confirm_clear = True
            st.warning("⚠️ Click again to confirm — this cannot be undone.")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    inject_css()

    # Default session state
    for key, val in [
        ("bootstrapped", False), ("active_tab", 0),
        ("authenticated", False), ("pin_entered", ""),
        ("pin_attempts", 0),
    ]:
        if key not in st.session_state:
            st.session_state[key] = val

    if not st.session_state.bootstrapped:
        bootstrap_session()

    show_pin_gate()

    tab = st.session_state.active_tab
    if   tab == 0: tab_today()
    elif tab == 1: tab_dashboard()
    elif tab == 2: tab_calendar()
    elif tab == 3: tab_stats()
    elif tab == 4: tab_habits()
    elif tab == 5: tab_manage()

    render_nav()


if __name__ == "__main__":
    main()
