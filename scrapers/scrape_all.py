"""
scrapers/scrape_all.py
Run this daily (via GitHub Actions or locally) to refresh all data files.
Outputs CSVs to the /data directory.
"""

import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def save(df, filename):
    path = DATA_DIR / filename
    df.to_csv(path, index=False)
    print(f"  ✓ Saved {filename} ({len(df)} rows)")


# ── 1. Hashtag Basketball: Defense vs Position ────────────────────────────────
def scrape_defense(duration="14", filename="defense_14d.csv"):
    print(f"Scraping hashtag defense (duration={duration})...")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://hashtagbasketball.com/nba-defense-vs-position",
        "X-MicrosoftAjax": "Delta=true",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    url = "https://hashtagbasketball.com/nba-defense-vs-position"
    r = session.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    viewstate     = soup.find("input", {"id": "__VIEWSTATE"})["value"]
    viewstate_gen = (soup.find("input", {"id": "__VIEWSTATEGENERATOR"}) or {}).get("value", "")
    event_val     = (soup.find("input", {"id": "__EVENTVALIDATION"}) or {}).get("value", "")

    post_data = {
        "ctl00$ScriptManager1":                    "ctl00$UpdatePanel1|ctl00$ContentPlaceHolder1$DDDURATION",
        "__EVENTTARGET":                           "ctl00$ContentPlaceHolder1$DDDURATION",
        "__EVENTARGUMENT":                         "",
        "__LASTFOCUS":                             "",
        "__VIEWSTATE":                             viewstate,
        "__VIEWSTATEGENERATOR":                    viewstate_gen,
        "__EVENTVALIDATION":                       event_val,
        "ctl00$ContentPlaceHolder1$DDDURATION":    duration,
        "ctl00$ContentPlaceHolder1$RBL1":          "PG",
        "ctl00$ContentPlaceHolder1$DropDownList1": "All positions",
        "ctl00$ContentPlaceHolder1$DropDownList2": "All Teams",
        "__ASYNCPOST":                             "true",
    }
    r = session.post(url, data=post_data, headers=headers)
    html_chunks = re.findall(r'<table.*?</table>', r.text, re.DOTALL)
    df = pd.read_html(StringIO(html_chunks[3]))[0]
    save(df, filename)


# ── 2. Basketball Reference ───────────────────────────────────────────────────
BREF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def scrape_bball_ref(url, filename):
    print(f"Scraping {filename}...")
    time.sleep(4)  # bball-ref rate limit: be respectful
    df = pd.read_html(url, attrs={"id": "per_game_stats"} if "per_game" in url else None)[0]
    # Drop repeated header rows that bball-ref injects
    if "Rk" in df.columns:
        df = df[df["Rk"] != "Rk"].reset_index(drop=True)
    save(df, filename)


def scrape_all_bball_ref():
    season = "2026"
    scrape_bball_ref(f"https://www.basketball-reference.com/leagues/NBA_{season}_per_game.html", "per_game.csv")
    scrape_bball_ref(f"https://www.basketball-reference.com/leagues/NBA_{season}_per_minute.html", "per_36.csv")
    scrape_bball_ref(f"https://www.basketball-reference.com/leagues/NBA_{season}_totals.html", "game_totals.csv")


# ── 3. Team Rankings ─────────────────────────────────────────────────────────
def scrape_teamrankings():
    print("Scraping Team Rankings...")
    base = "https://www.teamrankings.com/nba/stat/"
    stats = {
        "defensive-rebounding-pct":    "def_rebounds.csv",
        "offensive-rebounding-pct":    "off_rebounds.csv",
        "opponent-assists-per-game":   "assists.csv",
        "possessions-per-game":        "pace.csv",
    }
    for slug, filename in stats.items():
        time.sleep(2)
        df = pd.read_html(f"{base}{slug}")[0]
        save(df, filename)


# ── 4. NBA Stuffer: Referee Stats ────────────────────────────────────────────
def scrape_ref_stats():
    print("Scraping ref stats...")
    df = pd.read_html("https://www.nbastuffer.com/2025-2026-nba-referee-stats/")[0]
    save(df, "ref_stats.csv")


# ── 5. NBA Official: Referee Assignments (requires curl_cffi) ─────────────────
def scrape_ref_assignments():
    print("Scraping referee assignments...")
    try:
        from curl_cffi import requests as cffi_requests
        r = cffi_requests.get(
            "https://official.nba.com/referee-assignments/",
            impersonate="chrome120",
        )
        soup = BeautifulSoup(r.text, "html.parser")
        tables = soup.find_all("table")
        if tables:
            df = pd.read_html(StringIO(str(tables[0])))[0]
            save(df, "ref_assignments.csv")
        else:
            print("  ⚠ No table found in referee assignments page")
    except ImportError:
        print("  ⚠ curl_cffi not installed — skipping referee assignments")
    except Exception as e:
        print(f"  ⚠ Referee assignments failed: {e}")


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scrape_defense(duration="14", filename="defense_14d.csv")
    scrape_defense(duration="1",  filename="defense_season.csv")
    scrape_all_bball_ref()
    scrape_teamrankings()
    scrape_ref_stats()
    scrape_ref_assignments()
    print("\n✅ All done!")
