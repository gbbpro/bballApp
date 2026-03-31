import streamlit as st
import pandas as pd
import os
from pathlib import Path

st.set_page_config(
    page_title="NBA Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Bebas+Neue&family=DM+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.05em; }

.stApp { background: #0d0d0f; color: #e8e8e8; }

section[data-testid="stSidebar"] {
    background: #111114;
    border-right: 1px solid #222;
}

.metric-card {
    background: #16161a;
    border: 1px solid #2a2a2f;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.5rem;
}
.metric-label { font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 0.1em; }
.metric-value { font-family: 'DM Mono', monospace; font-size: 1.6rem; color: #f0f0f0; }
.metric-delta { font-size: 0.75rem; margin-top: 2px; }
.delta-good { color: #4ade80; }
.delta-bad  { color: #f87171; }

.stDataFrame { border: 1px solid #2a2a2f !important; border-radius: 8px; }
div[data-testid="stDataFrameResizable"] { border-radius: 8px; overflow: hidden; }

.freshness-badge {
    display: inline-block;
    background: #1a2a1a;
    border: 1px solid #2d4a2d;
    color: #4ade80;
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


# ── data loader ─────────────────────────────────────────────────────────────
DATA_DIR = Path("data")

@st.cache_data(ttl=3600)
def load(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return None
    return pd.read_parquet(path) if filename.endswith(".parquet") else pd.read_csv(path)

def freshness(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return "no data yet"
    mtime = path.stat().st_mtime
    import datetime
    dt = datetime.datetime.fromtimestamp(mtime)
    return dt.strftime("Updated %b %d, %Y %H:%M")


# ── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🏀 NBA\nDashboard")
    st.markdown("---")
    page = st.radio(
        "View",
        ["Defense vs Position", "Player Stats", "Referee Stats", "Team Rebounding"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("##### Data Sources")
    sources = {
        "defense_14d.csv":    "Hashtag Basketball",
        "per_game.csv":       "Basketball Reference",
        "per_36.csv":         "Basketball Reference",
        "game_totals.csv":    "Basketball Reference",
        "ref_stats.csv":      "NBA Stuffer",
        "def_rebounds.csv":   "Team Rankings",
        "off_rebounds.csv":   "Team Rankings",
        "assists.csv":        "Team Rankings",
        "pace.csv":           "Team Rankings",
    }
    for fname, label in sources.items():
        path = DATA_DIR / fname
        dot = "🟢" if path.exists() else "🔴"
        st.markdown(f"{dot} `{label}`")


# ── pages ────────────────────────────────────────────────────────────────────

def defense_page():
    st.markdown("# Defense vs Position")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("Last 14 days • opponent fantasy points allowed by position")
    with col2:
        st.markdown(f'<span class="freshness-badge">{freshness("defense_14d.csv")}</span>', unsafe_allow_html=True)

    df_14 = load("defense_14d.csv")
    df_season = load("defense_season.csv")

    tab1, tab2 = st.tabs(["Last 14 Days", "Full Season"])

    with tab1:
        if df_14 is None:
            st.info("Run the scraper to populate this data: `python scrapers/scrape_defense.py`")
        else:
            pos_filter = st.multiselect("Position", options=df_14.columns.tolist()[1:] if len(df_14.columns) > 1 else [], default=[])
            st.dataframe(df_14, use_container_width=True, hide_index=True)

    with tab2:
        if df_season is None:
            st.info("No season data yet.")
        else:
            st.dataframe(df_season, use_container_width=True, hide_index=True)


def player_stats_page():
    st.markdown("# Player Stats")
    st.markdown(f'<span class="freshness-badge">{freshness("per_game.csv")}</span>', unsafe_allow_html=True)

    df_pg   = load("per_game.csv")
    df_p36  = load("per_36.csv")
    df_tot  = load("game_totals.csv")

    if df_pg is None:
        st.info("Run `python scrapers/scrape_bball_ref.py` to fetch data.")
        return

    # Clean bball-ref multi-header artifact
    for df in [df_pg, df_p36, df_tot]:
        if df is not None and "Rk" in df.columns:
            df.drop(df[df["Rk"] == "Rk"].index, inplace=True)
            df.reset_index(drop=True, inplace=True)

    search = st.text_input("Search player", placeholder="e.g. Jokic")
    view   = st.radio("View", ["Per Game", "Per 36 Min", "Totals"], horizontal=True)

    df_map = {"Per Game": df_pg, "Per 36 Min": df_p36, "Totals": df_tot}
    df = df_map[view]

    if df is not None:
        if search:
            df = df[df["Player"].str.contains(search, case=False, na=False)]
        st.dataframe(df, use_container_width=True, hide_index=True)


def referee_page():
    st.markdown("# Referee Stats")
    col1, col2 = st.columns([3,1])
    with col2:
        st.markdown(f'<span class="freshness-badge">{freshness("ref_stats.csv")}</span>', unsafe_allow_html=True)

    df_ref  = load("ref_stats.csv")
    df_assign = load("ref_assignments.csv")

    tab1, tab2 = st.tabs(["Season Stats", "Today's Assignments"])

    with tab1:
        if df_ref is None:
            st.info("Run `python scrapers/scrape_refs.py`")
        else:
            sort_col = st.selectbox("Sort by", df_ref.columns.tolist(), index=0)
            asc = st.checkbox("Ascending", value=True)
            st.dataframe(df_ref.sort_values(sort_col, ascending=asc), use_container_width=True, hide_index=True)

    with tab2:
        if df_assign is None:
            st.info("Run `python scrapers/scrape_assignments.py` (requires curl_cffi)")
        else:
            st.dataframe(df_assign, use_container_width=True, hide_index=True)


def rebounding_page():
    st.markdown("# Team Rebounding & Pace")
    st.markdown(f'<span class="freshness-badge">{freshness("def_rebounds.csv")}</span>', unsafe_allow_html=True)

    df_def  = load("def_rebounds.csv")
    df_off  = load("off_rebounds.csv")
    df_ast  = load("assists.csv")
    df_pace = load("pace.csv")

    if df_def is None:
        st.info("Run `python scrapers/scrape_teamrankings.py`")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Defensive Rebounding %")
        st.dataframe(df_def, use_container_width=True, hide_index=True)
        st.markdown("### Opponent Assists / Game")
        if df_ast is not None:
            st.dataframe(df_ast, use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Offensive Rebounding %")
        if df_off is not None:
            st.dataframe(df_off, use_container_width=True, hide_index=True)
        st.markdown("### Pace (Possessions / Game)")
        if df_pace is not None:
            st.dataframe(df_pace, use_container_width=True, hide_index=True)


# ── router ───────────────────────────────────────────────────────────────────
if page == "Defense vs Position":
    defense_page()
elif page == "Player Stats":
    player_stats_page()
elif page == "Referee Stats":
    referee_page()
elif page == "Team Rebounding":
    rebounding_page()
