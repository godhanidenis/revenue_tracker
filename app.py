"""
app.py — Revenue Intelligence Dashboard
Fixes: sidebar top padding, chart empty space, table column alignment
"""
from datetime import date, timedelta
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from fetchers.admob_fetcher import fetch_admob_apps
from database import (
    init_db,
    get_currency_config, update_currency_config,
    get_all_monthly_fx_rates, set_monthly_fx_rate, clear_monthly_fx_rate,
    effective_rate,
    get_overall_summary, get_monthly_summary, get_daywise_for_month,
    get_last_fetch_logs,
)

st.set_page_config(
    page_title="Revenue Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)
init_db()

# ── Tokens ───────────────────────────────────────────────────────────────
BLUE       = "#1a56db"
BLUE_LIGHT = "#eff6ff"
BLUE_MID   = "#dbeafe"
GREEN      = "#059669"
GREEN_BG   = "#ecfdf5"
RED        = "#dc2626"
RED_BG     = "#fef2f2"
AMBER      = "#d97706"
AMBER_BG   = "#fffbeb"
GRAY_50    = "#f8fafc"
GRAY_100   = "#f1f5f9"
GRAY_200   = "#e2e8f0"
GRAY_300   = "#cbd5e1"
GRAY_400   = "#94a3b8"
GRAY_500   = "#64748b"
GRAY_600   = "#475569"
GRAY_700   = "#334155"
GRAY_800   = "#1e293b"
GRAY_900   = "#0f172a"
WHITE      = "#ffffff"
BORDER     = "#e2e8f0"

# Brand SVGs removed — using generic labels instead
ADMOB_SVG = ''
GADS_SVG  = ''

SYM = {"INR": "₹", "USD": "$"}

# Column widths — single source of truth used by BOTH header and data rows
# Must match exactly: month | revenue | spend | profit | impressions | conversions | rate | toggle
COL_WIDTHS = "160px 1fr 1fr 1fr 110px 110px 140px 44px"

def chart_layout(height=300, tickprefix="₹"):
    return dict(
        paper_bgcolor=WHITE, plot_bgcolor=WHITE,
        font=dict(family="DM Sans,sans-serif", color=GRAY_500, size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRAY_100, linecolor=GRAY_200, tickfont=dict(size=11), showgrid=False),
        yaxis=dict(gridcolor=GRAY_100, linecolor=GRAY_200, tickprefix=tickprefix,
                   tickfont=dict(size=11), zeroline=True, zerolinecolor=GRAY_200),
        margin=dict(l=0, r=0, t=10, b=0), height=height, barmode="group",
        hoverlabel=dict(bgcolor=WHITE, bordercolor=BORDER,
                        font=dict(family="DM Mono,monospace", size=12)),
    )

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=DM+Mono:wght@400;500&display=swap');

*,[class*="css"]{{font-family:'DM Sans',sans-serif!important}}

/* ── Hide Streamlit top toolbar and collapse its height entirely ── */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
header[data-testid="stHeader"]{{
    display:none!important;
    visibility:hidden!important;
    height:0!important;
    min-height:0!important;
    max-height:0!important;
    overflow:hidden!important;
    padding:0!important;
    margin:0!important;
}}
/* ── Hide sidebar collapse button on desktop only ── */
@media (min-width: 768px) {{
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"]{{
        display:none!important;
        visibility:hidden!important;
    }}

}}

/* ── Mobile: sidebar as full-width overlay drawer ── */
@media (max-width: 767px) {{
    /* Style Streamlit's native sidebar toggle — both open (hamburger) and close (X) */
    [data-testid="stSidebarCollapseButton"]{{
        position:absolute!important;
        top:14px!important;
        right:14px!important;
        left:auto!important;
        width:28px!important;
        height:28px!important;
        background:{GRAY_100}!important;
        border:1px solid {BORDER}!important;
        border-radius:7px!important;
        display:flex!important;
        align-items:center!important;
        justify-content:center!important;
        z-index:9999!important;
    }}
    [data-testid="stSidebarCollapseButton"] svg{{
        width:14px!important;
        height:14px!important;
        color:{GRAY_700}!important;
    }}
    /* Hamburger button to open sidebar — fixed top-left */
    [data-testid="collapsedControl"]{{
        display:flex!important;
        visibility:visible!important;
        position:fixed!important;
        top:14px!important;
        left:14px!important;
        z-index:9999!important;
        background:{WHITE}!important;
        border:1px solid {BORDER}!important;
        border-radius:8px!important;
        width:36px!important;
        height:36px!important;
        align-items:center!important;
        justify-content:center!important;
        box-shadow:0 2px 8px rgba(15,23,42,0.12)!important;
        padding:0!important;
    }}
    [data-testid="collapsedControl"] svg{{
        width:16px!important;
        height:16px!important;
        color:{GRAY_700}!important;
    }}

    /* Sidebar: slides in from left as an overlay */
    [data-testid="stSidebar"]{{
        position:fixed!important;
        top:0!important;
        left:0!important;
        height:100vh!important;
        width:280px!important;
        min-width:280px!important;
        max-width:280px!important;
        z-index:9998!important;
        box-shadow:4px 0 20px rgba(15,23,42,0.15)!important;
        overflow-y:auto!important;
    }}
    /* Main content: full width, no left offset */
    [data-testid="stAppViewContainer"] > section.main{{
        margin-left:0!important;
        width:100vw!important;
        max-width:100vw!important;
    }}
    /* Top padding so hamburger doesn't cover content */
    [data-testid="block-container"]{{
        padding:60px 14px 18px!important;
    }}
    /* KPI cards: 2 per row */
    [data-testid="stHorizontalBlock"]{{
        flex-wrap:wrap!important;
        gap:8px!important;
    }}
    [data-testid="stHorizontalBlock"] > div{{
        min-width:calc(50% - 4px)!important;
        flex:0 0 calc(50% - 4px)!important;
    }}
    /* Page header */
    .pg-hdr{{
        flex-direction:column!important;
        align-items:flex-start!important;
        gap:4px!important;
        padding-top:4px!important;
    }}
    .pg-title{{font-size:1.1rem!important}}
    .pg-sub{{font-size:0.7rem!important;line-height:1.6!important}}
    /* Metric cards smaller on mobile */
    .stMetric [data-testid="stMetricValue"]{{
        font-size:1.1rem!important;
    }}
    /* Table: hide impressions + conversions columns on mobile */
    .tbl-outer [data-testid="stHorizontalBlock"] > div:nth-child(5),
    .tbl-outer [data-testid="stHorizontalBlock"] > div:nth-child(6){{
        display:none!important;
    }}
}}

/* ── Tablet (768px - 1024px) ── */
@media (min-width: 768px) and (max-width: 1024px) {{
    [data-testid="block-container"]{{
        padding:16px 14px 18px!important;
    }}
    .stMetric [data-testid="stMetricValue"]{{
        font-size:1.1rem!important;
    }}
}}
/* Streamlit shifts main content down by header height — reset it */
[data-testid="stAppViewContainer"]{{
    padding-top:0!important;
    margin-top:0!important;
}}
.main{{
    padding-top:0!important;
    margin-top:0!important;
}}

/* ── Remove ALL top padding from main area ── */
[data-testid="stAppViewContainer"]{{background:{GRAY_50}}}
[data-testid="block-container"]{{
    padding:16px 18px 18px!important;
    max-width:1440px;
}}
.main .block-container{{
    padding:16px 18px 18px!important;
}}
/* Kill every Streamlit-injected top gap on main content */
.main > div:first-child{{
    padding-top:0!important;
    margin-top:0!important;
}}
[data-testid="stAppViewContainer"] > section.main{{
    padding-top:0!important;
}}
[data-testid="stAppViewContainer"] > section.main > div{{
    padding-top:0!important;
}}
[data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"]:first-child{{
    padding-top:0!important;
    margin-top:0!important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"]{{
    background:{WHITE}!important;
    border-right:1px solid {BORDER}!important;
}}
[data-testid="stSidebar"] > div:first-child{{
    padding-top:0!important;
    margin-top:0!important;
}}
[data-testid="stSidebarContent"]{{
    padding-top:0!important;
    gap:0!important;
}}
[data-testid="stSidebarUserContent"]{{
    padding-top:0!important;
    padding-left:0.75rem!important;
    padding-right:0.75rem!important;
    padding-bottom:1.5rem!important;
}}
/* Widget vertical rhythm */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{{
    gap:6px!important;
}}

/* ── Logo header ── */
.sb-header{{
    background:{WHITE};
    border-bottom:1px solid {BORDER};
    padding:16px 18px 14px;
    position:sticky;
    top:0;
    z-index:10;
    margin:0 -0.75rem 0 -0.75rem;
}}
.sb-logo-row{{display:flex;align-items:center;gap:10px}}
.sb-icon{{
    width:32px;height:32px;background:{BLUE};border-radius:8px;
    display:flex;align-items:center;justify-content:center;
    font-size:16px;flex-shrink:0;
}}
.sb-name{{font-size:0.87rem;font-weight:600;color:{GRAY_900};letter-spacing:-0.01em}}
.sb-sub{{font-size:0.68rem;color:{GRAY_400};margin-top:2px}}

/* ── Section heading ──
   Space above: 20px (margin-top)
   Heading text bottom: 6px gap before underline
   Underline to first widget: 10px (margin-bottom)
*/
.sb-sec{{
    display:block;
    font-size:0.6rem;
    font-weight:700;
    letter-spacing:0.1em;
    text-transform:uppercase;
    color:{GRAY_400};
    margin:0 0 14px;
    padding:0;
}}
/* Section block wrapper — holds the divider above + label + widgets */
.sb-section{{
    border-top:1px solid {BORDER};
    padding-top:14px;
    margin-top:14px;
}}
/* First section has no divider above it */
.sb-section.first{{
    border-top:none;
    padding-top:14px;
    margin-top:8px;
}}

/* ── Note text below section heading ── */
.sb-note{{
    font-size:0.7rem;
    color:{GRAY_400};
    line-height:1.55;
    margin:0 0 8px;
}}
.sb-note b{{color:{GRAY_600};font-weight:600}}

/* ── Widget labels — match section heading style ── */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stDateInput label{{
    font-size:0.6rem!important;
    font-weight:700!important;
    letter-spacing:0.09em!important;
    text-transform:uppercase!important;
    color:{GRAY_400}!important;
    margin-bottom:4px!important;
    padding:0!important;
    line-height:1!important;
}}
/* Tighten gap between label and input box */
[data-testid="stSidebar"] .stSelectbox > div,
[data-testid="stSidebar"] .stNumberInput > div,
[data-testid="stSidebar"] .stDateInput > div{{
    margin-top:0!important;
}}

/* ── Checkbox ── */
[data-testid="stSidebar"] .stCheckbox{{
    margin-top:4px!important;
}}
[data-testid="stSidebar"] .stCheckbox label{{
    font-size:0.82rem!important;
    color:{GRAY_700}!important;
    font-weight:400!important;
    gap:8px!important;
    align-items:center!important;
}}

/* ── Horizontal divider between sections ── */
.sb-divider{{
    border:none;
    border-top:1px solid {BORDER};
    margin:20px 0 0;
}}

/* ── Hide stray Streamlit-injected hr at bottom of sidebar ── */
[data-testid="stSidebar"] hr,
[data-testid="stSidebarContent"] hr{{
    display:none!important;
}}

/* ── Metrics ── */
[data-testid="metric-container"]{{
    background:{WHITE}!important;border:1px solid {BORDER}!important;
    border-radius:12px!important;padding:1rem 1.1rem!important;
    box-shadow:0 1px 3px rgba(15,23,42,.05)!important;
    transition:box-shadow .2s,transform .15s;
}}
[data-testid="metric-container"]:hover{{
    box-shadow:0 5px 16px rgba(15,23,42,.09)!important;
    transform:translateY(-1px)
}}
.stMetric label{{
    font-size:0.66rem!important;font-weight:700!important;
    letter-spacing:.08em!important;text-transform:uppercase!important;
    color:{GRAY_400}!important
}}
.stMetric [data-testid="stMetricValue"]{{
    font-size:1.32rem!important;font-weight:600!important;
    color:{GRAY_900}!important;letter-spacing:-.02em!important;
    font-family:'DM Mono',monospace!important
}}
.stMetric [data-testid="stMetricDelta"]{{font-size:.71rem!important;font-weight:500!important}}

/* ── Page header ── */
.pg-hdr{{
    display:flex;justify-content:space-between;align-items:center;
    padding:0 0 14px;border-bottom:1px solid {BORDER};margin-bottom:1.2rem
}}
.pg-title{{font-size:1.3rem;font-weight:600;color:{GRAY_900};letter-spacing:-.02em}}
.pg-sub{{font-size:0.75rem;color:{GRAY_400};margin-top:3px}}
.pg-badge{{
    background:{BLUE_LIGHT};color:{BLUE};border:1px solid {BLUE_MID};
    border-radius:6px;padding:4px 11px;font-size:0.7rem;font-weight:600;
    display:flex;align-items:center;gap:5px
}}

/* ── Section title ── */
.sec-ttl{{
    font-size:0.78rem;font-weight:600;color:{GRAY_700};
    margin:0 0 .65rem;display:flex;align-items:center;gap:6px
}}
.sec-ttl::before{{
    content:'';display:inline-block;width:3px;height:13px;
    background:{BLUE};border-radius:2px;flex-shrink:0
}}

/* ── Chart wrapper — no extra div, just a section title above plotly ── */
.chart-outer{{
    background:{WHITE};border:1px solid {BORDER};border-radius:12px;
    padding:14px 18px 6px;
    box-shadow:0 1px 3px rgba(15,23,42,.05);margin-bottom:1rem;
    overflow:hidden;
}}

/* ── Info bar ── */
.info-bar{{
    background:{BLUE_LIGHT};border:1px solid {BLUE_MID};border-radius:8px;
    padding:7px 13px;font-size:0.74rem;color:{BLUE};
    font-weight:500;margin-bottom:.8rem;
    display:flex;align-items:center;gap:6px
}}

/* ── Table ── */
.tbl-outer{{
    background:{WHITE};border:1px solid {BORDER};border-radius:12px;
    overflow-x:auto;box-shadow:0 1px 3px rgba(15,23,42,.05);
    -webkit-overflow-scrolling:touch;
}}
/* On mobile, allow the inner stHorizontalBlock to scroll */
@media (max-width: 767px) {{
    .tbl-outer [data-testid="stHorizontalBlock"]{{
        overflow-x:auto!important;
        -webkit-overflow-scrolling:touch!important;
        flex-wrap:nowrap!important;
    }}
    .tbl-outer [data-testid="stHorizontalBlock"] > div{{
        min-width:100px!important;
        flex-shrink:0!important;
    }}
    .tbl-outer [data-testid="stHorizontalBlock"] > div:first-child{{
        min-width:130px!important;
    }}
}}

.rate-chip{{
    display:inline-flex;align-items:center;
    font-family:'DM Mono',monospace;font-size:.62rem;font-weight:700;
    border-radius:4px;padding:2px 6px;
}}
.rc-g{{background:{BLUE_LIGHT};color:{BLUE};border:1px solid {BLUE_MID}}}
.rc-c{{background:{GREEN_BG};color:{GREEN};border:1px solid #a7f3d0}}

/* Month row toggle button */
.tbl-outer [data-testid="stButton"] button{{
    background:none!important;
    border:none!important;
    box-shadow:none!important;
    padding:10px 0!important;
    font-size:.82rem!important;
    font-weight:600!important;
    color:{GRAY_800}!important;
    text-align:left!important;
    width:100%!important;
    justify-content:flex-start!important;
    letter-spacing:0!important;
    text-transform:none!important;
    border-radius:0!important;
    height:auto!important;
    line-height:1.4!important;
}}
.tbl-outer [data-testid="stButton"] button:hover{{
    color:{BLUE}!important;
    background:none!important;
}}

/* Day panel */
.day-panel{{
    background:{GRAY_50};border-top:1px solid {BORDER};
    padding:16px 20px 18px;
}}
.day-ttl{{
    font-size:.68rem;font-weight:700;letter-spacing:.08em;
    text-transform:uppercase;color:{GRAY_400};margin-bottom:10px
}}
.override-strip{{
    display:flex;align-items:center;gap:8px;flex-wrap:wrap;
    background:{WHITE};border:1px solid {BORDER};border-radius:8px;
    padding:8px 13px;margin-bottom:10px
}}
.ov-label{{font-size:.72rem;color:{GRAY_600};font-weight:500}}
.badge-g{{background:{BLUE_LIGHT};color:{BLUE};border:1px solid {BLUE_MID};border-radius:4px;padding:2px 7px;font-size:.67rem;font-weight:700;font-family:'DM Mono',monospace}}
.badge-c{{background:{GREEN_BG};color:{GREEN};border:1px solid #a7f3d0;border-radius:4px;padding:2px 7px;font-size:.67rem;font-weight:700;font-family:'DM Mono',monospace}}

/* Streamlit widget resets */
.stButton>button{{border-radius:7px!important;font-weight:500!important;font-size:.78rem!important;transition:all .15s!important}}
[data-testid="stBaseButton-primary"]{{background:{BLUE}!important;color:{WHITE}!important;border:none!important}}
[data-testid="stBaseButton-primary"]:hover{{background:#1648c0!important;box-shadow:0 2px 8px rgba(26,86,219,.25)!important}}
.stNumberInput>div>div,.stSelectbox>div>div,.stDateInput>div>div{{border-radius:7px!important;border-color:{BORDER}!important;font-size:.82rem!important}}
/* Kill the label gap on number inputs used inline in table */
.stNumberInput{{margin:0!important}}
.stNumberInput label{{display:none!important}}
[data-testid="stDataFrame"]{{border-radius:8px;overflow:hidden;border:1px solid {BORDER}}}
[data-testid="stDataFrame"] th{{background:{GRAY_50}!important;font-size:.67rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:.06em!important;color:{GRAY_500}!important}}
[data-testid="stDataFrame"] td{{font-family:'DM Mono',monospace!important;font-size:.79rem!important}}
.stCheckbox label{{font-size:.8rem!important;color:{GRAY_600}!important}}
.stSuccess,.stInfo,.stWarning{{border-radius:8px!important}}
.pg-footer{{text-align:center;padding:1.5rem 0 .5rem;font-size:.68rem;color:{GRAY_400};border-top:1px solid {BORDER};margin-top:1rem}}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="sb-header">
  <div class="sb-logo-row">
    <div class="sb-icon">📈</div>
    <div>
      <div class="sb-name">Revenue Dashboard</div>
      <div class="sb-sub">Spending &amp; Revenue</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
    # ── Date Range ──────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section first"><p class="sb-sec">Date Range</p></div>', unsafe_allow_html=True)
    preset = st.selectbox(
        "Quick select",
        ["Last 3 months","Last 6 months","This year","Last 7 days","Last 30 days","Custom"],
        label_visibility="collapsed",
    )

    today = date.today()
    if   preset=="Last 3 months": ds,de=today.replace(day=1)-timedelta(days=90), today-timedelta(days=1)
    elif preset=="Last 6 months": ds,de=today.replace(day=1)-timedelta(days=180),today-timedelta(days=1)
    elif preset=="This year":     ds,de=date(today.year,1,1),                    today-timedelta(days=1)
    elif preset=="Last 7 days":   ds,de=today-timedelta(days=7),                 today-timedelta(days=1)
    elif preset=="Last 30 days":  ds,de=today-timedelta(days=30),                today-timedelta(days=1)
    else:                         ds,de=today-timedelta(days=90),                today-timedelta(days=1)

    dc1, dc2 = st.columns(2)
    with dc1: start_date = st.date_input("From", value=ds, max_value=today)
    with dc2: end_date   = st.date_input("To",   value=de, max_value=today)
    if start_date > end_date:
        st.error("Start must be ≤ End"); st.stop()

    # ── Currency ─────────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section"><p class="sb-sec">Currency</p></div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sb-note">Revenue data stored in <b>USD</b>. Spend data stored in <b>INR</b>.<br>'
        'Global rate is used for months with no override.</p>',
        unsafe_allow_html=True
    )

    cfg = get_currency_config()
    disp_curr   = st.selectbox("Display currency", ["INR","USD"],
                               index=0 if cfg["display_currency"]=="INR" else 1)
    global_rate = st.number_input("USD → INR rate", min_value=1.0, max_value=500.0,
                                  value=float(cfg["usd_to_inr_rate"]), step=0.5, format="%.2f")

    # ── AdMob App Filter ─────────────────────────────────────────────────
    st.markdown('<div class="sb-section"><p class="sb-sec">AdMob App</p></div>', unsafe_allow_html=True)
    st.markdown('<p class="sb-note">Select which app to track. Changing this requires a backfill to refresh data.</p>', unsafe_allow_html=True)

    # Load apps (cached in session state so we don't hit API on every rerun)
    if "admob_apps" not in st.session_state or st.session_state.get("admob_apps_error"):
        try:
            st.session_state.admob_apps = fetch_admob_apps()
            st.session_state.admob_apps_error = False
        except Exception as e:
            st.session_state.admob_apps = []
            st.session_state.admob_apps_error = True
            st.warning(f"Could not load apps: {e}")

    apps = st.session_state.admob_apps
    app_options = {"All Apps": "ALL"}
    app_options.update({f"{a['name']} ({a['platform']})": a["app_id"] for a in apps})
    app_labels  = list(app_options.keys())
    current_app_id   = cfg.get("admob_app_id", "ALL")
    current_app_label = next((k for k, v in app_options.items() if v == current_app_id), "All Apps")
    selected_app_label = st.selectbox("App", app_labels,
                                      index=app_labels.index(current_app_label) if current_app_label in app_labels else 0)
    selected_app_id   = app_options[selected_app_label]


    if st.button("Save Settings", use_container_width=True, type="primary"):
        update_currency_config(global_rate, disp_curr, selected_app_id, selected_app_label)
        st.success("Saved! Re-run backfill if you changed the app filter.")
        st.rerun()

    # ── Options ──────────────────────────────────────────────────────────────
    st.markdown('<div class="sb-section"><p class="sb-sec">Options</p></div>', unsafe_allow_html=True)
    show_logs = st.checkbox("Show fetch logs")

# ── Runtime config ────────────────────────────────────────────────────────
cfg              = get_currency_config()
global_rate      = cfg["usd_to_inr_rate"]
disp             = cfg["display_currency"]
sym              = SYM.get(disp, disp)
monthly_override = get_all_monthly_fx_rates()

if "expanded_month" not in st.session_state:
    st.session_state.expanded_month = None
if "sidebar_open" not in st.session_state:
    st.session_state.sidebar_open = True

# ── Page header ───────────────────────────────────────────────────────────
n_ov    = len(monthly_override)
ov_note = (f"&nbsp;·&nbsp;<span style='color:{GREEN};font-weight:500'>"
           f"{n_ov} override{'s' if n_ov!=1 else ''} active</span>") if n_ov else ""

app_label = cfg.get("admob_app_name", "All Apps")
app_note  = f"&nbsp;·&nbsp;<span style='color:{GRAY_600}'>App: <b>{app_label}</b></span>"

st.markdown(
    f'<div class="pg-hdr">'
    f'<div><div class="pg-title">Revenue Dashboard</div>'
    f'<div class="pg-sub">{start_date.strftime("%d %b %Y")} — {end_date.strftime("%d %b %Y")}'
    f'&nbsp;·&nbsp;{disp}&nbsp;·&nbsp;1 USD = {sym}{global_rate:,.2f}'
    f'{app_note}{ov_note}</div></div>'
    f'</div>', unsafe_allow_html=True
)

# ── KPI cards ─────────────────────────────────────────────────────────────
summary = get_overall_summary(start_date, end_date, global_rate, monthly_override, disp)
margin  = (summary["profit"]/summary["revenue"]*100) if summary["revenue"] else 0

k1,k2,k3,k4,k5,k6 = st.columns(6)
with k1: st.metric("Total Revenue", f"{sym}{summary['revenue']:,.2f}")
with k2: st.metric("Total Spend",   f"{sym}{summary['spend']:,.2f}")
with k3: st.metric("Net Profit",    f"{sym}{summary['profit']:,.2f}",
                   delta=f"{margin:.1f}% margin",
                   delta_color="normal" if summary["profit"]>=0 else "inverse")
with k4: st.metric("Avg eCPM",      f"{sym}{summary['ecpm']:,.4f}")
with k5: st.metric("Conversions",   f"{summary['conversions']:,.0f}")
with k6: st.metric("Ad Clicks",  f"{summary['clicks_admob']:,}")

# ── Monthly chart — contained purely in HTML div, no open/close mismatch ─
monthly_df = get_monthly_summary(start_date, end_date, global_rate, monthly_override, disp)
if monthly_df.empty:
    st.warning("No data for selected range. Run the backfill cron job first.")
    st.stop()

# Render chart title inside an HTML container then plotly outside it
# to avoid any dangling open divs being passed to Streamlit's markdown parser
st.markdown('<div class="sec-ttl">Monthly Overview</div>', unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Bar(x=monthly_df["month_label"], y=monthly_df["revenue"],
                     name="Revenue", marker_color=BLUE, marker_opacity=.88, marker_line_width=0))
fig.add_trace(go.Bar(x=monthly_df["month_label"], y=monthly_df["spend"],
                     name="Spend", marker_color=AMBER, marker_opacity=.88, marker_line_width=0))
fig.add_trace(go.Scatter(
    x=monthly_df["month_label"], y=monthly_df["profit"], name="Profit / Loss",
    mode="lines+markers", line=dict(color=GREEN, width=2),
    marker=dict(color=[GREEN if p>=0 else RED for p in monthly_df["profit"]],
                size=7, line=dict(color=WHITE, width=1.5)),
))
lo = chart_layout(height=275, tickprefix=sym)
fig.update_layout(**lo)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

# ── Monthly table ─────────────────────────────────────────────────────────
st.markdown('<div class="sec-ttl">Month-by-Month Breakdown</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="info-bar">'
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>'
    ' Click ▸ to expand day-wise data. Edit the rate field and press Enter to apply instantly.'
    '</div>', unsafe_allow_html=True
)

# ── Table header — st.columns matching row ratios ────────────────────────
st.markdown('<div class="tbl-outer">', unsafe_allow_html=True)
HDR_COLS = [1.8, 1.2, 1.2, 1.3, 1.1, 1.0, 1.3]
hc = st.columns(HDR_COLS)
_TH = f"font-size:.6rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:{GRAY_400};padding:10px 0 8px;display:block"
with hc[0]: st.markdown(f'<span style="{_TH}">Month</span>', unsafe_allow_html=True)
with hc[1]: st.markdown(f'<span style="{_TH}">Revenue</span>', unsafe_allow_html=True)
with hc[2]: st.markdown(f'<span style="{_TH}">Spend</span>', unsafe_allow_html=True)
with hc[3]: st.markdown(f'<span style="{_TH}">Profit / Loss</span>', unsafe_allow_html=True)
with hc[4]: st.markdown(f'<span style="{_TH}">Impressions</span>', unsafe_allow_html=True)
with hc[5]: st.markdown(f'<span style="{_TH}">Conversions</span>', unsafe_allow_html=True)
with hc[6]: st.markdown(f'<span style="{_TH}">USD → INR</span>', unsafe_allow_html=True)
st.markdown(f'<hr style="border:none;border-top:2px solid {BORDER};margin:0">', unsafe_allow_html=True)

# ── Rows ──────────────────────────────────────────────────────────────────
for _, mrow in monthly_df.iterrows():
    ym          = mrow["year_month"]
    yr, mo      = int(ym[:4]), int(ym[5:])
    is_override = mrow["rate_overridden"]
    eff_rate    = mrow["effective_rate"]
    profit      = mrow["profit"]
    p_pos       = profit >= 0
    p_sign      = "+" if p_pos else ""
    arrow       = "▲" if p_pos else "▼"
    is_open     = st.session_state.expanded_month == ym
    p_col       = GREEN if p_pos else RED
    row_bg      = BLUE_LIGHT if is_open else WHITE
    ov_chip     = f'<span class="rate-chip rc-c">custom</span>' if is_override else ""

    # ── Row cols: toggle btn | revenue | spend | profit | impr | conv | rate ──
    rc = st.columns([1.8, 1.2, 1.2, 1.3, 1.1, 1.0, 1.3])

    with rc[0]:
        if st.button(
            f"{'▾' if is_open else '▸'}  {mrow['month_label']}{'  ✎' if is_override else ''}",
            key=f"tog_{ym}", use_container_width=True,
        ):
            st.session_state.expanded_month = None if is_open else ym
            st.rerun()
    with rc[1]:
        st.markdown(f'<p style="margin:0;padding:14px 0 14px;font-family:DM Mono,monospace;font-size:.82rem;color:{BLUE}">{sym}{mrow["revenue"]:,.2f}</p>', unsafe_allow_html=True)
    with rc[2]:
        st.markdown(f'<p style="margin:0;padding:14px 0 14px;font-family:DM Mono,monospace;font-size:.82rem;color:{AMBER}">{sym}{mrow["spend"]:,.2f}</p>', unsafe_allow_html=True)
    with rc[3]:
        st.markdown(f'<p style="margin:0;padding:14px 0 14px;font-family:DM Mono,monospace;font-size:.82rem;color:{p_col}">{arrow} {p_sign}{sym}{abs(profit):,.2f}</p>', unsafe_allow_html=True)
    with rc[4]:
        st.markdown(f'<p style="margin:0;padding:14px 0 14px;font-family:DM Mono,monospace;font-size:.82rem;color:{GRAY_600}">{int(mrow.get("impressions",0)):,}</p>', unsafe_allow_html=True)
    with rc[5]:
        st.markdown(f'<p style="margin:0;padding:14px 0 14px;font-family:DM Mono,monospace;font-size:.82rem;color:{GRAY_600}">{mrow.get("conversions",0):,.1f}</p>', unsafe_allow_html=True)
    with rc[6]:
        rate_key = f"rate_input_{ym}"
        if rate_key not in st.session_state:
            st.session_state[rate_key] = float(eff_rate)
        def _make_saver(ym_=ym, rk_=rate_key):
            def _save():
                set_monthly_fx_rate(ym_, st.session_state[rk_])
            return _save
        st.number_input("rate", min_value=1.0, max_value=500.0,
            key=rate_key, step=0.5, format="%.2f",
            label_visibility="collapsed", on_change=_make_saver(),
            help=f"USD→INR for {mrow['month_label']}. Press Enter to apply.")

    st.markdown(f'<hr style="border:none;border-top:1px solid {BORDER};margin:0">', unsafe_allow_html=True)

    # ── Day panel — expanded below this row ──────────────────────────────
    if is_open:
        fresh_overrides = get_all_monthly_fx_rates()
        fresh_rate      = effective_rate(ym, global_rate, fresh_overrides)
        fresh_override  = ym in fresh_overrides

        badge = (f"<span class='badge-c'>Custom: 1 USD = {sym}{fresh_rate:,.2f}</span>"
                 if fresh_override else
                 f"<span class='badge-g'>Global: 1 USD = {sym}{fresh_rate:,.2f}</span>")

        st.markdown(
            f'<div class="day-panel">'
            f'<div class="override-strip">'
            f'  <span class="ov-label">Rate for {mrow["month_label"]}:</span>'
            f'  {badge}'
            f'  <span style="font-size:.68rem;color:{GRAY_400}">Edit rate in row above → press Enter to apply</span>'
            f'</div>', unsafe_allow_html=True
        )

        if fresh_override:
            if st.button(f"✕ Clear override for {mrow['month_label']}",
                         key=f"clr_{ym}"):
                clear_monthly_fx_rate(ym)
                st.session_state.pop(f"rate_input_{ym}", None)
                st.rerun()

        # Month mini KPIs
        mk1,mk2,mk3,mk4,mk5,mk6 = st.columns(6)
        with mk1: st.metric("Revenue",      f"{sym}{mrow['revenue']:,.2f}")
        with mk2: st.metric("Spend",        f"{sym}{mrow['spend']:,.2f}")
        with mk3: st.metric("Profit",       f"{sym}{mrow['profit']:,.2f}")
        with mk4: st.metric("Impressions",  f"{int(mrow.get('impressions',0)):,}")
        with mk5: st.metric("Conversions",  f"{mrow.get('conversions',0):,.1f}")
        with mk6: st.metric("Ad Clicks", f"{int(mrow.get('clicks_admob',0)):,}")

        st.markdown(f'<div class="day-ttl" style="margin-top:12px">Daily breakdown — {mrow["month_label"]} · Rate: 1 USD = {sym}{fresh_rate:,.2f}</div>', unsafe_allow_html=True)

        with st.spinner(f"Loading {mrow['month_label']}…"):
            day_df = get_daywise_for_month(yr, mo, fresh_rate, disp)

        if day_df.empty:
            st.info("No day-wise data for this month.")
        else:
            dc = [GREEN if p>=0 else RED for p in day_df["profit"]]
            fd = go.Figure()
            fd.add_trace(go.Bar(x=day_df["date"],y=day_df["revenue"],name="Revenue",
                                marker_color=BLUE,marker_opacity=.85,marker_line_width=0))
            fd.add_trace(go.Bar(x=day_df["date"],y=day_df["spend"],name="Spend",
                                marker_color=AMBER,marker_opacity=.85,marker_line_width=0))
            fd.add_trace(go.Scatter(x=day_df["date"],y=day_df["profit"],name="Profit",
                                    mode="lines+markers",line=dict(color=GREEN,width=1.5),
                                    marker=dict(color=dc,size=5,line=dict(color=WHITE,width=1))))
            ld = chart_layout(height=210, tickprefix=sym)
            ld["xaxis"]["tickformat"] = "%d %b"
            fd.update_layout(**ld)
            st.plotly_chart(fd, use_container_width=True, config={"displayModeBar": False})

            tbl = day_df[["date","revenue","spend","profit","ecpm",
                           "impressions","clicks_admob","clicks_gads",
                           "conversions","ctr","match_rate"]].copy()
            tbl["date"]        = tbl["date"].dt.strftime("%d %b %Y")
            tbl["revenue"]     = tbl["revenue"].map(lambda x: f"{sym}{x:,.4f}")
            tbl["spend"]       = tbl["spend"].map(lambda x: f"{sym}{x:,.4f}")
            tbl["profit"]      = tbl["profit"].map(lambda x: f"{sym}{x:,.4f}")
            tbl["ecpm"]        = tbl["ecpm"].map(lambda x: f"{sym}{x:,.4f}")
            tbl["impressions"] = tbl["impressions"].map(lambda x: f"{int(x):,}")
            tbl["clicks_admob"]= tbl["clicks_admob"].map(lambda x: f"{int(x):,}")
            tbl["clicks_gads"] = tbl["clicks_gads"].map(lambda x: f"{int(x):,}")
            tbl["conversions"] = tbl["conversions"].map(lambda x: f"{x:,.1f}")
            tbl["ctr"]         = tbl["ctr"].map(lambda x: f"{x:.2f}%")
            tbl["match_rate"]  = tbl["match_rate"].map(lambda x: f"{x:.1f}%")
            tbl.columns = ["Date",f"Revenue ({disp})",f"Spend ({disp})",f"Profit ({disp})",
                           f"eCPM ({disp})","Impressions","Ad Clicks",
                           "Spend Clicks","Conversions","CTR","Match Rate"]
            st.dataframe(tbl, use_container_width=True, hide_index=True)

            csv = day_df.to_csv(index=False).encode("utf-8")
            st.download_button(f"↓ Download {mrow['month_label']} CSV",
                               data=csv, file_name=f"revenue_{ym}.csv",
                               mime="text/csv", key=f"dl_{ym}")

        st.markdown("</div>", unsafe_allow_html=True)   # day-panel

# Close tbl-outer
st.markdown('</div>', unsafe_allow_html=True)

# ── Fetch logs ─────────────────────────────────────────────────────────────
if show_logs:
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="sec-ttl">Fetch Logs</div>', unsafe_allow_html=True)
    logs = get_last_fetch_logs(20)
    if logs.empty: st.info("No fetch logs yet.")
    else: st.dataframe(logs, use_container_width=True, hide_index=True)

st.markdown(
    f'<div class="pg-footer">Revenue Intelligence'
    f'<span style="margin:0 6px">·</span>Revenue in USD · Spend in INR'
    f'<span style="margin:0 6px">·</span>Data refreshes daily at 01:00 IST'
    f'</div>', unsafe_allow_html=True
)