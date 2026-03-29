import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import json, uuid, calendar
import plotly.graph_objects as go

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HabitTracker",
    page_icon=":fire:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── DESIGN TOKENS ─────────────────────────────────────────────────────────────
C = {
    "bg":          "#0d1117",
    "surface":     "#161b22",
    "surface2":    "#1c2333",
    "border":      "#30363d",
    "primary":     "#7c6df8",
    "primary_dim": "rgba(124,109,248,0.12)",
    "income":      "#00c896",
    "expense":     "#ff4f6d",
    "warning":     "#f0a500",
    "info":        "#58a6ff",
    "text":        "#e6edf3",
    "muted":       "#8b949e",
    "success":     "#3fb950",
    "streak":      "#f97316",
}

# ── GOOGLE SHEETS ──────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SPREADSHEET_NAME = "ClearSpend"

HABIT_HEADERS = ["HabitID", "Name", "Icon", "Order", "CreatedDate", "Active"]
LOG_HEADERS   = ["LogID", "Date", "HabitID", "HabitName"]


# ═══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS CONNECTION
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_resource
def get_ss():
    client = get_client()
    try:
        return client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        ss = client.create(SPREADSHEET_NAME)
        return ss

def ensure_habit_sheets():
    ss = get_ss()
    existing = [ws.title for ws in ss.worksheets()]
    if "Habits" not in existing:
        ws = ss.add_worksheet(title="Habits", rows=500, cols=len(HABIT_HEADERS))
        ws.append_row(HABIT_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})
    if "HabitLogs" not in existing:
        ws = ss.add_worksheet(title="HabitLogs", rows=5000, cols=len(LOG_HEADERS))
        ws.append_row(LOG_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})


# ═══════════════════════════════════════════════════════════════════════════════
#  CRUD — HABITS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=15)
def load_habits() -> pd.DataFrame:
    ss = get_ss()
    data = ss.worksheet("Habits").get_all_records()
    if not data:
        return pd.DataFrame(columns=HABIT_HEADERS)
    df = pd.DataFrame(data)
    df["Order"]  = pd.to_numeric(df["Order"], errors="coerce").fillna(99).astype(int)
    df["Active"] = df["Active"].astype(str).str.upper().isin(["TRUE", "YES", "1"])
    return df.sort_values("Order").reset_index(drop=True)

@st.cache_data(ttl=15)
def load_logs(days_back: int = 25) -> pd.DataFrame:
    ss = get_ss()
    data = ss.worksheet("HabitLogs").get_all_records()
    if not data:
        return pd.DataFrame(columns=LOG_HEADERS)
    df = pd.DataFrame(data)
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    df = df[df["Date"] >= cutoff]
    return df.reset_index(drop=True)

def write_log(habit_id: str, habit_name: str, log_date: str):
    ss = get_ss()
    ws = ss.worksheet("HabitLogs")
    all_data = ws.get_all_records()
    for row in all_data:
        if str(row.get("Date", "")) == log_date and str(row.get("HabitID", "")) == habit_id:
            return
    ws.append_row([str(uuid.uuid4())[:8], log_date, habit_id, habit_name])
    st.cache_data.clear()

def delete_log(habit_id: str, log_date: str):
    ss = get_ss()
    ws = ss.worksheet("HabitLogs")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    date_col = hdrs.index("Date")    if "Date"    in hdrs else 1
    id_col   = hdrs.index("HabitID") if "HabitID" in hdrs else 2
    for i, row in enumerate(all_vals[1:], start=2):
        if len(row) > max(date_col, id_col):
            if row[date_col] == log_date and row[id_col] == habit_id:
                ws.delete_rows(i)
                st.cache_data.clear()
                return

def write_habit(name: str, icon: str, order: int):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    ws.append_row([str(uuid.uuid4())[:8], name.strip(), icon.strip() or "🎯",
                   order, date.today().isoformat(), "TRUE"])
    st.cache_data.clear()

def update_habit_order(habit_id: str, new_order: int):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col  = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    ord_col = hdrs.index("Order")   if "Order"   in hdrs else 3
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == habit_id:
            ws.update_cell(i, ord_col + 1, new_order)
            break
    st.cache_data.clear()

def toggle_habit_active(habit_id: str, current_active: bool):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col  = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    act_col = hdrs.index("Active")  if "Active"  in hdrs else 5
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == habit_id:
            ws.update_cell(i, act_col + 1, "FALSE" if current_active else "TRUE")
            break
    st.cache_data.clear()

def delete_habit(habit_id: str):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == habit_id:
            ws.delete_rows(i)
            break
    st.cache_data.clear()

def swap_habit_orders(id_a: str, order_a: int, id_b: str, order_b: int):
    ss = get_ss()
    ws = ss.worksheet("Habits")
    all_vals = ws.get_all_values()
    hdrs = all_vals[0]
    id_col  = hdrs.index("HabitID") if "HabitID" in hdrs else 0
    ord_col = hdrs.index("Order")   if "Order"   in hdrs else 3
    rows_to_update = {}
    for i, row in enumerate(all_vals[1:], start=2):
        if row[id_col] == id_a:
            rows_to_update[id_a] = i
        if row[id_col] == id_b:
            rows_to_update[id_b] = i
        if len(rows_to_update) == 2:
            break
    if id_a in rows_to_update:
        ws.update_cell(rows_to_update[id_a], ord_col + 1, order_b)
    if id_b in rows_to_update:
        ws.update_cell(rows_to_update[id_b], ord_col + 1, order_a)
    st.cache_data.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_daily_score(target_date: date, active_habits: pd.DataFrame,
                        logs_df: pd.DataFrame) -> float | None:
    date_str   = target_date.isoformat()
    applicable = active_habits[active_habits["CreatedDate"] <= date_str]
    total = len(applicable)
    if total == 0:
        return None
    if logs_df.empty:
        return 0.0
    day_logs       = logs_df[logs_df["Date"] == date_str]
    completed_ids  = set(day_logs["HabitID"].astype(str).tolist())
    applicable_ids = set(applicable["HabitID"].astype(str).tolist())
    done = len(completed_ids & applicable_ids)
    return round(done / total * 100, 1)

def compute_21day_scores(active_habits: pd.DataFrame,
                         logs_df: pd.DataFrame) -> pd.DataFrame:
    today = date.today()
    rows  = []
    for i in range(20, -1, -1):
        d     = today - timedelta(days=i)
        score = compute_daily_score(d, active_habits, logs_df)
        rows.append({"Date": d, "Score": score})
    return pd.DataFrame(rows)

def compute_habit_streak(habit_id: str, logs_df: pd.DataFrame) -> int:
    today = date.today()
    if logs_df.empty:
        return 0
    completed_dates = set(
        logs_df[logs_df["HabitID"].astype(str) == habit_id]["Date"].tolist()
    )
    streak = 0
    check  = today
    while True:
        if check.isoformat() in completed_dates:
            streak += 1
            check  -= timedelta(days=1)
        else:
            break
    return streak

def compute_overall_streak(active_habits: pd.DataFrame, logs_df: pd.DataFrame) -> int:
    today  = date.today()
    streak = 0
    check  = today
    for _ in range(365):
        score = compute_daily_score(check, active_habits, logs_df)
        if score is None:
            break
        if score == 100.0:
            streak += 1
            check  -= timedelta(days=1)
        else:
            break
    return streak

def get_today_status(active_habits: pd.DataFrame, logs_df: pd.DataFrame):
    today_str = date.today().isoformat()
    if logs_df.empty:
        return 0, len(active_habits), set()
    today_logs    = logs_df[logs_df["Date"] == today_str]
    completed_ids = set(today_logs["HabitID"].astype(str).tolist())
    total         = len(active_habits)
    done          = len(completed_ids & set(active_habits["HabitID"].astype(str).tolist()))
    return done, total, completed_ids


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _make_7day_dots(habit_id: str, created_date: str,
                    logs_df: pd.DataFrame, today: date) -> str:
    """7 small coloured circles: green=done, red=missed, grey=pending/N/A."""
    completed_dates: set[str] = set()
    if not logs_df.empty:
        completed_dates = set(
            logs_df[logs_df["HabitID"].astype(str) == habit_id]["Date"].tolist()
        )

    dots = []
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.isoformat()
        if d_str < created_date:
            bg, title = C["surface2"], "N/A"
            opacity   = "0.25"
        elif d_str in completed_dates:
            bg, title = C["income"], "Done"
            opacity   = "1"
        elif d == today:
            bg, title = C["border"], "Pending"
            opacity   = "1"
        else:
            bg, title = C["expense"], "Missed"
            opacity   = "0.55"

        day_label = d.strftime("%a")
        dots.append(
            f'<span title="{day_label}: {title}" style="'
            f'width:7px;height:7px;border-radius:50%;'
            f'background:{bg};opacity:{opacity};'
            f'display:inline-block;flex-shrink:0;'
            f'cursor:default"></span>'
        )

    return (
        '<div style="display:flex;gap:3px;align-items:center">'
        + "".join(dots)
        + "</div>"
    )


def _week_completion_pct(active_habits: pd.DataFrame, logs_df: pd.DataFrame) -> int:
    """% of habit-days completed in the last 7 days."""
    today      = date.today()
    total_opp  = 0
    total_done = 0
    for i in range(6, -1, -1):
        d       = today - timedelta(days=i)
        d_str   = d.isoformat()
        applic  = active_habits[active_habits["CreatedDate"] <= d_str]
        if applic.empty:
            continue
        total_opp += len(applic)
        if not logs_df.empty:
            day_done = set(
                logs_df[logs_df["Date"] == d_str]["HabitID"].astype(str).tolist()
            )
            total_done += len(day_done & set(applic["HabitID"].astype(str).tolist()))
    return round(total_done / total_opp * 100) if total_opp else 0


# ═══════════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

*, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background:{C["bg"]} !important;
    color:{C["text"]};
    font-family:'Nunito', sans-serif;
}}

[data-testid="stAppViewContainer"] > .main {{
    max-width:480px; margin:0 auto; padding:0 0 80px 0 !important;
}}
.block-container {{
    padding:0 12px 80px !important; max-width:480px !important;
}}

[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="collapsedControl"],
[data-testid="stSidebar"],
footer, #MainMenu {{ display:none !important; }}

/* ── CARDS ── */
.card {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:16px; padding:16px; margin:8px 0;
}}
.card-sm {{
    background:{C["surface"]}; border:1px solid {C["border"]};
    border-radius:12px; padding:12px 14px; margin:4px 0;
}}

/* ── TYPOGRAPHY ── */
.page-title {{
    font-size:1.3rem; font-weight:900; color:{C["text"]}; padding:12px 4px 2px;
}}
.section-label {{
    font-size:.62rem; font-weight:800; letter-spacing:1.5px;
    text-transform:uppercase; color:{C["muted"]}; margin:12px 0 6px 2px;
}}
.mono {{ font-family:'JetBrains Mono',monospace; font-weight:600; }}

/* ── SLIM HEADER ── */
.slim-header {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px;
    padding:12px 14px;
    margin:10px 0 6px;
}}

/* ── PROGRESS BAR ── */
.bar-wrap {{
    background:{C["surface2"]}; border-radius:100px;
    height:7px; overflow:hidden;
}}
.bar-fill {{
    height:100%; border-radius:100px; transition:width .5s ease;
}}

/* ── COMPACT HABIT TABLE ── */
.habit-table {{
    background:{C["surface"]};
    border:1px solid {C["border"]};
    border-radius:14px;
    overflow:hidden;
    margin:6px 0;
}}

/* Remove default Streamlit vertical gaps inside habit-table */
.habit-table > div > div > div[data-testid="stVerticalBlock"] {{
    gap:0 !important;
}}
.habit-table [data-testid="stHorizontalBlock"] {{
    gap:4px !important;
    align-items:center !important;
    padding:0 8px !important;
    border-bottom:1px solid {C["surface2"]};
    min-height:40px;
}}
.habit-table [data-testid="stHorizontalBlock"]:last-child {{
    border-bottom:none;
}}
.habit-table [data-testid="column"] {{
    padding:0 !important;
    overflow:visible !important;
}}

/* ── COMPACT ROW BODY ── */
.hrow {{
    display:flex;
    align-items:center;
    gap:7px;
    padding:5px 4px 5px 0;
    min-height:36px;
    overflow:hidden;
}}
.hrow.done {{
    opacity:.75;
}}
.hrow-name {{
    flex:1;
    font-size:.82rem;
    font-weight:700;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    min-width:0;
}}
.hrow-right {{
    display:flex;
    align-items:center;
    gap:5px;
    flex-shrink:0;
}}

/* ── STREAK BADGE ── */
.streak-badge {{
    background:rgba(249,115,22,0.15); color:#f97316;
    font-size:.58rem; font-weight:800;
    padding:2px 6px; border-radius:20px;
    white-space:nowrap; letter-spacing:.3px;
}}

/* ── ALL BUTTONS RESET ── */
[data-testid="stButton"] > button {{
    background:transparent !important;
    border:none !important; color:{C["muted"]} !important;
    font-family:'Nunito',sans-serif !important;
    font-size:.68rem !important; font-weight:700 !important;
    padding:4px 6px !important; border-radius:10px !important;
    width:100% !important; line-height:1.4 !important;
    white-space:nowrap !important; box-shadow:none !important;
    transition:color .2s, background .2s !important;
}}
[data-testid="stButton"] > button:hover {{
    color:{C["primary"]} !important;
    background:{C["primary_dim"]} !important;
}}

/* ── TOGGLE DONE ── */
.tog-done [data-testid="stButton"] > button {{
    background:rgba(0,200,150,0.18) !important;
    color:{C["income"]} !important;
    border:1.5px solid {C["income"]} !important;
    border-radius:50% !important;
    width:30px !important; height:30px !important;
    font-size:.9rem !important; padding:0 !important;
    min-height:unset !important;
}}

/* ── TOGGLE PENDING ── */
.tog-pend [data-testid="stButton"] > button {{
    background:{C["surface2"]} !important;
    color:{C["muted"]} !important;
    border:1.5px solid {C["border"]} !important;
    border-radius:50% !important;
    width:30px !important; height:30px !important;
    font-size:.9rem !important; padding:0 !important;
    min-height:unset !important;
}}
.tog-pend [data-testid="stButton"] > button:hover {{
    border-color:{C["income"]} !important;
    color:{C["income"]} !important;
    background:rgba(0,200,150,0.08) !important;
}}

/* ── PRIMARY / FORM SUBMIT ── */
[data-testid="stFormSubmitButton"] > button,
[data-testid="stButton"] > button[kind="primary"] {{
    background:{C["primary"]} !important;
    color:white !important; border-radius:12px !important;
    font-size:.9rem !important; font-weight:800 !important;
    padding:10px 16px !important;
    box-shadow:0 3px 12px rgba(124,109,248,.4) !important;
}}

/* ── REORDER BUTTONS ── */
.reorder-btn [data-testid="stButton"] > button {{
    background:{C["surface2"]} !important;
    color:{C["muted"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:8px !important;
    font-size:.8rem !important;
    padding:2px 6px !important;
    width:32px !important; height:32px !important;
    min-height:unset !important;
}}
.reorder-btn [data-testid="stButton"] > button:hover {{
    border-color:{C["primary"]} !important;
    color:{C["primary"]} !important;
}}

/* ── DELETE ── */
.del-btn [data-testid="stButton"] > button {{
    background:rgba(255,79,109,.1) !important;
    color:{C["expense"]} !important;
    border:1px solid rgba(255,79,109,.3) !important;
    border-radius:8px !important;
    font-size:.72rem !important;
    padding:3px 8px !important;
    width:auto !important;
}}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {{
    background:{C["surface2"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:10px !important;
    color:{C["text"]} !important;
    font-family:'Nunito',sans-serif !important;
    font-size:.9rem !important;
}}
[data-testid="stSelectbox"] > div > div {{
    background:{C["surface2"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:10px !important;
    color:{C["text"]} !important;
}}

/* ── EXPANDER ── */
[data-testid="stExpander"] {{
    background:{C["surface"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:12px !important;
    margin:6px 0 !important;
}}
[data-testid="stExpander"] summary {{
    color:{C["text"]} !important; font-weight:700 !important;
    font-size:.82rem !important;
    padding:8px 12px !important;
}}

/* ── ALERTS / HR ── */
[data-testid="stAlert"] {{ border-radius:12px !important; border:none !important; }}
hr {{ border-color:{C["border"]} !important; margin:12px 0 !important; }}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {{ width:3px; }}
::-webkit-scrollbar-thumb {{ background:{C["border"]}; border-radius:2px; }}

/* ── NAV DROPDOWN ── */
div[data-key="habit_nav_dd"] > div > div > div {{
    background:rgba(124,109,248,0.12) !important;
    border:1px solid #7c6df8 !important;
    border-radius:10px !important;
    font-weight:800 !important; font-size:.82rem !important;
}}

/* ── LOG DATE PICKER LABEL ── */
[data-testid="stDateInput"] label {{
    font-size:.72rem !important;
    color:{C["muted"]} !important;
}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_state():
    defaults = {
        "habit_nav":   "today",
        "setup_ok":    False,
        "confirm_del": None,
        "log_date":    date.today(),  # for backdating logs
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_top_bar():
    NAV = {"today": "🔥 Today", "manage": "⚙️ Manage"}
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        current = NAV.get(st.session_state.habit_nav, "🔥 Today")
        choice  = st.selectbox("", list(NAV.values()),
                               index=list(NAV.values()).index(current),
                               key="habit_nav_dd", label_visibility="collapsed")
        chosen_key = [k for k, v in NAV.items() if v == choice][0]
        if chosen_key != st.session_state.habit_nav:
            st.session_state.habit_nav = chosen_key
            st.rerun()
    with c2:
        if st.button("🔄", key="habit_reload", help="Refresh"):
            st.cache_data.clear()
            st.rerun()
    with c3:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — TODAY
# ═══════════════════════════════════════════════════════════════════════════════

def screen_today():
    habits_df = load_habits()
    logs_df   = load_logs(days_back=25)
    active    = habits_df[habits_df["Active"] == True].copy()
    today     = date.today()
    today_str = today.isoformat()

    # Which date are we logging for?
    log_date     = st.session_state.log_date
    log_date_str = log_date.isoformat()
    is_today     = (log_date == today)

    # ── SLIM HEADER ─────────────────────────────────────────────────────────
    hour     = datetime.now().hour
    greeting = "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening"
    dow      = today.strftime("%a, %d %b")

    done_count, total_count, completed_ids_today = get_today_status(active, logs_df)
    today_score    = round(done_count / total_count * 100) if total_count > 0 else 0
    overall_streak = compute_overall_streak(active, logs_df)
    week_pct       = _week_completion_pct(active, logs_df)

    bar_color = (C["income"] if today_score == 100
                 else C["primary"] if today_score >= 50
                 else C["warning"])

    celebrate = " 🎉" if (total_count > 0 and done_count == total_count) else ""

    st.markdown(f"""
    <div class="slim-header">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div style="font-size:1.05rem;font-weight:900;color:{C['text']}">
                Good {greeting} 🔥{celebrate}
            </div>
            <div style="font-size:.7rem;color:{C['muted']};font-weight:600">{dow}</div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <div class="bar-wrap" style="flex:1">
                <div class="bar-fill" style="width:{today_score}%;background:{bar_color}"></div>
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:.78rem;font-weight:700;
                 color:{bar_color};white-space:nowrap">{done_count}/{total_count}</div>
            <div style="font-size:.73rem;color:{C['streak']};white-space:nowrap;font-weight:800">
                🔥{overall_streak}d
            </div>
        </div>
        <div style="display:flex;gap:12px">
            <div style="font-size:.65rem;color:{C['muted']}">
                Week
                <span style="color:{C['primary']};font-weight:800;margin-left:3px">{week_pct}%</span>
            </div>
            <div style="font-size:.65rem;color:{C['muted']}">
                Today
                <span style="color:{bar_color};font-weight:800;margin-left:3px">{today_score}%</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    if active.empty:
        st.markdown(f"""
        <div class="card" style="text-align:center;padding:40px 20px">
            <div style="font-size:2.5rem">🌱</div>
            <div style="font-weight:800;font-size:1rem;margin:10px 0">No habits yet</div>
            <div style="color:{C['muted']};font-size:.82rem">
                Go to ⚙️ Manage to add your first habit
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── DATE SELECTOR (back-log) ─────────────────────────────────────────────
    with st.expander("📅 Log for a different date", expanded=not is_today):
        picked = st.date_input(
            "Select date",
            value=log_date,
            max_value=today,
            key="date_picker_input",
            label_visibility="collapsed",
        )
        if picked != log_date:
            st.session_state.log_date = picked
            st.rerun()
        if not is_today:
            st.markdown(
                f'<div style="font-size:.72rem;color:{C["warning"]};margin-top:4px">'
                f'Logging for {log_date.strftime("%d %b %Y")} — not today</div>',
                unsafe_allow_html=True,
            )
            if st.button("↩ Back to today", key="back_today"):
                st.session_state.log_date = today
                st.rerun()

    # ── RESOLVE completed_ids FOR THE CHOSEN DATE ────────────────────────────
    if is_today:
        completed_ids = completed_ids_today
    else:
        if logs_df.empty:
            completed_ids = set()
        else:
            day_logs      = logs_df[logs_df["Date"] == log_date_str]
            completed_ids = set(day_logs["HabitID"].astype(str).tolist())

    # ── SECTION LABEL WITH DAY DOTS LEGEND ──────────────────────────────────
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin:10px 2px 4px">'
        f'<div class="section-label" style="margin:0">Today\'s Habits</div>'
        f'<div style="display:flex;align-items:center;gap:8px;font-size:.6rem;color:{C["muted"]}">'
        f'<span style="display:flex;align-items:center;gap:3px">'
        f'<span style="width:7px;height:7px;background:{C["income"]};border-radius:50%;display:inline-block"></span>done</span>'
        f'<span style="display:flex;align-items:center;gap:3px">'
        f'<span style="width:7px;height:7px;background:{C["expense"]};opacity:.55;border-radius:50%;display:inline-block"></span>missed</span>'
        f'<span style="font-size:.55rem;color:{C["muted"]}">← 7d</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── COMPACT HABIT TABLE ──────────────────────────────────────────────────
    st.markdown('<div class="habit-table">', unsafe_allow_html=True)

    for _, habit in active.iterrows():
        h_id      = str(habit["HabitID"])
        h_name    = str(habit["Name"])
        h_icon    = str(habit["Icon"]) or "🎯"
        h_created = str(habit["CreatedDate"])
        is_done   = h_id in completed_ids
        streak    = compute_habit_streak(h_id, logs_df)
        dots_html = _make_7day_dots(h_id, h_created, logs_df, today)

        col_body, col_tog = st.columns([7, 1])

        with col_body:
            name_style  = (
                f"color:{C['income']};text-decoration:line-through"
                if is_done else f"color:{C['text']}"
            )
            streak_html = (
                f'<span class="streak-badge">🔥{streak}d</span>'
                if streak > 0 else ""
            )
            st.markdown(f"""
            <div class="hrow {'done' if is_done else ''}">
                <span style="font-size:.9rem;flex-shrink:0">{h_icon}</span>
                <span class="hrow-name" style="{name_style}">{h_name}</span>
                <div class="hrow-right">
                    {streak_html}
                    {dots_html}
                </div>
            </div>""", unsafe_allow_html=True)

        with col_tog:
            if is_done:
                st.markdown('<div class="tog-done">', unsafe_allow_html=True)
                if st.button("✓", key=f"tog_{h_id}_{log_date_str}"):
                    delete_log(h_id, log_date_str)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="tog-pend">', unsafe_allow_html=True)
                if st.button("○", key=f"tog_{h_id}_{log_date_str}"):
                    write_log(h_id, h_name, log_date_str)
                    st.toast(f"✓ {h_name}", icon="🎯")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # /habit-table

    # ── 21-DAY TREND (collapsed) ─────────────────────────────────────────────
    with st.expander("📊 21-day trend"):
        scores_df = compute_21day_scores(active, logs_df)
        valid     = scores_df.dropna(subset=["Score"])

        if valid.empty:
            st.markdown(
                f'<div style="text-align:center;padding:20px;color:{C["muted"]};'
                f'font-size:.82rem">Complete habits to see your trend</div>',
                unsafe_allow_html=True,
            )
        else:
            x_dates  = valid["Date"].astype(str).tolist()
            y_scores = valid["Score"].tolist()

            point_colors = [
                C["income"]  if s == 100 else
                C["primary"] if s >= 70  else
                C["warning"] if s >= 40  else
                C["expense"]
                for s in y_scores
            ]

            today_idx = [i for i, d in enumerate(x_dates) if d == today_str]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=x_dates, y=y_scores,
                mode="lines",
                line=dict(color=C["primary"], width=2),
                fill="tozeroy", fillcolor="rgba(124,109,248,0.07)",
                hovertemplate="%{x}<br>%{y:.0f}%<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=x_dates, y=y_scores, mode="markers",
                marker=dict(
                    color=point_colors,
                    size=[9 if i in today_idx else 5 for i in range(len(x_dates))],
                    line=dict(color=C["bg"], width=1.5),
                ),
                hovertemplate="%{x}<br>%{y:.0f}%<extra></extra>",
            ))
            fig.add_hline(y=100, line_dash="dot", line_color=C["income"],
                          line_width=1, opacity=0.25)
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color=C["text"],
                showlegend=False,
                height=170,
                margin=dict(l=4, r=4, t=8, b=4),
                xaxis=dict(
                    gridcolor=C["border"],
                    tickfont=dict(color=C["muted"], size=7),
                    showgrid=False,
                    tickmode="array",
                    tickvals=[x_dates[0], x_dates[len(x_dates)//2], x_dates[-1]],
                    ticktext=[
                        pd.Timestamp(x_dates[0]).strftime("%d %b"),
                        pd.Timestamp(x_dates[len(x_dates)//2]).strftime("%d %b"),
                        "Today",
                    ],
                ),
                yaxis=dict(
                    gridcolor=C["border"],
                    tickfont=dict(color=C["muted"], size=7),
                    range=[-5, 110], ticksuffix="%",
                ),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — MANAGE
# ═══════════════════════════════════════════════════════════════════════════════

def screen_manage():
    habits_df = load_habits()

    st.markdown('<div class="page-title">Manage Habits ⚙️</div>', unsafe_allow_html=True)

    # ── ADD NEW HABIT ────────────────────────────────────────────────────────
    with st.expander("➕  Add New Habit", expanded=habits_df.empty):
        st.markdown(
            f"<div style='color:{C['muted']};font-size:.78rem;margin-bottom:8px'>"
            f"Order 1 = first thing in your morning.</div>",
            unsafe_allow_html=True,
        )
        with st.form("add_habit_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                new_name = st.text_input("Habit Name *",
                                         placeholder="e.g. Drink a bottle of water")
            with c2:
                new_icon = st.text_input("Icon", value="🎯")

            next_order = (int(habits_df["Order"].max()) + 1) if not habits_df.empty else 1
            new_order  = st.number_input("Position (Order)", value=next_order,
                                         min_value=1, step=1)

            submitted = st.form_submit_button("💾 Add Habit",
                                              use_container_width=True, type="primary")
            if submitted:
                if new_name.strip():
                    write_habit(new_name.strip(), new_icon.strip() or "🎯", int(new_order))
                    st.success(f"✅ Added: {new_icon} {new_name}")
                    st.rerun()
                else:
                    st.error("Enter a habit name.")

    if habits_df.empty:
        return

    # ── ACTIVE HABITS ────────────────────────────────────────────────────────
    active_df   = habits_df[habits_df["Active"] == True].reset_index(drop=True)
    inactive_df = habits_df[habits_df["Active"] == False].reset_index(drop=True)

    st.markdown('<div class="section-label">Active Habits</div>', unsafe_allow_html=True)

    for idx, habit in active_df.iterrows():
        h_id    = str(habit["HabitID"])
        h_name  = str(habit["Name"])
        h_icon  = str(habit["Icon"]) or "🎯"
        h_order = int(habit["Order"])

        st.markdown(f"""
        <div style="background:{C['surface2']};border:1px solid {C['border']};
             border-radius:12px;padding:8px 12px;margin:3px 0;
             display:flex;align-items:center;gap:10px">
            <span style="font-size:1rem;flex-shrink:0">{h_icon}</span>
            <div style="flex:1;min-width:0">
                <div style="font-weight:700;font-size:.82rem;white-space:nowrap;
                     overflow:hidden;text-overflow:ellipsis">{h_name}</div>
                <div style="font-size:.6rem;color:{C['muted']}">Position {h_order}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        bc1, bc2, bc3, bc4, bc5 = st.columns([1, 1, 1, 1, 2])

        with bc1:
            st.markdown('<div class="reorder-btn">', unsafe_allow_html=True)
            if st.button("↑", key=f"up_{h_id}", disabled=(idx == 0), help="Move up"):
                prev = active_df.iloc[idx - 1]
                swap_habit_orders(h_id, h_order, str(prev["HabitID"]), int(prev["Order"]))
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with bc2:
            st.markdown('<div class="reorder-btn">', unsafe_allow_html=True)
            if st.button("↓", key=f"dn_{h_id}", disabled=(idx == len(active_df) - 1),
                         help="Move down"):
                nxt = active_df.iloc[idx + 1]
                swap_habit_orders(h_id, h_order, str(nxt["HabitID"]), int(nxt["Order"]))
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with bc3:
            st.markdown('<div class="reorder-btn">', unsafe_allow_html=True)
            if st.button("⏸", key=f"dis_{h_id}", help="Pause habit"):
                toggle_habit_active(h_id, True)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with bc4:
            if st.session_state.confirm_del == h_id:
                st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                if st.button("✓ Sure?", key=f"confirm_{h_id}"):
                    delete_habit(h_id)
                    st.session_state.confirm_del = None
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="del-btn">', unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{h_id}", help="Delete"):
                    st.session_state.confirm_del = h_id
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        with bc5:
            if st.session_state.confirm_del == h_id:
                st.markdown(
                    f"<div style='font-size:.62rem;color:{C['expense']};padding:8px 0'>"
                    f"Deletes all logs too.</div>",
                    unsafe_allow_html=True,
                )

    # ── PAUSED ───────────────────────────────────────────────────────────────
    if not inactive_df.empty:
        st.markdown('<div class="section-label">Paused Habits</div>', unsafe_allow_html=True)
        for _, habit in inactive_df.iterrows():
            h_id   = str(habit["HabitID"])
            h_name = str(habit["Name"])
            h_icon = str(habit["Icon"]) or "🎯"

            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(f"""
                <div style="padding:6px 4px;display:flex;align-items:center;gap:8px;
                     opacity:0.45;border-bottom:1px solid {C['surface2']}">
                    <span style="font-size:.9rem">{h_icon}</span>
                    <span style="font-size:.8rem;color:{C['muted']}">{h_name}</span>
                </div>""", unsafe_allow_html=True)
            with col_btn:
                if st.button("▶ Resume", key=f"res_{h_id}"):
                    toggle_habit_active(h_id, False)
                    st.rerun()

    # ── QUICK STATS ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-label">Quick Stats</div>', unsafe_allow_html=True)
    logs_df = load_logs(days_back=30)
    if not logs_df.empty and not active_df.empty:
        scores_7 = [
            s for i in range(7)
            if (s := compute_daily_score(date.today() - timedelta(days=i),
                                         active_df, logs_df)) is not None
        ]
        avg_7             = round(sum(scores_7) / len(scores_7)) if scores_7 else 0
        total_completions = len(logs_df)

        qs1, qs2 = st.columns(2)
        with qs1:
            st.markdown(f"""
            <div class="card-sm" style="text-align:center">
                <div style="font-size:.58rem;color:{C['muted']};font-weight:800;
                       letter-spacing:.8px;text-transform:uppercase">7-Day Avg</div>
                <div class="mono" style="font-size:1.2rem;color:{C['primary']}">{avg_7}%</div>
            </div>""", unsafe_allow_html=True)
        with qs2:
            st.markdown(f"""
            <div class="card-sm" style="text-align:center">
                <div style="font-size:.58rem;color:{C['muted']};font-weight:800;
                       letter-spacing:.8px;text-transform:uppercase">Total ✓</div>
                <div class="mono" style="font-size:1.2rem;color:{C['income']}">{total_completions}</div>
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SETUP
# ═══════════════════════════════════════════════════════════════════════════════

def run_setup():
    if not st.session_state.setup_ok:
        with st.spinner("⚡ Setting up HabitTracker..."):
            try:
                ensure_habit_sheets()
                st.session_state.setup_ok = True
            except Exception as ex:
                st.error(f"**Setup failed:** {ex}")
                st.markdown("""
**What to check:**
1. `GOOGLE_CREDENTIALS` secret is set in Streamlit Cloud → App Settings → Secrets.
2. The same service account used for ClearSpend will work here.
3. The spreadsheet name in this file is `ClearSpend` — same as your main app.
""")
                st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_state()
    inject_css()
    run_setup()
    render_top_bar()

    if st.session_state.habit_nav == "today":
        screen_today()
    elif st.session_state.habit_nav == "manage":
        screen_manage()


if __name__ == "__main__":
    main()
