# NBA Analytics Dashboard

Personal NBA analytics dashboard built with Streamlit.

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/nba-dashboard
cd nba-dashboard
uv sync
```

## Run locally

```bash
# First, populate the data directory
uv run python scrapers/scrape_all.py

# Then launch the app
uv run streamlit run app.py
```

## Deploy to Streamlit Cloud (free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Click **Deploy** — done

## Daily data refresh (GitHub Actions)

The workflow in `.github/workflows/daily_refresh.yml` runs every day at 9am ET,
scrapes all sources, and commits updated CSVs back to the `data/` folder.
Streamlit Cloud picks up the new files automatically.

**To trigger manually:** GitHub → Actions tab → "Daily NBA Data Refresh" → Run workflow

## Project structure

```
nba-dashboard/
├── app.py                          # Streamlit app
├── requirements.txt
├── scrapers/
│   └── scrape_all.py               # All scrapers in one script
├── data/                           # CSVs written here (git-tracked)
│   ├── defense_14d.csv
│   ├── defense_season.csv
│   ├── per_game.csv
│   ├── per_36.csv
│   ├── game_totals.csv
│   ├── ref_stats.csv
│   ├── ref_assignments.csv
│   ├── def_rebounds.csv
│   ├── off_rebounds.csv
│   ├── assists.csv
│   └── pace.csv
└── .github/
    └── workflows/
        └── daily_refresh.yml
```

## Data sources

| File | Source | Scraper method |
|------|--------|---------------|
| defense_*.csv | hashtagbasketball.com | ASP.NET form POST |
| per_game/36/totals.csv | basketball-reference.com | pd.read_html |
| def/off_rebounds, assists, pace | teamrankings.com | pd.read_html |
| ref_stats.csv | nbastuffer.com | pd.read_html |
| ref_assignments.csv | official.nba.com | curl_cffi (Akamai bypass) |
