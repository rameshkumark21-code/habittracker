import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
import json, uuid

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Habits",
    page_icon=":fire:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── DESIGN TOKENS ─────────────────────────────────────────────────────────────
C = {
    "bg":      "#1a1a1a",
    "surface": "#242424",
    "s2":      "#2d2d2d",
    "s3":      "#363636",
    "border":  "#3d3d3d",
    "text":    "#f0f0f0",
    "muted":   "#888888",
    "blue":    "#5b8dee",
    "green":   "#00c896",
    "red":     "#e84855",
    "amber":   "#f0a500",
    "streak":  "#f97316",
    "dim":     "rgba(91,141,238,0.12)",
}

# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────
SCOPES           = ["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "ClearSpend"

HABIT_HEADERS = ["HabitID", "Name", "Icon", "Category", "Type",
                 "Target", "TargetUnit", "FreqType", "WeekDay", "Order", "Active"]
LOG_HEADERS   = ["LogID", "Date", "HabitID", "HabitName", "Value"]

CATEGORIES = ["Daily", "Nutrition & Movement", "Workout Days", "Weekly"]

CAT_ICONS = {
    "Daily":                "Sun",
    "Nutrition & Movement": "Leaf",
    "Workout Days":         "Bolt",
    "Weekly":               "Cal",
}

# ── SEED HABITS ────────────────────────────────────────────────────────────────
HABIT_SEEDS = [
    ["h01", "500ml water on waking",     "W", "Daily",                "boolean", "1",   "",       "daily",  "",    1,  "TRUE"],
    ["h02", "Morning mobility 15 min",   "M", "Daily",                "boolean", "1",   "",       "daily",  "",    2,  "TRUE"],
    ["h03", "Protein-first breakfast",   "B", "Daily",                "boolean", "1",   "",       "daily",  "",    3,  "TRUE"],
    ["h04", "Pre-sleep stretch",         "S", "Daily",                "boolean", "1",   "",       "daily",  "",    4,  "TRUE"],
    ["h05", "In bed by 12:30 AM",        "Z", "Daily",                "boolean", "1",   "",       "daily",  "",    5,  "TRUE"],
    ["h06", "1-Floor Rule (stairs)",     "1", "Daily",                "boolean", "1",   "",       "daily",  "",    6,  "TRUE"],
    ["h07", "50/5 Rule (breaks)",        "5", "Nutrition & Movement", "numeric", "5",   "breaks", "daily",  "",    7,  "TRUE"],
    ["h08", "Protein intake",            "P", "Nutrition & Movement", "numeric", "140", "g",      "daily",  "",    8,  "TRUE"],
    ["h09", "Floors climbed",            "F", "Nutrition & Movement", "numeric", "10",  "floors", "daily",  "",    9,  "TRUE"],
    ["h10", "Workout before 10 AM",      "W", "Workout Days",         "boolean", "1",   "",       "daily",  "",    10, "TRUE"],
    ["h11", "Foam rolling done",         "R", "Workout Days",         "boolean", "1",   "",       "daily",  "",    11, "TRUE"],
    ["h12", "Post-workout protein",      "P", "Workout Days",         "boolean", "1",   "",       "daily",  "",    12, "TRUE"],
    ["h13", "Long walk 45-60 min",       "L", "Weekly",               "boolean", "1",   "",       "weekly", "Sun", 13, "TRUE"],
    ["h14", "Flexibility / yoga",        "Y", "Weekly",               "boolean", "1",   "",       "weekly", "Sat", 14, "TRUE"],
    ["h15", "Weekly stair test",         "T", "Weekly",               "boolean", "1",   "",       "weekly", "Sun", 15, "TRUE"],
]


# ═══════════════════════════════════════════════════════════════════════════════
#  DATE HELPERS  — store DD/MM/YYYY in GSheets, work in ISO internally
# ═══════════════════════════════════════════════════════════════════════════════

def iso_to_dmy(iso_str: str) -> str:
    return datetime.strptime(iso_str, "%Y-%m-%d").strftime("%d/%m/%Y")

def dmy_to_iso(dmy_str: str) -> str:
    return datetime.strptime(dmy_str, "%d/%m/%Y").strftime("%Y-%m-%d")

def _rolling_days(n: int = 5) -> list:
    today = date.today()
    return [today - timedelta(days=n - 1 - i) for i in range(n)]

def _day_label(d: date, today: date) -> str:
    suffix = " *" if d == today else ""
    return f"{d.strftime('%a').upper()} {d.day}{suffix}"


# ═══════════════════════════════════════════════════════════════════════════════
#  GOOGLE SHEETS
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
        return client.create(SPREADSHEET_NAME)

def ensure_habit_sheets():
    ss       = get_ss()
    existing = [ws.title for ws in ss.worksheets()]

    # Habits tab — check for new schema
    if "Habits" in existing:
        ws  = ss.worksheet("Habits")
        hdr = ws.row_values(1)
        if "Category" not in hdr:
            ss.del_worksheet(ws)
            existing.remove("Habits")

    if "Habits" not in existing:
        ws = ss.add_worksheet(title="Habits", rows=200, cols=len(HABIT_HEADERS))
        ws.append_row(HABIT_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})
        for seed in HABIT_SEEDS:
            ws.append_row(seed)

    # HabitLogs tab — check for Value column
    if "HabitLogs" in existing:
        ws  = ss.worksheet("HabitLogs")
        hdr = ws.row_values(1)
        if "Value" not in hdr:
            ss.del_worksheet(ws)
            existing.remove("HabitLogs")

    if "HabitLogs" not in existing:
        ws = ss.add_worksheet(title="HabitLogs", rows=10000, cols=len(LOG_HEADERS))
        ws.append_row(LOG_HEADERS)
        ws.format("1:1", {"textFormat": {"bold": True}})


# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD DATA
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=20)
def load_habits() -> pd.DataFrame:
    ss   = get_ss()
    data = ss.worksheet("Habits").get_all_records()
    if not data:
        return pd.DataFrame(columns=HABIT_HEADERS)
    df = pd.DataFrame(data)
    df["Order"]  = pd.to_numeric(df["Order"],  errors="coerce").fillna(99).astype(int)
    df["Target"] = pd.to_numeric(df["Target"], errors="coerce").fillna(1)
    df["Active"] = df["Active"].astype(str).str.upper().isin(["TRUE", "YES", "1"])
    return df.sort_values("Order").reset_index(drop=True)

@st.cache_data(ttl=20)
def load_logs(days_back: int = 90) -> pd.DataFrame:
    ss   = get_ss()
    data = ss.worksheet("HabitLogs").get_all_records()
    if not data:
        return pd.DataFrame(columns=LOG_HEADERS)
    df      = pd.DataFrame(data)
    cutoff  = (date.today() - timedelta(days=days_back)).isoformat()
    def _keep(dmy):
        try:
            return dmy_to_iso(str(dmy)) >= cutoff
        except Exception:
            return False
    return df[df["Date"].apply(_keep)].reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  LOG CRUD  (date stored as DD/MM/YYYY)
# ═══════════════════════════════════════════════════════════════════════════════

def _find_log_row(ws_vals, hdrs, habit_id, date_dmy):
    try:
        dc = hdrs.index("Date")
        ic = hdrs.index("HabitID")
    except ValueError:
        return None
    for i, row in enumerate(ws_vals[1:], start=2):
        if len(row) > max(dc, ic) and row[dc] == date_dmy and row[ic] == habit_id:
            return i
    return None

def upsert_log(habit_id: str, habit_name: str, date_iso: str, value):
    """
    Persist a habit log.
    value: True/False for boolean  |  float for numeric  |  None to delete.
    """
    date_dmy = iso_to_dmy(date_iso)
    ss       = get_ss()
    ws       = ss.worksheet("HabitLogs")
    all_vals = ws.get_all_values()
    hdrs     = all_vals[0] if all_vals else LOG_HEADERS

    existing = _find_log_row(all_vals, hdrs, habit_id, date_dmy)

    # Compute stored string
    if value is None:
        stored = None
    elif isinstance(value, bool):
        stored = "1" if value else None
    else:
        try:
            f = float(value)
            stored = None if (f == 0 or pd.isna(f)) else str(f)
        except Exception:
            stored = None

    if stored is None:
        if existing:
            ws.delete_rows(existing)
            st.cache_data.clear()
        return

    try:
        vc = hdrs.index("Value")
    except ValueError:
        vc = 4

    if existing:
        ws.update_cell(existing, vc + 1, stored)
    else:
        ws.append_row([str(uuid.uuid4())[:8], date_dmy, habit_id, habit_name, stored])

    st.cache_data.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORE / STREAK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _done_dates(habit_id: str, logs_df: pd.DataFrame,
                h_type: str, target: float) -> set:
    if logs_df.empty:
        return set()
    rows = logs_df[logs_df["HabitID"].astype(str) == habit_id]
    out  = set()
    for _, r in rows.iterrows():
        try:
            d_iso = dmy_to_iso(str(r["Date"]))
            val   = float(r["Value"])
            if h_type == "boolean" and val >= 1:
                out.add(d_iso)
            elif h_type == "numeric" and val >= target:
                out.add(d_iso)
        except Exception:
            pass
    return out

def compute_streak(habit_id: str, logs_df: pd.DataFrame,
                   h_type: str, target: float) -> int:
    done   = _done_dates(habit_id, logs_df, h_type, target)
    today  = date.today()
    streak = 0
    check  = today
    for _ in range(365):
        if check.isoformat() in done:
            streak += 1
            check  -= timedelta(days=1)
        else:
            break
    return streak

def get_log_value(habit_id: str, date_iso: str, logs_df: pd.DataFrame, h_type: str):
    if logs_df.empty:
        return False if h_type == "boolean" else None
    dmy = iso_to_dmy(date_iso)
    row = logs_df[
        (logs_df["HabitID"].astype(str) == habit_id) &
        (logs_df["Date"].astype(str)    == dmy)
    ]
    if row.empty:
        return False if h_type == "boolean" else None
    try:
        val = float(row.iloc[0]["Value"])
        return (val >= 1) if h_type == "boolean" else val
    except Exception:
        return False if h_type == "boolean" else None

def today_completion(habits_df: pd.DataFrame, logs_df: pd.DataFrame):
    today_dmy  = iso_to_dmy(date.today().isoformat())
    active     = habits_df[habits_df["Active"] == True]
    if active.empty:
        return 0, 0
    total      = len(active)
    done       = 0
    today_logs = logs_df[logs_df["Date"] == today_dmy] if not logs_df.empty else pd.DataFrame()
    for _, h in active.iterrows():
        h_id   = str(h["HabitID"])
        h_type = str(h["Type"])
        target = float(h["Target"])
        log    = today_logs[today_logs["HabitID"].astype(str) == h_id] if not today_logs.empty else pd.DataFrame()
        if log.empty:
            continue
        try:
            val = float(log.iloc[0]["Value"])
            if (h_type == "boolean" and val >= 1) or (h_type == "numeric" and val >= target):
                done += 1
        except Exception:
            pass
    return done, total

def cat_completion(cat_habits: pd.DataFrame, logs_df: pd.DataFrame):
    today_dmy  = iso_to_dmy(date.today().isoformat())
    today_logs = logs_df[logs_df["Date"] == today_dmy] if not logs_df.empty else pd.DataFrame()
    total = len(cat_habits)
    done  = 0
    for _, h in cat_habits.iterrows():
        h_id   = str(h["HabitID"])
        h_type = str(h["Type"])
        target = float(h["Target"])
        log    = today_logs[today_logs["HabitID"].astype(str) == h_id] if not today_logs.empty else pd.DataFrame()
        if log.empty:
            continue
        try:
            val = float(log.iloc[0]["Value"])
            if (h_type == "boolean" and val >= 1) or (h_type == "numeric" and val >= target):
                done += 1
        except Exception:
            pass
    return done, total

def week_ring(habit_id: str, logs_df: pd.DataFrame, h_type: str, target: float) -> str:
    """7-char pattern oldest→today: ● done  ○ not done."""
    today = date.today()
    done  = _done_dates(habit_id, logs_df, h_type, target)
    return "".join(
        "●" if (today - timedelta(days=6 - i)).isoformat() in done else "○"
        for i in range(7)
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════════

def inject_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

*, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background:{C["bg"]} !important;
    color:{C["text"]};
    font-family:'Inter', sans-serif;
}}
[data-testid="stAppViewContainer"] > .main {{
    max-width:520px; margin:0 auto; padding:0 0 90px !important;
}}
.block-container {{
    padding:0 10px 90px !important; max-width:520px !important;
}}
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="collapsedControl"], [data-testid="stSidebar"],
footer, #MainMenu {{ display:none !important; }}

/* ── HEADER ── */
.top-hdr {{
    padding:12px 4px 10px;
    border-bottom:1px solid {C["border"]};
    margin-bottom:2px;
}}
.top-date {{
    font-size:.65rem; font-weight:600; color:{C["muted"]};
    letter-spacing:.7px; text-transform:uppercase;
}}
.top-greet {{
    font-size:1.15rem; font-weight:800; color:{C["text"]}; margin:2px 0 8px;
}}
.pbar-wrap {{
    background:{C["s2"]}; border-radius:100px; height:5px; overflow:hidden;
}}
.pbar-fill {{
    height:100%; border-radius:100px; transition:width .5s ease;
}}
.pbar-lbl {{
    display:flex; justify-content:space-between;
    font-size:.62rem; color:{C["muted"]}; margin-top:4px;
}}

/* ── SECTION DIVIDER ── */
.sdiv {{
    display:flex; align-items:center; gap:8px; margin:12px 0 4px;
}}
.sdiv-txt {{
    font-size:.6rem; font-weight:800; letter-spacing:1.5px;
    text-transform:uppercase; color:{C["muted"]}; white-space:nowrap;
}}
.sdiv-line {{ flex:1; height:1px; background:{C["border"]}; }}
.sdiv-badge {{
    font-size:.6rem; font-weight:700; padding:1px 8px;
    border-radius:20px; background:{C["s2"]}; white-space:nowrap;
}}

/* ── DATA EDITOR ── */
[data-testid="stDataEditor"] {{
    border:1px solid {C["border"]} !important;
    border-radius:10px !important;
    overflow:hidden;
    margin:0 0 4px;
}}
[data-testid="stDataEditor"] > div {{
    box-shadow:none !important; border:none !important;
}}

/* ── COMPLETION STRIP (fixed bottom) ── */
.cs {{
    position:fixed; bottom:0; left:50%; transform:translateX(-50%);
    width:100%; max-width:520px; z-index:999;
    background:{C["surface"]}; border-top:1px solid {C["border"]};
    padding:9px 16px 14px;
    display:flex; align-items:center; gap:14px;
}}
.cs-score {{
    font-family:'JetBrains Mono',monospace;
    font-size:1.1rem; font-weight:700; flex-shrink:0;
}}
.cs-bar-w {{
    flex:1; background:{C["s2"]}; border-radius:100px; height:7px; overflow:hidden;
}}
.cs-bar-f {{
    height:100%; border-radius:100px; transition:width .5s ease;
}}
.cs-lbl {{
    font-size:.62rem; color:{C["muted"]}; flex-shrink:0;
    font-family:'JetBrains Mono',monospace;
}}

/* ── NAV ── */
div[data-key="nav_dd"] > div > div > div {{
    background:{C["dim"]} !important;
    border:1px solid {C["blue"]} !important;
    border-radius:10px !important;
    font-weight:800 !important; font-size:.82rem !important;
}}

/* ── BUTTONS ── */
[data-testid="stButton"] > button {{
    background:transparent !important; border:none !important;
    color:{C["muted"]} !important; font-family:'Inter',sans-serif !important;
    font-size:.7rem !important; font-weight:700 !important;
    padding:4px 8px !important; border-radius:8px !important;
    width:100% !important; transition:color .15s, background .15s !important;
    box-shadow:none !important;
}}
[data-testid="stButton"] > button:hover {{
    color:{C["blue"]} !important; background:{C["dim"]} !important;
}}
[data-testid="stFormSubmitButton"] > button {{
    background:{C["blue"]} !important; color:#fff !important;
    border-radius:10px !important; font-weight:800 !important;
    font-size:.88rem !important; padding:9px 16px !important;
    box-shadow:0 2px 10px rgba(91,141,238,.3) !important;
}}

/* ── INPUTS ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    background:{C["s2"]} !important; border:1px solid {C["border"]} !important;
    border-radius:8px !important; color:{C["text"]} !important;
    font-family:'Inter',sans-serif !important;
}}
[data-testid="stSelectbox"] > div > div {{
    background:{C["s2"]} !important; border:1px solid {C["border"]} !important;
    border-radius:8px !important; color:{C["text"]} !important;
}}
[data-testid="stExpander"] {{
    background:{C["surface"]} !important;
    border:1px solid {C["border"]} !important;
    border-radius:10px !important; margin:4px 0 !important;
}}
[data-testid="stExpander"] summary {{
    color:{C["text"]} !important; font-weight:700 !important; font-size:.82rem !important;
}}
[data-testid="stAlert"] {{ border-radius:10px !important; border:none !important; }}
hr {{ border-color:{C["border"]} !important; margin:10px 0 !important; }}
::-webkit-scrollbar {{ width:3px; height:3px; }}
::-webkit-scrollbar-thumb {{ background:{C["border"]}; border-radius:2px; }}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_state():
    for k, v in {"nav": "today", "setup_ok": False, "confirm_del": None}.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_top_bar():
    NAV = {"today": "Today", "manage": "Manage"}
    c1, c2, _ = st.columns([4, 1, 1])
    with c1:
        current    = NAV.get(st.session_state.nav, "Today")
        choice     = st.selectbox("", list(NAV.values()),
                                  index=list(NAV.values()).index(current),
                                  key="nav_dd", label_visibility="collapsed")
        chosen_key = [k for k, v in NAV.items() if v == choice][0]
        if chosen_key != st.session_state.nav:
            st.session_state.nav = chosen_key
            st.rerun()
    with c2:
        if st.button("Sync", key="reload_btn"):
            st.cache_data.clear()
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  HABIT SECTION — 5-day data_editor grid
# ═══════════════════════════════════════════════════════════════════════════════

def _same_val(a, b, h_type: str) -> bool:
    if h_type == "boolean":
        return bool(a) == bool(b)
    a_n = a is None or (isinstance(a, float) and pd.isna(a))
    b_n = b is None or (isinstance(b, float) and pd.isna(b))
    if a_n and b_n:
        return True
    if a_n or b_n:
        return False
    try:
        return abs(float(a) - float(b)) < 1e-9
    except Exception:
        return False

def render_section(category: str, cat_habits: pd.DataFrame,
                   days: list, logs_df: pd.DataFrame, today: date):
    if cat_habits.empty:
        return

    h_type  = str(cat_habits.iloc[0]["Type"])
    done_n, total_n = cat_completion(cat_habits, logs_df)
    done_color = C["green"] if (done_n == total_n and total_n > 0) else C["muted"]

    # Section header
    st.markdown(f"""
    <div class="sdiv">
        <div class="sdiv-txt">{category}</div>
        <div class="sdiv-line"></div>
        <div class="sdiv-badge" style="color:{done_color}">{done_n}/{total_n} today</div>
    </div>""", unsafe_allow_html=True)

    # Build DataFrame
    day_isos   = [d.isoformat() for d in days]
    day_labels = [_day_label(d, today) for d in days]

    rows, habit_ids, habit_names, targets = [], [], [], []

    for _, habit in cat_habits.iterrows():
        h_id   = str(habit["HabitID"])
        h_name = str(habit["Name"])
        target = float(habit["Target"])
        h_unit = str(habit.get("TargetUnit", ""))
        streak = compute_streak(h_id, logs_df, h_type, target)
        ring   = week_ring(h_id, logs_df, h_type, target)

        tgt_txt = f" ({int(target)}{h_unit})" if h_type == "numeric" else ""
        row = {
            "Habit": f"{h_name}{tgt_txt}",
            "7d":    ring,
            "Str":   f"{streak}" if streak > 0 else "-",
        }
        for d_iso, lbl in zip(day_isos, day_labels):
            row[lbl] = get_log_value(h_id, d_iso, logs_df, h_type)

        rows.append(row)
        habit_ids.append(h_id)
        habit_names.append(h_name)
        targets.append(target)

    orig_df = pd.DataFrame(rows)

    # Column config
    col_cfg = {
        "Habit": st.column_config.TextColumn("Habit", disabled=True, width="large"),
        "7d":    st.column_config.TextColumn("7d",    disabled=True, width="small"),
        "Str":   st.column_config.TextColumn("Str",   disabled=True, width="small"),
    }
    for lbl in day_labels:
        if h_type == "boolean":
            col_cfg[lbl] = st.column_config.CheckboxColumn(lbl, width="small")
        else:
            col_cfg[lbl] = st.column_config.NumberColumn(
                lbl, min_value=0, format="%g", width="small"
            )

    edited_df = st.data_editor(
        orig_df,
        column_config=col_cfg,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        key=f"ed_{category}_{today.isoformat()}",
    )

    # Detect changes and persist
    changed = False
    for i in range(len(orig_df)):
        for d_iso, lbl in zip(day_isos, day_labels):
            o = orig_df.iloc[i][lbl]
            e = edited_df.iloc[i][lbl]
            if not _same_val(o, e, h_type):
                upsert_log(habit_ids[i], habit_names[i], d_iso, e)
                changed = True
    if changed:
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — TODAY
# ═══════════════════════════════════════════════════════════════════════════════

def screen_today():
    habits_df = load_habits()
    logs_df   = load_logs(days_back=90)
    active    = habits_df[habits_df["Active"] == True].copy()
    today     = date.today()

    # Header
    hour     = datetime.now().hour
    greeting = "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening"
    done_n, total_n = today_completion(active, logs_df)
    pct      = round(done_n / total_n * 100) if total_n > 0 else 0
    pct_col  = C["green"] if pct == 100 else C["blue"] if pct >= 50 else C["amber"]

    st.markdown(f"""
    <div class="top-hdr">
        <div class="top-date">{today.strftime("%A, %d %B %Y")}</div>
        <div class="top-greet">Good {greeting}</div>
        <div class="pbar-wrap">
            <div class="pbar-fill" style="width:{pct}%;background:{pct_col}"></div>
        </div>
        <div class="pbar-lbl">
            <span>Today's progress</span>
            <span style="color:{pct_col};font-weight:700">{done_n}/{total_n}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    if active.empty:
        st.info("No active habits. Go to Manage to add habits.")
        return

    days = _rolling_days(5)

    for cat in CATEGORIES:
        cat_habits = active[active["Category"] == cat].reset_index(drop=True)
        render_section(cat, cat_habits, days, logs_df, today)

    # Fixed bottom strip
    lbl = "All done!" if (total_n > 0 and done_n == total_n) else f"{pct}%"
    st.markdown(f"""
    <div class="cs">
        <div class="cs-score" style="color:{pct_col}">{lbl}</div>
        <div class="cs-bar-w">
            <div class="cs-bar-f" style="width:{pct}%;background:{pct_col}"></div>
        </div>
        <div class="cs-lbl">{done_n}/{total_n}</div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREEN — MANAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _toggle_active(habit_id: str, currently_active: bool):
    ss   = get_ss()
    ws   = ss.worksheet("Habits")
    vals = ws.get_all_values()
    hdrs = vals[0]
    try:
        ic = hdrs.index("HabitID")
        ac = hdrs.index("Active")
    except ValueError:
        return
    for i, row in enumerate(vals[1:], start=2):
        if len(row) > max(ic, ac) and row[ic] == habit_id:
            ws.update_cell(i, ac + 1, "FALSE" if currently_active else "TRUE")
            break
    st.cache_data.clear()

def _delete_habit(habit_id: str):
    ss   = get_ss()
    ws   = ss.worksheet("Habits")
    vals = ws.get_all_values()
    hdrs = vals[0]
    try:
        ic = hdrs.index("HabitID")
    except ValueError:
        return
    for i, row in enumerate(vals[1:], start=2):
        if len(row) > ic and row[ic] == habit_id:
            ws.delete_rows(i)
            break
    st.cache_data.clear()

def screen_manage():
    habits_df = load_habits()

    st.markdown(f'<div style="font-size:1.1rem;font-weight:900;padding:12px 4px 8px">'
                f'Manage Habits</div>', unsafe_allow_html=True)

    # Add new habit
    with st.expander("Add New Habit", expanded=habits_df.empty):
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                new_name = st.text_input("Name *", placeholder="e.g. Cold shower")
            with c2:
                new_icon = st.text_input("Icon", value="*")

            c3, c4 = st.columns(2)
            with c3:
                new_cat  = st.selectbox("Category", CATEGORIES)
            with c4:
                new_type = st.selectbox("Type", ["boolean", "numeric"])

            c5, c6 = st.columns(2)
            with c5:
                new_tgt  = st.number_input("Target", value=1, min_value=0, step=1)
            with c6:
                new_unit = st.text_input("Unit", placeholder="g, reps…")

            if st.form_submit_button("Add Habit", type="primary", use_container_width=True):
                if new_name.strip():
                    next_order = int(habits_df["Order"].max()) + 1 if not habits_df.empty else 1
                    ws = get_ss().worksheet("Habits")
                    ws.append_row([
                        str(uuid.uuid4())[:6], new_name.strip(),
                        new_icon.strip() or "*", new_cat, new_type,
                        str(new_tgt), new_unit.strip(),
                        "daily", "", next_order, "TRUE",
                    ])
                    st.cache_data.clear()
                    st.success(f"Added: {new_name}")
                    st.rerun()
                else:
                    st.error("Enter a habit name.")

    if habits_df.empty:
        return

    # Active habits by category
    for cat in CATEGORIES:
        cat_h = habits_df[
            (habits_df["Category"] == cat) & (habits_df["Active"] == True)
        ].reset_index(drop=True)
        if cat_h.empty:
            continue

        st.markdown(f"""
        <div class="sdiv" style="margin-top:16px">
            <div class="sdiv-txt">{cat}</div>
            <div class="sdiv-line"></div>
        </div>""", unsafe_allow_html=True)

        for idx, habit in cat_h.iterrows():
            h_id   = str(habit["HabitID"])
            h_name = str(habit["Name"])
            h_type = str(habit["Type"])
            h_tgt  = str(int(habit["Target"])) if h_type == "numeric" else ""
            h_unit = str(habit.get("TargetUnit", ""))
            tgt_txt = f"  target: {h_tgt}{h_unit}" if h_type == "numeric" else ""

            st.markdown(f"""
            <div style="background:{C['s2']};border:1px solid {C['border']};
                 border-radius:9px;padding:7px 12px;margin:3px 0;
                 display:flex;align-items:center;gap:10px">
                <div style="flex:1;min-width:0">
                    <div style="font-size:.82rem;font-weight:700;white-space:nowrap;
                         overflow:hidden;text-overflow:ellipsis">{h_name}</div>
                    <div style="font-size:.6rem;color:{C['muted']}">{h_type}{tgt_txt}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            b1, b2, _ = st.columns([1, 1, 4])
            with b1:
                if st.button("Pause", key=f"pause_{h_id}"):
                    _toggle_active(h_id, True)
                    st.rerun()
            with b2:
                if st.session_state.confirm_del == h_id:
                    if st.button("Confirm del", key=f"cd_{h_id}"):
                        _delete_habit(h_id)
                        st.session_state.confirm_del = None
                        st.rerun()
                else:
                    if st.button("Delete", key=f"del_{h_id}"):
                        st.session_state.confirm_del = h_id
                        st.rerun()

    # Paused habits
    inactive = habits_df[habits_df["Active"] == False].reset_index(drop=True)
    if not inactive.empty:
        st.markdown("---")
        st.markdown(f'<div class="sdiv-txt" style="margin:8px 0 4px">Paused</div>',
                    unsafe_allow_html=True)
        for _, habit in inactive.iterrows():
            h_id   = str(habit["HabitID"])
            h_name = str(habit["Name"])
            ci, cb = st.columns([4, 1])
            with ci:
                st.markdown(f"""
                <div style="padding:5px 4px;opacity:.4;display:flex;gap:8px;
                     border-bottom:1px solid {C['border']}">
                    <span style="font-size:.8rem">{h_name}</span>
                </div>""", unsafe_allow_html=True)
            with cb:
                if st.button("Resume", key=f"res_{h_id}"):
                    _toggle_active(h_id, False)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  SETUP & MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run_setup():
    if not st.session_state.setup_ok:
        with st.spinner("Setting up…"):
            try:
                ensure_habit_sheets()
                st.session_state.setup_ok = True
            except Exception as ex:
                st.error(f"Setup failed: {ex}")
                st.stop()

def main():
    init_state()
    inject_css()
    run_setup()
    render_top_bar()
    if st.session_state.nav == "today":
        screen_today()
    elif st.session_state.nav == "manage":
        screen_manage()

if __name__ == "__main__":
    main()
