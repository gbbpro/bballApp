import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from io import StringIO

st.set_page_config(page_title="Props Calculator", page_icon="🏀", layout="wide")

DATA_DIR = Path("data")

# ── styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Bebas+Neue&family=DM+Sans:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.05em; }
.stApp { background: #0d0d0f; color: #e8e8e8; }
section[data-testid="stSidebar"] { background: #111114; border-right: 1px solid #222; }

.proj-card {
    background: #16161a;
    border: 1px solid #2a2a2f;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    text-align: center;
}
.proj-label { font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 4px; }
.proj-value { font-family: 'DM Mono', monospace; font-size: 2.2rem; color: #f0f0f0; line-height: 1; }
.proj-sub   { font-family: 'DM Mono', monospace; font-size: 0.85rem; color: #888; margin-top: 4px; }

.odds-card {
    background: #0f1a0f;
    border: 1px solid #1a3a1a;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    text-align: center;
}
.odds-label { font-size: 0.65rem; color: #4ade80; text-transform: uppercase; letter-spacing: 0.12em; }
.odds-line  { font-family: 'DM Mono', monospace; font-size: 1.1rem; color: #e8e8e8; margin: 4px 0 2px; }
.odds-over  { font-family: 'DM Mono', monospace; font-size: 0.9rem; color: #4ade80; }
.odds-under { font-family: 'DM Mono', monospace; font-size: 0.9rem; color: #f87171; }

.combo-card {
    background: #16161a;
    border: 1px solid #2a2a2f;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    text-align: center;
}
.combo-label { font-size: 0.65rem; color: #888; text-transform: uppercase; letter-spacing: 0.1em; }
.combo-value { font-family: 'DM Mono', monospace; font-size: 1.3rem; color: #c084fc; }

.adj-row {
    background: #16161a;
    border: 1px solid #2a2a2f;
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    color: #aaa;
    display: flex;
    justify-content: space-between;
}
.section-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 0.08em;
    color: #888;
    margin: 1rem 0 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# ── data loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_csv(name):
    p = DATA_DIR / name
    return pd.read_csv(p) if p.exists() else None

def get_per_game():
    df = load_csv("per_game.csv")
    if df is None:
        return None
    # Drop repeated bball-ref header rows
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"].reset_index(drop=True)
    # Keep last entry per player (most recent team)
    df = df.drop_duplicates(subset="Player", keep="last").reset_index(drop=True)
    return df

def get_defense():
    df14  = load_csv("defense_14d.csv")
    dfSzn = load_csv("defense_season.csv")
    return df14, dfSzn

def get_pace():      return load_csv("pace.csv")
def get_def_reb():   return load_csv("def_rebounds.csv")
def get_off_reb():   return load_csv("off_rebounds.csv")

# ── team name normalisation ───────────────────────────────────────────────────
# bball-ref abbrev → full team name (for Team Rankings lookups)
TEAM_MAP = {
    "ATL":"Atlanta Hawks","BOS":"Boston Celtics","BRK":"Brooklyn Nets",
    "CHO":"Charlotte Hornets","CHI":"Chicago Bulls","CLE":"Cleveland Cavaliers",
    "DAL":"Dallas Mavericks","DEN":"Denver Nuggets","DET":"Detroit Pistons",
    "GSW":"Golden State Warriors","HOU":"Houston Rockets","IND":"Indiana Pacers",
    "LAC":"LA Clippers","LAL":"LA Lakers","MEM":"Memphis Grizzlies",
    "MIA":"Miami Heat","MIL":"Milwaukee Bucks","MIN":"Minnesota Timberwolves",
    "NOP":"New Orleans Pelicans","NYK":"New York Knicks","OKC":"Oklahoma City Thunder",
    "ORL":"Orlando Magic","PHI":"Philadelphia 76ers","PHO":"Phoenix Suns",
    "POR":"Portland Trail Blazers","SAC":"Sacramento Kings","SAS":"San Antonio Spurs",
    "TOR":"Toronto Raptors","UTA":"Utah Jazz","WAS":"Washington Wizards",
}

# bball-ref abbrev → Hashtag Basketball DEF_POS abbreviation (from your doc)
HASHTAG_MAP = {
    "ATL":"ATL","BOS":"BOS","BRK":"bkn","CHO":"CHA","CHI":"CHI",
    "CLE":"CLE","DAL":"DAL","DEN":"DEN","DET":"DET","GSW":"GS",
    "HOU":"HOU","IND":"IND","LAC":"LAC","LAL":"LAL","MEM":"MEM",
    "MIA":"MIA","MIL":"MIL","MIN":"MIN","NOP":"NO","NYK":"NY",
    "OKC":"OKC","ORL":"ORL","PHI":"PHI","PHO":"PHO","POR":"POR",
    "SAC":"sac","SAS":"sa","TOR":"TOR","UTA":"UTA","WAS":"WAS",
}

LEAGUE_AVG_PACE   = 98.0   # fallback if data missing
LEAGUE_AVG_DEF_REB = 0.745
LEAGUE_AVG_OFF_REB = 0.255
LEAGUE_AVG_OPP_AST = 24.5


# ── helper: lookup team rankings value ───────────────────────────────────────
def tr_lookup(df, team_full, col_hint="2025"):
    """Return the first numeric column value for a team in a teamrankings df."""
    if df is None:
        return None
    # Find team column (usually 'Team')
    team_col = [c for c in df.columns if "team" in c.lower()]
    if not team_col:
        return None
    team_col = team_col[0]
    row = df[df[team_col].str.contains(team_full.split()[-1], case=False, na=False)]
    if row.empty:
        return None
    # Find the most recent season numeric column
    num_cols = [c for c in df.columns if c != team_col]
    for c in num_cols:
        try:
            val = float(str(row.iloc[0][c]).replace("%",""))
            return val
        except:
            continue
    return None


# ── Poisson odds ─────────────────────────────────────────────────────────────
def poisson_odds(mean, line, american=True):
    from scipy.stats import poisson
    p_under = poisson.cdf(line, mean)        # P(X <= line)  -- "under" includes line
    p_over  = 1 - poisson.cdf(line - 0.5, mean)   # P(X > line - 0.5)

    def to_american(p):
        if p <= 0 or p >= 1:
            return "N/A"
        if p <= 0.5:
            return f"+{round((1/p - 1)*100)}"
        else:
            return f"-{round(p/(1-p)*100)}"

    return to_american(p_over), to_american(p_under)


# ── Monte Carlo points simulation ────────────────────────────────────────────
def simulate_points(fga_rate, two_pa_pct, two_p, three_pa_pct, three_p, ft_rate, ft_pct,
                    xmp_pct, pace_adj, home_adj, off_reb_adj, def_reb_adj, pts_adj,
                    n=1000):
    """
    Mirrors Excel:
    xPoints = xMP% * PaceAdj * HomeAdv * OffRebAdj * DefRebAdj *
              (2PA_rate * 2P% * 2  +  3PA_rate * 3P% * 3  +  FT_rate * FT%)
    Monte Carlo: for each trial, simulate actual 2PM, 3PM, FTM via binomial draws.
    """
    rng = np.random.default_rng()

    # Expected attempts per adjusted minute share
    scale = xmp_pct * pace_adj * home_adj * off_reb_adj * def_reb_adj * pts_adj

    avg_fga  = fga_rate * scale
    avg_2pa  = avg_fga * two_pa_pct
    avg_3pa  = avg_fga * three_pa_pct
    avg_fta  = fga_rate * ft_rate * scale   # ft_rate relative to fga

    # Simulate
    two_pa_trials  = rng.poisson(avg_2pa,  n)
    three_pa_trials= rng.poisson(avg_3pa,  n)
    fta_trials     = rng.poisson(avg_fta,  n)

    two_pm   = rng.binomial(two_pa_trials,   np.clip(two_p,   0, 1))
    three_pm = rng.binomial(three_pa_trials, np.clip(three_p, 0, 1))
    ftm      = rng.binomial(fta_trials,      np.clip(ft_pct,  0, 1))

    pts = two_pm * 2 + three_pm * 3 + ftm
    return pts


def pts_odds(simulations, line, american=True):
    p_over  = np.mean(simulations > line)
    p_under = np.mean(simulations <= line)

    def to_american(p):
        if p <= 0 or p >= 1:
            return "N/A"
        if p <= 0.5:
            return f"+{round((1/p - 1)*100)}"
        else:
            return f"-{round(p/(1-p)*100)}"

    return to_american(p_over), to_american(p_under)


# ── main UI ──────────────────────────────────────────────────────────────────
st.markdown("# Props Calculator")

pg_df = get_per_game()
if pg_df is None:
    st.error("No player data found. Run the scraper first: `python scrapers/scrape_all.py`")
    st.stop()

pace_df    = get_pace()
def_reb_df = get_def_reb()
off_reb_df = get_off_reb()
def14_df, defszn_df = get_defense()

# ── Step 1: pick teams playing ───────────────────────────────────────────────
st.markdown("### 1 · Select Matchup")
all_teams = sorted(TEAM_MAP.keys())
col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    away_team = st.selectbox("Away Team", all_teams, format_func=lambda x: f"{x} — {TEAM_MAP[x]}")
with col2:
    home_team = st.selectbox("Home Team", [t for t in all_teams if t != away_team],
                             format_func=lambda x: f"{x} — {TEAM_MAP[x]}")
with col3:
    player_team = st.radio("Player's team", [away_team, home_team], horizontal=True)

is_home = (player_team == home_team)
opponent = home_team if player_team == away_team else away_team
opponent_full = TEAM_MAP[opponent]

# ── Step 2: pick player ──────────────────────────────────────────────────────
st.markdown("### 2 · Select Player")

team_col = "Tm" if "Tm" in pg_df.columns else "Team" if "Team" in pg_df.columns else None
if team_col:
    roster = pg_df[pg_df[team_col] == player_team]["Player"].tolist()
else:
    roster = pg_df["Player"].tolist()
if not roster:
    roster = pg_df["Player"].tolist()

col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    player = st.selectbox("Player", sorted(roster))
with col2:
    positions = ["PG","SG","SF","PF","C"]
    default_pos = "SG"
    if player:
        row = pg_df[pg_df["Player"] == player]
        if not row.empty and "Pos" in row.columns:
            raw_pos = str(row.iloc[0]["Pos"]).split("-")[0].strip()
            default_pos = raw_pos if raw_pos in positions else "SG"
    alt_pos = st.selectbox("Position (ALT override)", positions,
                           index=positions.index(default_pos))
with col3:
    xmp = st.number_input("Adj. Minutes", min_value=0.0, max_value=48.0,
                          value=0.0, step=0.5,
                          help="Leave 0 to use season average")

# ── pull player stats ─────────────────────────────────────────────────────────
if not player:
    st.stop()

prow = pg_df[pg_df["Player"] == player].iloc[0]

def safe_float(val, default=0.0):
    try:    return float(val)
    except: return default

mp_avg   = safe_float(prow.get("MP", 0))
fga_avg  = safe_float(prow.get("FGA", 0))
fg_pct   = safe_float(prow.get("FG%", 0))
fga3_avg = safe_float(prow.get("3PA", 0))
fg3_pct  = safe_float(prow.get("3P%", 0))
fta_avg  = safe_float(prow.get("FTA", 0))
ft_pct   = safe_float(prow.get("FT%", 0))
reb_avg  = safe_float(prow.get("TRB", 0))
ast_avg  = safe_float(prow.get("AST", 0))
pts_avg  = safe_float(prow.get("PTS", 0))
stl_avg  = safe_float(prow.get("STL", 0))
blk_avg  = safe_float(prow.get("BLK", 0))

# Derived shooting rates (as fractions of FGA)
two_pa_pct  = (fga_avg - fga3_avg) / fga_avg if fga_avg > 0 else 0
three_pa_pct = fga3_avg / fga_avg if fga_avg > 0 else 0
two_p        = (fg_pct * fga_avg - fg3_pct * fga3_avg) / max(fga_avg - fga3_avg, 0.01)
ft_rate      = fta_avg / fga_avg if fga_avg > 0 else 0

# ── Step 3: compute adjustments ──────────────────────────────────────────────
# Minutes adjustment
xmp_pct = (xmp / mp_avg) if (xmp > 0 and mp_avg > 0) else 1.0

# Home advantage
home_adj = np.sqrt(1.01) if is_home else 1 / np.sqrt(1.01)

# Pace adjustment
player_team_full   = TEAM_MAP[player_team]
opp_pace = tr_lookup(pace_df, opponent_full)
own_pace = tr_lookup(pace_df, player_team_full)
if opp_pace and own_pace and opp_pace > 0:
    pace_adj = np.sqrt(opp_pace * own_pace) / opp_pace
else:
    pace_adj = 1.0

# Defensive rebound adjustment
def_reb_pct = tr_lookup(def_reb_df, opponent_full)
if def_reb_pct:
    def_reb_pct_dec = def_reb_pct / 100 if def_reb_pct > 1 else def_reb_pct
    def_reb_adj = (1 - def_reb_pct_dec) / LEAGUE_AVG_OFF_REB
else:
    def_reb_adj = 1.0

# Offensive rebound adjustment
off_reb_pct = tr_lookup(off_reb_df, opponent_full)
if off_reb_pct:
    off_reb_pct_dec = off_reb_pct / 100 if off_reb_pct > 1 else off_reb_pct
    off_reb_adj = (1 - off_reb_pct_dec) / LEAGUE_AVG_DEF_REB
else:
    off_reb_adj = 1.0

# Defense vs Position multiplier from hashtag data
def get_dvp_multiplier(pos, stat, use_14d=True):
    df = def14_df if use_14d else defszn_df
    if df is None:
        return 1.0
    try:
        hashtag_abbrev = HASHTAG_MAP.get(opponent, "").upper()
        # Filter by position and team
        pos_mask  = df["Position"].str.upper() == pos.upper()
        team_mask = df["Team"].str.upper().str.contains(hashtag_abbrev)
        opp_row   = df[pos_mask & team_mask]
        if opp_row.empty:
            # fallback: team only
            opp_row = df[team_mask]
        if opp_row.empty:
            return 1.0
        val_col = f"{stat.upper()}_VAL"
        if val_col not in df.columns:
            return 1.0
        val        = float(opp_row.iloc[0][val_col])
        league_avg = float(df[val_col].mean())
        return val / league_avg if league_avg > 0 else 1.0
    except:
        return 1.0

use_14d = st.toggle("Use Last 14 Days defense data", value=True)

pts_adj = get_dvp_multiplier(alt_pos, "PTS", use_14d)
reb_adj = get_dvp_multiplier(alt_pos, "REB", use_14d)
ast_adj = get_dvp_multiplier(alt_pos, "AST", use_14d)

# ── projected stats ───────────────────────────────────────────────────────────
scale_base = xmp_pct * pace_adj * home_adj

x_reb = reb_avg * scale_base * off_reb_adj * def_reb_adj * reb_adj
x_ast = ast_avg * scale_base * ast_adj
x_pts_formula = scale_base * off_reb_adj * def_reb_adj * pts_adj * (
    two_pa_pct * fga_avg * two_p * 2 +
    three_pa_pct * fga_avg * fg3_pct * 3 +
    fta_avg * ft_pct
)

# Monte Carlo for points
sims = simulate_points(
    fga_rate=fga_avg, two_pa_pct=two_pa_pct, two_p=two_p,
    three_pa_pct=three_pa_pct, three_p=fg3_pct,
    ft_rate=ft_rate, ft_pct=ft_pct,
    xmp_pct=xmp_pct, pace_adj=pace_adj, home_adj=home_adj,
    off_reb_adj=off_reb_adj, def_reb_adj=def_reb_adj, pts_adj=pts_adj,
    n=2000
)

x_pts_sim = float(np.mean(sims))

# ── Step 3 display: adjustments ──────────────────────────────────────────────
st.markdown("---")
st.markdown("### 3 · Adjustments")

acols = st.columns(7)
adj_items = [
    ("Home Adv",    f"{home_adj:.4f}"),
    ("xMP %",       f"{xmp_pct*100:.1f}%"),
    ("Pace Adj",    f"{pace_adj:.3f}"),
    ("Off Reb Adj", f"{off_reb_adj:.3f}"),
    ("Def Reb Adj", f"{def_reb_adj:.3f}"),
    ("Pts Def Adj", f"{pts_adj:.3f}"),
    ("Reb/Ast Adj", f"{reb_adj:.3f} / {ast_adj:.3f}"),
]
for col, (label, val) in zip(acols, adj_items):
    col.markdown(f"""
    <div class="proj-card" style="padding:0.75rem">
      <div class="proj-label">{label}</div>
      <div class="proj-sub" style="font-size:1.1rem;color:#e8e8e8">{val}</div>
    </div>""", unsafe_allow_html=True)

# ── Step 4: lines input + projections ────────────────────────────────────────
st.markdown("---")
st.markdown("### 4 · Lines & Projections")

lcol1, lcol2, lcol3 = st.columns(3)
with lcol1:
    pts_line = st.number_input("Points Line", value=round(x_pts_sim * 2) / 2, step=0.5)
with lcol2:
    reb_line = st.number_input("Rebounds Line", value=round(x_reb * 2) / 2, step=0.5)
with lcol3:
    ast_line = st.number_input("Assists Line", value=round(x_ast * 2) / 2, step=0.5)

# Odds
pts_over, pts_under = pts_odds(sims, pts_line)
reb_over, reb_under = poisson_odds(x_reb, reb_line)
ast_over, ast_under = poisson_odds(x_ast, ast_line)

# Display projection cards + odds
for label, proj, line, over, under in [
    ("Points",   x_pts_sim, pts_line, pts_over, pts_under),
    ("Rebounds", x_reb,     reb_line, reb_over, reb_under),
    ("Assists",  x_ast,     ast_line, ast_over, ast_under),
]:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"""
        <div class="proj-card">
          <div class="proj-label">x_{label}</div>
          <div class="proj-value">{proj:.2f}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="odds-card">
          <div class="odds-label">Line {line}</div>
          <div class="odds-over">Over &nbsp; {over}</div>
          <div class="odds-under">Under {under}</div>
        </div>""", unsafe_allow_html=True)

# ── Combo projections ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Combo Props")

combos = {
    "PRA":  x_pts_sim + x_reb + x_ast,
    "P+A":  x_pts_sim + x_ast,
    "P+R":  x_pts_sim + x_reb,
    "R+A":  x_reb + x_ast,
    "B+S":  safe_float(prow.get("BLK",0)) * scale_base + safe_float(prow.get("STL",0)) * scale_base,
}

ccols = st.columns(len(combos))
for col, (label, val) in zip(ccols, combos.items()):
    col.markdown(f"""
    <div class="combo-card">
      <div class="combo-label">{label}</div>
      <div class="combo-value">{val:.1f}</div>
    </div>""", unsafe_allow_html=True)

# ── raw player stats expander ─────────────────────────────────────────────────
with st.expander("Raw player stats"):
    st.dataframe(pg_df[pg_df["Player"] == player], use_container_width=True, hide_index=True)
