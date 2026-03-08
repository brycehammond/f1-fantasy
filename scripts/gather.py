#!/usr/bin/env python3
"""
Gather script — collects all F1 Fantasy state and caches it for Claude to analyze.

Run this first. It will:
1. Fetch all driver/constructor prices and IDs from the public API
2. Fetch season info (current round, fixtures)
3. Log into F1 Fantasy via Playwright
4. Scrape your current team, budget, free transfers, DRS boost
5. Scrape available/used chips
6. Fetch scoring history for each driver on your team
7. Save everything to data/state.json

Usage:
    python scripts/gather.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from playwright.async_api import async_playwright

from src.config import (
    API_BASE_URL,
    DATA_DIR,
    F1_EMAIL,
    F1_PASSWORD,
    FANTASY_BASE_URL,
    STATE_DIR,
)

STORAGE_STATE_PATH = STATE_DIR / "auth_state.json"
OUTPUT_PATH = DATA_DIR / "state.json"
HISTORY_DIR = DATA_DIR / "history"


async def fetch_public_api() -> dict:
    """Fetch driver prices, constructor prices, and season info from public API."""
    print("Fetching public API data...")
    async with httpx.AsyncClient(timeout=30) as client:
        players_resp, teams_resp, season_resp = await asyncio.gather(
            client.get(f"{API_BASE_URL}/players"),
            client.get(f"{API_BASE_URL}/teams"),
            client.get(f"{API_BASE_URL}/"),
        )

    players_data = players_resp.json()
    teams_data = teams_resp.json()
    season_data = season_resp.json()

    players = players_data.get("players", players_data if isinstance(players_data, list) else [])
    teams = teams_data.get("teams", teams_data if isinstance(teams_data, list) else [])

    print(f"  {len(players)} drivers, {len(teams)} constructors")
    return {
        "players": players,
        "constructors": teams,
        "season": season_data,
    }


async def fetch_player_scores(player_ids: list[int]) -> dict[int, list]:
    """Fetch scoring history for specific players."""
    print(f"Fetching scoring history for {len(player_ids)} players...")
    scores = {}
    async with httpx.AsyncClient(timeout=30) as client:
        for pid in player_ids:
            try:
                resp = await client.get(
                    f"{API_BASE_URL}/players/{pid}/game_periods_scores",
                    params={"season_name": "2026"},
                )
                if resp.status_code == 200:
                    scores[pid] = resp.json()
            except Exception as e:
                print(f"  Warning: could not fetch scores for player {pid}: {e}")
    return scores


async def scrape_authenticated_data(playwright) -> dict:
    """Log in and scrape current team, chips, and budget."""
    print("Launching browser...")
    browser = await playwright.chromium.launch(headless=False)

    if STORAGE_STATE_PATH.exists():
        context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))
        print("  Restored saved session")
    else:
        context = await browser.new_context()

    page = await context.new_page()

    # Capture API responses as the page loads
    captured_responses = {}

    async def capture_response(response):
        url = response.url
        if response.status != 200:
            return
        try:
            if "picked_teams" in url:
                captured_responses["picked_teams"] = await response.json()
            elif "boosters" in url:
                captured_responses["boosters"] = await response.json()
            elif "/players" in url and "game_periods" not in url:
                captured_responses["players_auth"] = await response.json()
        except Exception:
            pass

    page.on("response", capture_response)

    # Navigate and check login
    print("Navigating to F1 Fantasy...")
    await page.goto(FANTASY_BASE_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)

    logged_in = await _check_logged_in(page)
    if not logged_in:
        print("Not logged in, attempting login...")
        logged_in = await _do_login(page)
        if not logged_in:
            print("ERROR: Login failed. Check credentials in .env")
            await browser.close()
            return {}

    # Save session for next time
    await page.context.storage_state(path=str(STORAGE_STATE_PATH))

    # Navigate to My Team to trigger API calls
    print("Loading My Team page...")
    await page.goto(f"{FANTASY_BASE_URL}my-team", wait_until="networkidle")
    await page.wait_for_timeout(5000)

    # Try direct API fetch using the authenticated session cookies
    if "picked_teams" not in captured_responses:
        print("  Fetching team data via page context...")
        try:
            result = await page.evaluate("""
                async () => {
                    const urls = [
                        '/api/picked_teams?my_current_picked_teams=true&my_next_picked_teams=true',
                        'https://fantasy-api.formula1.com/f1/2026/picked_teams?my_current_picked_teams=true&my_next_picked_teams=true',
                    ];
                    for (const url of urls) {
                        try {
                            const resp = await fetch(url, {credentials: 'include'});
                            if (resp.ok) return await resp.json();
                        } catch {}
                    }
                    return null;
                }
            """)
            if result:
                captured_responses["picked_teams"] = result
        except Exception:
            pass

    if "boosters" not in captured_responses:
        try:
            result = await page.evaluate("""
                async () => {
                    const urls = [
                        '/api/boosters',
                        'https://fantasy-api.formula1.com/f1/2026/boosters',
                    ];
                    for (const url of urls) {
                        try {
                            const resp = await fetch(url, {credentials: 'include'});
                            if (resp.ok) return await resp.json();
                        } catch {}
                    }
                    return null;
                }
            """)
            if result:
                captured_responses["boosters"] = result
        except Exception:
            pass

    # Parse captured data
    auth_data = {}

    # Current team
    team_raw = captured_responses.get("picked_teams")
    if team_raw:
        auth_data["current_team_raw"] = team_raw
        auth_data["current_team"] = _parse_team(team_raw)
        print(f"  Team: {', '.join(d['name'] for d in auth_data['current_team']['drivers'])}")
    else:
        print("  WARNING: Could not fetch current team from API, falling back to DOM scraping")
        auth_data["current_team"] = await _scrape_team_from_dom(page)

    # Chips
    boosters_raw = captured_responses.get("boosters")
    if boosters_raw:
        auth_data["chips_raw"] = boosters_raw
        auth_data["chips"] = _parse_chips(boosters_raw)
        print(f"  Chips available: {', '.join(auth_data['chips']['available'])}")
    else:
        auth_data["chips"] = {"available": [], "used": {}}

    # Take a screenshot for Claude to see the page state
    screenshot_path = DATA_DIR / "my_team_screenshot.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"  Screenshot saved: {screenshot_path}")

    await browser.close()
    return auth_data


def _parse_team(data: dict) -> dict:
    """Parse picked_teams API response into a clean structure."""
    picks = data if isinstance(data, list) else data.get("picked_teams", [data])
    if not picks:
        return {"drivers": [], "constructors": [], "budget_remaining": 0, "free_transfers": 2, "drs_boost": None}

    current = picks[0]
    drivers = []
    constructors = []
    drs_boost = None

    for player in current.get("picked_players", []):
        p = player.get("player", {})
        entry = {
            "name": p.get("display_name", p.get("last_name", "")),
            "id": p.get("id"),
            "price": p.get("price"),
            "team": p.get("team_name", p.get("team", {}).get("name", "")),
            "season_score": player.get("score"),
        }
        if p.get("position") == "Driver":
            drivers.append(entry)
        else:
            constructors.append(entry)

        if player.get("is_drs_boosted"):
            drs_boost = entry["name"]

    return {
        "drivers": drivers,
        "constructors": constructors,
        "budget_remaining": current.get("budget_remaining", 0.0),
        "free_transfers": current.get("free_transfers", 2),
        "drs_boost": drs_boost,
        "total_value": sum(d.get("price", 0) or 0 for d in drivers + constructors),
    }


def _parse_chips(data: dict) -> dict:
    """Parse boosters API response."""
    available = []
    used = {}
    for booster in data.get("boosters", data if isinstance(data, list) else []):
        name = booster.get("name", "").lower().replace(" ", "_")
        if booster.get("is_used"):
            used[name] = booster.get("game_period_id")
        else:
            available.append(name)
    return {"available": available, "used": used}


async def _scrape_team_from_dom(page) -> dict:
    """Fallback: scrape team from the page DOM."""
    team = {"drivers": [], "constructors": [], "budget_remaining": 0, "free_transfers": 2, "drs_boost": None}

    driver_cards = page.locator('[class*="driver"], [class*="player"], [data-type="driver"]')
    count = await driver_cards.count()
    for i in range(count):
        card = driver_cards.nth(i)
        name_el = card.locator('[class*="name"]').first
        try:
            name = await name_el.text_content(timeout=2000)
            if name:
                team["drivers"].append({"name": name.strip()})
        except Exception:
            pass

    constructor_cards = page.locator('[class*="constructor"], [data-type="constructor"]')
    count = await constructor_cards.count()
    for i in range(count):
        card = constructor_cards.nth(i)
        name_el = card.locator('[class*="name"]').first
        try:
            name = await name_el.text_content(timeout=2000)
            if name:
                team["constructors"].append({"name": name.strip()})
        except Exception:
            pass

    return team


async def _check_logged_in(page) -> bool:
    """Check if already logged in."""
    for selector in ["text=My Team", '[data-testid="user-menu"]', 'a[href*="my-team"]']:
        try:
            if await page.locator(selector).first.is_visible(timeout=3000):
                print("  Already logged in")
                return True
        except Exception:
            continue
    return False


async def _do_login(page) -> bool:
    """Perform the login flow."""
    if not F1_EMAIL or not F1_PASSWORD:
        print("ERROR: F1_FANTASY_EMAIL and F1_FANTASY_PASSWORD must be set in .env")
        return False

    sign_in_btn = page.locator("text=Sign In").first
    try:
        if await sign_in_btn.is_visible(timeout=5000):
            await sign_in_btn.click()
            await page.wait_for_load_state("networkidle")
    except Exception:
        pass

    # Email
    email_input = page.locator('input[type="email"], input[name="email"], input#email')
    await email_input.wait_for(state="visible", timeout=15000)
    await email_input.fill(F1_EMAIL)

    next_btn = page.locator('button:has-text("Next"), button:has-text("Continue"), button[type="submit"]').first
    await next_btn.click()
    await page.wait_for_timeout(2000)

    # Password
    password_input = page.locator('input[type="password"], input[name="password"]')
    await password_input.wait_for(state="visible", timeout=15000)
    await password_input.fill(F1_PASSWORD)

    login_btn = page.locator('button:has-text("Log In"), button:has-text("Sign In"), button[type="submit"]').first
    await login_btn.click()

    await page.wait_for_url("**fantasy.formula1.com**", timeout=30000)
    await page.wait_for_load_state("networkidle")

    return await _check_logged_in(page)


def save_history(state: dict):
    """Save a timestamped copy to history for trend tracking."""
    HISTORY_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = HISTORY_DIR / f"state_{ts}.json"
    history_file.write_text(json.dumps(state, indent=2))
    print(f"History saved: {history_file}")


async def main():
    # 1. Public API data
    public_data = await fetch_public_api()

    # 2. Authenticated data via browser
    async with async_playwright() as p:
        auth_data = await scrape_authenticated_data(p)

    # 3. Fetch scoring history for current team players
    player_ids = []
    if auth_data.get("current_team"):
        for d in auth_data["current_team"].get("drivers", []):
            if d.get("id"):
                player_ids.append(d["id"])
    scoring_history = await fetch_player_scores(player_ids) if player_ids else {}

    # 4. Determine current round
    current_round = None
    season = public_data.get("season", {})
    for period in season.get("game_periods", []):
        if period.get("is_current"):
            current_round = period
            break
    if not current_round:
        for period in season.get("game_periods", []):
            if not period.get("is_finished"):
                current_round = period
                break

    # 5. Assemble complete state
    state = {
        "gathered_at": datetime.now().isoformat(),
        "current_round": current_round,
        "drivers": public_data["players"],
        "constructors": public_data["constructors"],
        "season": season,
        "my_team": auth_data.get("current_team", {}),
        "chips": auth_data.get("chips", {}),
        "scoring_history": {str(k): v for k, v in scoring_history.items()},
        "raw_api": {
            "picked_teams": auth_data.get("current_team_raw"),
            "boosters": auth_data.get("chips_raw"),
        },
    }

    # 6. Save
    OUTPUT_PATH.write_text(json.dumps(state, indent=2))
    print(f"\nState saved to: {OUTPUT_PATH}")
    save_history(state)

    # 7. Print summary for Claude
    print("\n" + "=" * 60)
    print("CURRENT STATE SUMMARY")
    print("=" * 60)

    if current_round:
        print(f"Next race: Round {current_round.get('game_period_id', '?')} — {current_round.get('name', '?')}")

    team = auth_data.get("current_team", {})
    if team:
        print(f"\nMy Team:")
        print(f"  Drivers: {', '.join(d.get('name', '?') for d in team.get('drivers', []))}")
        print(f"  Constructors: {', '.join(c.get('name', '?') for c in team.get('constructors', []))}")
        print(f"  DRS Boost: {team.get('drs_boost', 'not set')}")
        print(f"  Budget remaining: ${team.get('budget_remaining', 0):.1f}M")
        print(f"  Free transfers: {team.get('free_transfers', '?')}")

    chips = auth_data.get("chips", {})
    if chips:
        print(f"  Chips available: {', '.join(chips.get('available', [])) or 'none'}")
        if chips.get("used"):
            print(f"  Chips used: {chips['used']}")

    print(f"\nDriver prices (all {len(public_data['players'])}):")
    for p in sorted(public_data["players"], key=lambda x: x.get("price", 0), reverse=True):
        name = p.get("display_name", p.get("last_name", "?"))
        price = p.get("price", 0)
        team_name = p.get("team_name", p.get("team", {}).get("name", "?"))
        print(f"  {name:25s} {team_name:20s} ${price:.1f}M")

    print(f"\nConstructor prices (all {len(public_data['constructors'])}):")
    for t in sorted(public_data["constructors"], key=lambda x: x.get("price", 0), reverse=True):
        name = t.get("name", t.get("short_name", "?"))
        price = t.get("price", 0)
        print(f"  {name:25s} ${price:.1f}M")

    print(f"\nFull data cached at: {OUTPUT_PATH}")
    print("Now ask Claude to analyze and pick the optimal lineup.")


if __name__ == "__main__":
    asyncio.run(main())
