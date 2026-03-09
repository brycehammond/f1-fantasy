#!/usr/bin/env python3
"""
Gather script — collects all F1 Fantasy state and caches it for Claude to analyze.

Run this first. It will:
1. Fetch all driver/constructor prices and IDs from the public API
2. Fetch season info (current round, fixtures)
3. Log into F1 Fantasy via Playwright
4. Scrape your current team, budget, free transfers, DRS boost
5. Scrape available/used chips
6. Scrape ALL driver/constructor prices from the My Team page
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
    DATA_DIR,
    F1_EMAIL,
    F1_PASSWORD,
    FANTASY_BASE_URL,
    STATE_DIR,
)

STORAGE_STATE_PATH = STATE_DIR / "auth_state.json"
OUTPUT_PATH = DATA_DIR / "state.json"
HISTORY_DIR = DATA_DIR / "history"

# Known 2026 driver names and their teams (for DOM scraping fallback)
KNOWN_DRIVERS = {
    "Verstappen": "Red Bull", "Russell": "Mercedes", "Antonelli": "Mercedes",
    "Leclerc": "Ferrari", "Hamilton": "Ferrari", "Norris": "McLaren",
    "Piastri": "McLaren", "Hadjar": "Red Bull", "Bearman": "Haas",
    "Ocon": "Haas", "Lindblad": "Racing Bulls", "Lawson": "Racing Bulls",
    "Bortoleto": "Audi", "Hulkenberg": "Audi", "Gasly": "Alpine",
    "Colapinto": "Alpine", "Albon": "Williams", "Sainz": "Williams",
    "Stroll": "Aston Martin", "Alonso": "Aston Martin",
    "Bottas": "Cadillac", "Perez": "Cadillac",
}

KNOWN_CONSTRUCTORS = [
    "Mercedes", "Ferrari", "McLaren", "Red Bull", "Haas",
    "Racing Bulls", "Audi", "Alpine", "Williams", "Aston Martin", "Cadillac",
]


FEEDS_BASE = "https://fantasy.formula1.com/feeds"
SERVICES_BASE = "https://fantasy.formula1.com/services"


async def fetch_feed_data(round_num: int = 2) -> dict | None:
    """Fetch all driver/constructor data from the fantasy.formula1.com feeds.

    The site serves data at /feeds/drivers/{round}_en.json which contains
    both drivers and constructors with current prices.

    Returns dict with 'players' and 'constructors' lists, or None on failure.
    """
    print(f"Fetching feed data for round {round_num}...")
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Try current round first, fall back to round 1
            for rnd in [round_num, 1]:
                url = f"{FEEDS_BASE}/drivers/{rnd}_en.json"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("Data", {}).get("Value", [])
                    if items:
                        print(f"  Got {len(items)} entries from {url}")
                        return _parse_feed_items(items)
                    print(f"  Empty Data.Value from {url}")
                else:
                    print(f"  {resp.status_code} from {url}")
    except Exception as e:
        print(f"  Feed fetch failed: {e}")

    return None


def _parse_feed_items(items: list[dict]) -> dict:
    """Parse the feed's Data.Value list into separate driver and constructor lists.

    Feed fields: PlayerId, Value (price), FUllName, DisplayName, TeamName,
    TeamId, PositionName (DRIVER/CONSTRUCTOR), OverallPpints, OldPlayerValue, etc.
    """
    drivers = []
    constructors = []

    for item in items:
        pos = item.get("PositionName", "").upper()
        full_name = item.get("FUllName", "")
        display_name = item.get("DisplayName", "")
        price = item.get("Value", 0)
        team_name = item.get("TeamName", "")
        player_id = item.get("PlayerId", 0)
        old_price = item.get("OldPlayerValue", 0)
        overall_pts = item.get("OverallPpints", 0)
        gameday_pts = item.get("GamedayPoints", 0)
        selected_pct = item.get("SelectedPercentage", 0)

        # Extract last name for matching with our internal data
        last_name = full_name.split()[-1] if full_name else display_name.split(".")[-1].strip()

        if isinstance(price, str):
            price = float(price)
        if isinstance(old_price, str):
            old_price = float(old_price)
        if isinstance(overall_pts, str):
            overall_pts = float(overall_pts)

        entry = {
            "id": int(player_id) if player_id else 0,
            "display_name": last_name,
            "full_name": full_name,
            "price": price,
            "old_price": old_price,
            "team_name": team_name,
            "position": "Driver" if pos == "DRIVER" else "Constructor",
            "overall_points": overall_pts,
            "gameday_points": gameday_pts,
            "selected_pct": selected_pct,
        }

        if pos == "DRIVER":
            drivers.append(entry)
        else:
            constructors.append({
                "id": int(player_id) if player_id else 0,
                "name": team_name or full_name,
                "price": price,
                "old_price": old_price,
                "overall_points": overall_pts,
                "gameday_points": gameday_pts,
                "selected_pct": selected_pct,
            })

    return {"players": drivers, "constructors": constructors}


async def scrape_authenticated_data(playwright, feed_items: list[dict] | None = None) -> dict:
    """Log in, scrape current team, chips, budget, and ALL player prices.

    If feed_items is provided (from the httpx feed fetch), it's used to resolve
    player IDs from the getteam response to names/prices.
    """
    print("Launching browser...")
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )

    context_opts = {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "bypass_csp": True,
    }
    if STORAGE_STATE_PATH.exists():
        context_opts["storage_state"] = str(STORAGE_STATE_PATH)
        print("  Restored saved session")

    context = await browser.new_context(**context_opts)
    page = await context.new_page()

    # Capture ALL JSON API responses from the page
    captured_responses = {}
    api_urls_seen = []

    async def capture_response(response):
        url = response.url
        if response.status != 200:
            return
        content_type = response.headers.get("content-type", "")
        if "json" not in content_type:
            return
        try:
            body = await response.json()

            # Log all JSON API calls for debugging
            if any(x in url for x in ["formula1", "fantasy", "api", "player", "team"]):
                api_urls_seen.append(url)

            # Capture specific known endpoints
            if "picked_teams" in url:
                captured_responses["picked_teams"] = body
            elif "boosters" in url:
                captured_responses["boosters"] = body

            # Capture feed/API responses that likely contain price data
            if "/feeds/drivers/" in url or "/feeds/constructors/" in url:
                captured_responses[f"feed:{url.split('/')[-1]}"] = body
                print(f"  [Captured] Feed data from: {url[:100]}")
            if "mixapi" in url:
                captured_responses["mixapi"] = body
                print(f"  [Captured] MixAPI data from: {url[:100]}")
            if "getteam" in url:
                captured_responses["getteam"] = body
                print(f"  [Captured] GetTeam data from: {url[:100]}")

            # Broadly capture any response containing player data
            if isinstance(body, dict):
                players = body.get("players", [])
                if isinstance(players, list) and len(players) > 10:
                    captured_responses["all_players"] = body
                    print(f"  [Captured] Player data ({len(players)} entries) from: {url[:100]}")
                teams = body.get("teams", [])
                if isinstance(teams, list) and len(teams) > 5:
                    captured_responses["all_teams"] = body
                    print(f"  [Captured] Team data ({len(teams)} entries) from: {url[:100]}")
            elif isinstance(body, list) and len(body) > 10:
                if body[0] and isinstance(body[0], dict) and "price" in body[0]:
                    captured_responses["all_players_list"] = body
                    print(f"  [Captured] Player list ({len(body)} entries) from: {url[:100]}")
        except Exception:
            pass

    page.on("response", capture_response)

    # Navigate and check login
    print("Navigating to F1 Fantasy...")
    await page.goto(FANTASY_BASE_URL, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    await page.wait_for_timeout(5000)

    debug_path = DATA_DIR / "debug_before_cookies.png"
    await page.screenshot(path=str(debug_path), full_page=False)

    await _dismiss_cookie_banner(page)
    await page.wait_for_timeout(1000)

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

    # Navigate to My Team within the SPA
    print("Loading My Team page...")
    navigated = False

    for sel in ['a:has-text("Manage your team")', 'button:has-text("Manage your team")',
                '[class*="manage"] a', 'a:has-text("Manage")']:
        try:
            el = page.locator(sel).first
            if await el.is_visible(timeout=3000):
                print(f"  Clicking: {sel}")
                await el.click()
                navigated = True
                break
        except Exception:
            continue

    if not navigated:
        try:
            my_team_link = page.locator('a:has-text("My Team")').first
            if await my_team_link.is_visible(timeout=3000):
                print("  Clicking My Team nav link")
                await my_team_link.click()
                navigated = True
        except Exception:
            pass

    # Wait for SPA to load and fire API calls
    await page.wait_for_timeout(10000)
    print(f"  Current URL: {page.url}")

    # Log all API URLs we captured
    if api_urls_seen:
        print(f"\n  API calls detected ({len(api_urls_seen)}):")
        for url in api_urls_seen:
            print(f"    {url[:120]}")

    # Try direct API fetch for team data using authenticated session
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

    # Parse team data — prefer getteam feed over old picked_teams API
    auth_data = {}

    getteam_raw = captured_responses.get("getteam")
    if getteam_raw:
        # Build player ID→info map: prefer pre-fetched feed, fall back to browser-captured
        resolve_items = feed_items or []
        if not resolve_items:
            for key, val in captured_responses.items():
                if not key.startswith("feed:") or not isinstance(val, dict):
                    continue
                items = val.get("Data", {}).get("Value", [])
                if isinstance(items, list) and len(items) > 20:
                    resolve_items = items
                    break
        auth_data["current_team_raw"] = getteam_raw
        auth_data["current_team"] = _parse_getteam(getteam_raw, resolve_items)
        drivers = auth_data["current_team"].get("drivers", [])
        print(f"  Team (from getteam): {', '.join(d['name'] for d in drivers)}")
    else:
        team_raw = captured_responses.get("picked_teams")
        if team_raw:
            auth_data["current_team_raw"] = team_raw
            auth_data["current_team"] = _parse_team(team_raw)
            print(f"  Team: {', '.join(d['name'] for d in auth_data['current_team']['drivers'])}")
        else:
            print("  WARNING: Could not fetch current team, falling back to DOM scraping")
            auth_data["current_team"] = await _scrape_team_from_dom(page)

    # Parse chips
    boosters_raw = captured_responses.get("boosters")
    if boosters_raw:
        auth_data["chips_raw"] = boosters_raw
        auth_data["chips"] = _parse_chips(boosters_raw)
        print(f"  Chips available: {', '.join(auth_data['chips']['available'])}")
    else:
        auth_data["chips"] = {"available": [], "used": {}}

    # Take screenshot
    screenshot_path = DATA_DIR / "my_team_screenshot.png"
    await page.screenshot(path=str(screenshot_path), full_page=True)
    print(f"  Screenshot saved: {screenshot_path}")

    # ========================================
    # SCRAPE ALL DRIVER & CONSTRUCTOR PRICES
    # ========================================
    price_data = await _fetch_all_prices(page, captured_responses)
    auth_data["all_players"] = price_data.get("players", [])
    auth_data["all_constructors"] = price_data.get("constructors", [])

    # Take a final screenshot showing the price list
    final_screenshot = DATA_DIR / "my_team_full.png"
    await page.screenshot(path=str(final_screenshot), full_page=True)
    print(f"  Final screenshot: {final_screenshot}")

    await browser.close()
    return auth_data


async def _fetch_all_prices(page, captured_responses: dict) -> dict:
    """Get all driver and constructor prices using multiple strategies.

    Strategy 1: Use data from captured network responses
    Strategy 2: Fetch API endpoints from the page context (uses browser cookies + DNS)
    Strategy 3: Scrape the player list panel DOM with scrolling
    """
    players = []
    constructors = []

    # --- Strategy 1: Captured network responses ---
    # Check all captured responses for player/team data
    print(f"  Captured response keys: {list(captured_responses.keys())}")

    for key in ["all_players", "all_players_list"]:
        raw = captured_responses.get(key)
        if not raw:
            continue
        p_list = raw.get("players", raw) if isinstance(raw, dict) else raw
        if isinstance(p_list, list) and len(p_list) > 10:
            players = p_list
            break

    # Check feed responses (e.g., feeds/drivers/2_en.json)
    if not players:
        for key, raw in captured_responses.items():
            if not key.startswith("feed:") and key not in ("mixapi", "getteam"):
                continue
            # The feed data might contain driver/constructor prices in various formats
            if isinstance(raw, dict):
                # Try common structures
                for subkey in ["players", "drivers", "data", "items"]:
                    sub = raw.get(subkey, [])
                    if isinstance(sub, list) and len(sub) > 5:
                        if sub[0] and isinstance(sub[0], dict) and ("price" in sub[0] or "Value" in sub[0]):
                            players = sub
                            print(f"    Found player data in {key} under '{subkey}'")
                            break
            elif isinstance(raw, list) and len(raw) > 5:
                if raw[0] and isinstance(raw[0], dict) and ("price" in raw[0] or "Value" in raw[0]):
                    players = raw
                    print(f"    Found player data in {key}")

    raw = captured_responses.get("all_teams")
    if raw:
        t_list = raw.get("teams", raw) if isinstance(raw, dict) else raw
        if isinstance(t_list, list) and len(t_list) > 5:
            constructors = t_list

    # Save and dump captured feed structures for debugging
    debug_feeds_path = DATA_DIR / "debug_feeds.json"
    debug_feeds = {}
    for key in ["mixapi", "getteam"] + [k for k in captured_responses if k.startswith("feed:")]:
        raw = captured_responses.get(key)
        if raw:
            debug_feeds[key] = raw
            if isinstance(raw, dict):
                print(f"    {key} keys: {list(raw.keys())[:15]}")
                # Show structure of 'Data' if present
                data = raw.get("Data")
                if isinstance(data, dict):
                    print(f"      Data keys: {list(data.keys())[:15]}")
                    # Show first item of any list inside Data
                    for dk, dv in data.items():
                        if isinstance(dv, list) and dv:
                            first = dv[0]
                            if isinstance(first, dict):
                                print(f"      Data.{dk}[0] keys: {list(first.keys())[:15]}")
                            break
                elif isinstance(data, list) and data:
                    print(f"      Data: list[{len(data)}]")
                    if isinstance(data[0], dict):
                        print(f"      Data[0] keys: {list(data[0].keys())[:15]}")
            elif isinstance(raw, list):
                print(f"    {key}: list[{len(raw)}], first item keys: {list(raw[0].keys())[:10] if raw and isinstance(raw[0], dict) else 'N/A'}")

    debug_feeds_path.write_text(json.dumps(debug_feeds, indent=2, default=str))
    print(f"    Feed debug data saved to: {debug_feeds_path}")

    if len(players) >= 20 and len(constructors) >= 10:
        print(f"  Prices from network capture: {len(players)} drivers, {len(constructors)} constructors")
        return {"players": players, "constructors": constructors}

    # --- Strategy 2: Fetch feeds via page context ---
    print("  Trying feed fetch via page context...")
    api_data = await page.evaluate("""
        async () => {
            // The site uses feeds on fantasy.formula1.com (no separate API domain)
            const playerUrls = [
                '/feeds/drivers/2_en.json',
                '/feeds/drivers/1_en.json',
            ];
            const teamUrls = [
                '/feeds/constructors/2_en.json',
                '/feeds/constructors/1_en.json',
            ];
            const mixUrl = '/feeds/live/mixapi.json';

            let players = null, teams = null, mix = null;

            for (const url of playerUrls) {
                if (players) break;
                try {
                    const r = await fetch(url, {credentials: 'include'});
                    if (r.ok) players = await r.json();
                } catch {}
            }

            for (const url of teamUrls) {
                if (teams) break;
                try {
                    const r = await fetch(url, {credentials: 'include'});
                    if (r.ok) teams = await r.json();
                } catch {}
            }

            try {
                const r = await fetch(mixUrl, {credentials: 'include'});
                if (r.ok) mix = await r.json();
            } catch {}

            return { players, teams, mix };
        }
    """)

    if api_data:
        if api_data.get("players") and not players:
            p = api_data["players"]
            p_list = p.get("players", p) if isinstance(p, dict) else p
            if isinstance(p_list, list) and len(p_list) > 10:
                players = p_list
                print(f"    Got {len(players)} drivers from page-context fetch")
        if api_data.get("teams") and not constructors:
            t = api_data["teams"]
            t_list = t.get("teams", t) if isinstance(t, dict) else t
            if isinstance(t_list, list) and len(t_list) > 5:
                constructors = t_list
                print(f"    Got {len(constructors)} constructors from page-context fetch")

    if len(players) >= 20 and len(constructors) >= 10:
        return {"players": players, "constructors": constructors}

    # --- Strategy 3: DOM scraping ---
    print("  Falling back to DOM scraping of price list...")
    dom_data = await _scrape_prices_from_dom(page)

    if dom_data.get("drivers") and not players:
        players = dom_data["drivers"]
    if dom_data.get("constructors") and not constructors:
        constructors = dom_data["constructors"]

    print(f"  Final price scrape result: {len(players)} drivers, {len(constructors)} constructors")
    return {"players": players, "constructors": constructors}


async def _scrape_prices_from_dom(page) -> dict:
    """Scrape driver and constructor prices from the My Team page's player list panel.

    The right panel shows a searchable, sortable list of all drivers (and constructors
    via a tab switch). This function scrolls through the list and extracts name+price pairs.
    """
    # Pass known names to JavaScript for matching (as a single object since evaluate takes 1 arg)
    known_data = {"drivers": KNOWN_DRIVERS, "constructors": KNOWN_CONSTRUCTORS}

    result = await page.evaluate("""
        async (knownData) => {
            const DRIVERS = knownData.drivers;  // {name: team, ...}
            const CONSTRUCTORS = knownData.constructors;  // [name, ...]
            const drivers = [];
            const constructors = [];
            const foundDrivers = new Set();
            const foundConstructors = new Set();

            // Find the scrollable price list container
            function findListContainer() {
                // Look for scrollable divs containing price text
                const allDivs = [...document.querySelectorAll('div, section, ul, ol')];
                const candidates = allDivs.filter(el => {
                    const style = window.getComputedStyle(el);
                    const isScrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll')
                        && el.scrollHeight > el.clientHeight + 30;
                    const hasPrice = /\\$\\d+\\.?\\d*M/.test(el.textContent);
                    // Should have multiple children (list items)
                    const hasMultipleItems = el.children.length >= 3;
                    return isScrollable && hasPrice && hasMultipleItems;
                });

                // Prefer the most specific (smallest) container
                candidates.sort((a, b) => {
                    const aSize = a.scrollHeight * a.scrollWidth;
                    const bSize = b.scrollHeight * b.scrollWidth;
                    return aSize - bSize;
                });

                return candidates[0] || null;
            }

            // Extract driver entries from visible text
            function extractDrivers(text) {
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

                for (let i = 0; i < lines.length; i++) {
                    for (const [name, team] of Object.entries(DRIVERS)) {
                        const nameLower = name.toLowerCase();
                        const lineLower = lines[i].toLowerCase();

                        if (!lineLower.includes(nameLower)) continue;
                        if (foundDrivers.has(name)) continue;

                        // Look for price in this line or nearby lines
                        for (let j = Math.max(0, i - 2); j <= Math.min(lines.length - 1, i + 5); j++) {
                            const priceMatch = lines[j].match(/\\$(\\d+\\.?\\d*)M/);
                            if (!priceMatch) continue;

                            const price = parseFloat(priceMatch[1]);
                            if (price < 3 || price > 35) continue;

                            // Make sure we're not in a parent container with multiple prices
                            // by checking the line is short-ish
                            if (lines[j].length > 100) {
                                const allPrices = lines[j].match(/\\$\\d+\\.?\\d*M/g);
                                if (allPrices && allPrices.length > 1) continue;
                            }

                            foundDrivers.add(name);
                            drivers.push({
                                display_name: name,
                                price: price,
                                team_name: team,
                                position: 'Driver'
                            });
                            break;
                        }
                    }
                }
            }

            // Extract constructor entries from visible text
            function extractConstructors(text) {
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

                for (let i = 0; i < lines.length; i++) {
                    for (const name of CONSTRUCTORS) {
                        const nameLower = name.toLowerCase();
                        const lineLower = lines[i].toLowerCase();

                        if (!lineLower.includes(nameLower)) continue;
                        if (foundConstructors.has(name)) continue;

                        // Avoid matching constructor names that appear as driver team labels
                        // Only match if the line is short or the name is the primary content
                        if (lines[i].length > 50) {
                            // Check if name is the primary content (not just a team label)
                            const nameStart = lineLower.indexOf(nameLower);
                            // If name is preceded by a lot of text, it might be a team label
                            if (nameStart > 20) continue;
                        }

                        for (let j = Math.max(0, i - 2); j <= Math.min(lines.length - 1, i + 5); j++) {
                            const priceMatch = lines[j].match(/\\$(\\d+\\.?\\d*)M/);
                            if (!priceMatch) continue;

                            const price = parseFloat(priceMatch[1]);
                            if (price < 3 || price > 35) continue;

                            foundConstructors.add(name);
                            constructors.push({ name, price });
                            break;
                        }
                    }
                }
            }

            // --- Scrape drivers ---
            const container = findListContainer();
            if (container) {
                console.log('[gather] Found scrollable list container, scrolling...');

                // Scroll to top first
                container.scrollTop = 0;
                await new Promise(r => setTimeout(r, 300));

                // Scroll down incrementally, extracting entries at each step
                let prevCount = 0;
                let sameCountStreak = 0;
                for (let step = 0; step < 50; step++) {
                    extractDrivers(container.innerText);

                    if (foundDrivers.size === prevCount) {
                        sameCountStreak++;
                        if (sameCountStreak > 5) break;  // No new entries found
                    } else {
                        sameCountStreak = 0;
                        prevCount = foundDrivers.size;
                    }

                    container.scrollTop += container.clientHeight * 0.6;
                    await new Promise(r => setTimeout(r, 400));
                }

                // Final extraction
                extractDrivers(container.innerText);
                console.log(`[gather] Found ${foundDrivers.size} drivers from scrolling`);
            } else {
                console.log('[gather] No scrollable container found, using full page text');
                extractDrivers(document.body.innerText);
            }

            // --- Switch to Constructors tab and scrape ---
            const tabs = document.querySelectorAll('button, a, [role="tab"], span, div');
            let switchedToConstructors = false;
            for (const tab of tabs) {
                const text = (tab.textContent || '').trim().toLowerCase();
                if (text === 'constructors' || text === 'constructor' || text === 'teams') {
                    // Check it's a clickable tab, not just a label
                    const style = window.getComputedStyle(tab);
                    if (tab.tagName === 'BUTTON' || tab.tagName === 'A' ||
                        tab.getAttribute('role') === 'tab' ||
                        style.cursor === 'pointer') {
                        tab.click();
                        switchedToConstructors = true;
                        console.log('[gather] Switched to Constructors tab');
                        await new Promise(r => setTimeout(r, 2000));
                        break;
                    }
                }
            }

            if (switchedToConstructors) {
                const cContainer = findListContainer();
                if (cContainer) {
                    cContainer.scrollTop = 0;
                    await new Promise(r => setTimeout(r, 300));

                    let prevCount = 0;
                    let sameCountStreak = 0;
                    for (let step = 0; step < 30; step++) {
                        extractConstructors(cContainer.innerText);

                        if (foundConstructors.size === prevCount) {
                            sameCountStreak++;
                            if (sameCountStreak > 5) break;
                        } else {
                            sameCountStreak = 0;
                            prevCount = foundConstructors.size;
                        }

                        cContainer.scrollTop += cContainer.clientHeight * 0.6;
                        await new Promise(r => setTimeout(r, 400));
                    }

                    extractConstructors(cContainer.innerText);
                } else {
                    extractConstructors(document.body.innerText);
                }

                // Switch back to Drivers tab
                for (const tab of tabs) {
                    const text = (tab.textContent || '').trim().toLowerCase();
                    if (text === 'drivers' || text === 'driver') {
                        const style = window.getComputedStyle(tab);
                        if (tab.tagName === 'BUTTON' || tab.tagName === 'A' ||
                            tab.getAttribute('role') === 'tab' ||
                            style.cursor === 'pointer') {
                            tab.click();
                            break;
                        }
                    }
                }
            } else {
                // No constructor tab found, try extracting from full page
                console.log('[gather] No constructors tab found, extracting from page');
                extractConstructors(document.body.innerText);
            }

            return {
                drivers,
                constructors,
                debug: {
                    foundContainer: !!container,
                    switchedToConstructors,
                    driverCount: drivers.length,
                    constructorCount: constructors.length,
                }
            };
        }
    """, known_data)

    debug = result.get("debug", {})
    print(f"    DOM scrape: container={debug.get('foundContainer')}, "
          f"constructorTab={debug.get('switchedToConstructors')}, "
          f"drivers={debug.get('driverCount')}, constructors={debug.get('constructorCount')}")

    return result


def _parse_getteam(data: dict, feed_items: list[dict]) -> dict:
    """Parse the /services/.../getteam response using feed data for player details.

    getteam structure: {Data: {Value: {mdid, userTeam: [{teambal, playerid: [{id, iscaptain, ...}], ...}]}}}
    """
    value = data.get("Data", {}).get("Value", {})
    teams = value.get("userTeam", [])
    if not teams:
        return {"drivers": [], "constructors": [], "budget_remaining": 0, "free_transfers": 2, "drs_boost": None}

    team = teams[0]
    bank = team.get("teambal", 0)
    player_entries = team.get("playerid", [])

    # Build ID→info map from feed (strip whitespace — feed IDs may have padding)
    id_map = {}
    for item in feed_items:
        pid = str(item.get("PlayerId", "")).strip()
        if pid:
            id_map[pid] = item

    drivers = []
    constructors = []
    drs_boost = None

    for entry in player_entries:
        pid = str(entry.get("id", "")).strip()
        info = id_map.get(pid, {})
        pos = info.get("PositionName", "").upper()
        full_name = info.get("FUllName", "")
        last_name = full_name.split()[-1] if full_name else f"ID:{pid}"
        price = info.get("Value", 0)
        team_name = info.get("TeamName", "")

        if isinstance(price, str):
            price = float(price)

        # For constructors, FUllName has the name (TeamName is empty for constructors)
        player = {
            "name": full_name if pos == "CONSTRUCTOR" else last_name,
            "id": int(pid) if pid.isdigit() else 0,
            "price": price,
            "team": team_name or full_name,
        }

        if pos == "CONSTRUCTOR":
            constructors.append(player)
        else:
            drivers.append(player)

        if entry.get("iscaptain"):
            drs_boost = player["name"]

    return {
        "drivers": drivers,
        "constructors": constructors,
        "budget_remaining": float(bank),
        "free_transfers": 2,  # Game rule: 2 free per race
        "drs_boost": drs_boost,
        "total_value": sum(d.get("price", 0) for d in drivers + constructors),
    }


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


async def _dismiss_cookie_banner(page):
    """Dismiss cookie consent banners/overlays using JS + selector fallback."""
    dismissed = await page.evaluate("""
        () => {
            // OneTrust (very common on F1 sites)
            const otBtn = document.getElementById('onetrust-accept-btn-handler');
            if (otBtn) { otBtn.click(); return 'onetrust'; }

            // CMP accept button patterns
            const selectors = [
                'button[id*="accept"]',
                'button[class*="accept"]',
                'button[data-testid*="accept"]',
                'a[id*="accept"]',
                '.cmp-button_button.cmp-intro_acceptAll',
                '#didomi-notice-agree-button',
                '.qc-cmp2-summary-buttons button:first-child',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.offsetParent !== null) {
                    el.click();
                    return 'selector:' + sel;
                }
            }

            // Generic: find any visible button with "accept" in its text
            const buttons = document.querySelectorAll('button, a[role="button"]');
            for (const btn of buttons) {
                const text = (btn.textContent || '').toLowerCase().trim();
                if ((text.includes('accept') || text.includes('agree') || text === 'ok') &&
                    btn.offsetParent !== null) {
                    btn.click();
                    return 'text:' + text;
                }
            }

            // Nuclear option: remove common overlay containers
            const overlays = document.querySelectorAll(
                '#onetrust-consent-sdk, .onetrust-pc-dark-filter, ' +
                '[class*="cookie-banner"], [class*="cookie-consent"], ' +
                '[class*="CookieBanner"], [id*="cookie-banner"], ' +
                '#didomi-popup, .qc-cmp2-container, ' +
                '[class*="consent-banner"], [class*="ConsentBanner"]'
            );
            if (overlays.length > 0) {
                overlays.forEach(el => el.remove());
                document.body.style.overflow = '';
                document.documentElement.style.overflow = '';
                return 'removed:' + overlays.length;
            }
            return null;
        }
    """)

    if dismissed:
        print(f"  Dismissed cookie banner ({dismissed})")
        await page.wait_for_timeout(1000)
        return

    # Selector-based fallback
    cookie_selectors = [
        'button:has-text("Accept All")',
        'button:has-text("Accept all")',
        'button:has-text("Accept All Cookies")',
        'button:has-text("AGREE")',
        'button:has-text("I Accept")',
    ]
    for sel in cookie_selectors:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                print(f"  Dismissed cookie banner (selector)")
                await page.wait_for_timeout(1000)
                return
        except Exception:
            continue

    # Try within iframes
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            dismissed = await frame.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button, a[role="button"]');
                    for (const btn of buttons) {
                        const text = (btn.textContent || '').toLowerCase().trim();
                        if ((text.includes('accept') || text.includes('agree')) &&
                            btn.offsetParent !== null) {
                            btn.click();
                            return 'iframe:' + text;
                        }
                    }
                    return null;
                }
            """)
            if dismissed:
                print(f"  Dismissed cookie banner ({dismissed})")
                await page.wait_for_timeout(1000)
                return
        except Exception:
            continue


async def _dismiss_overlays(page):
    """Remove loading spinners, modal overlays, and other blocking elements."""
    await page.evaluate("""
        () => {
            const selectors = [
                '[class*="loading"]', '[class*="spinner"]', '[class*="loader"]',
                '[class*="overlay"]:not([class*="cookie"]):not([class*="consent"])',
                '.modal-backdrop', '[class*="backdrop"]',
                '[class*="Loading"]', '[class*="Spinner"]',
            ];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.position === 'absolute') {
                        if (style.zIndex > 100 || el.querySelector('[class*="spin"]')) {
                            el.remove();
                        }
                    }
                });
            }
            document.body.style.overflow = '';
            document.body.style.pointerEvents = '';
            document.documentElement.style.overflow = '';
        }
    """)
    await page.wait_for_timeout(500)


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
    """Perform the login flow with automated + manual fallback."""
    if not F1_EMAIL or not F1_PASSWORD:
        print("ERROR: F1_FANTASY_EMAIL and F1_FANTASY_PASSWORD must be set in .env")
        return False

    await _dismiss_cookie_banner(page)

    # Listen for popup windows (F1 uses popup-based auth)
    popup_page = None

    async def handle_popup(popup):
        nonlocal popup_page
        popup_page = popup
        print(f"  Popup opened: {popup.url}")
        try:
            await popup.wait_for_load_state("networkidle")
        except Exception:
            pass

    page.context.on("page", handle_popup)

    # Click Sign In / Log In button
    clicked = False
    for btn_text in ["Sign In", "Log In", "Login", "Sign in"]:
        btn = page.locator(f"text={btn_text}").first
        try:
            if await btn.is_visible(timeout=3000):
                print(f"  Clicking '{btn_text}'...")
                await btn.click()
                await page.wait_for_timeout(3000)
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        for sel in ['svg[class*="user"]', 'button svg', '[class*="user-icon"]',
                    '[data-testid="user-icon"]', '[class*="sign-in"]', '[class*="login"]',
                    'a[href*="login"]', 'a[href*="sign-in"]', 'a[href*="account"]',
                    'a[href*="account.formula1.com"]']:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=2000):
                    print(f"  Clicking login element: {sel}")
                    await el.click()
                    await page.wait_for_timeout(3000)
                    clicked = True
                    break
            except Exception:
                continue

    debug_path = DATA_DIR / "debug_after_signin_click.png"
    await page.screenshot(path=str(debug_path), full_page=False)
    print(f"  Current URL: {page.url}")
    if popup_page:
        popup_debug = DATA_DIR / "debug_popup.png"
        try:
            await popup_page.screenshot(path=str(popup_debug), full_page=False)
            print(f"  Popup URL: {popup_page.url}")
        except Exception:
            print(f"  Popup URL: {popup_page.url} (couldn't screenshot)")

    login_target = popup_page if popup_page else page

    await _dismiss_cookie_banner(login_target)
    await _dismiss_overlays(login_target)

    # Try automated login
    login_done = False
    for attempt in range(2):
        try:
            target = login_target

            await _dismiss_overlays(target)

            email_selectors = [
                'input[placeholder*="username" i]',
                'input[placeholder*="email" i]',
                'input[type="email"]',
                'input[name="email"]',
                'input[name="Login"]',
                'input[autocomplete="email"]',
                'input[autocomplete="username"]',
            ]
            email_input = None
            for sel in email_selectors:
                try:
                    loc = target.locator(sel).first
                    if await loc.is_visible(timeout=3000):
                        email_input = loc
                        print(f"  Found email input: {sel}")
                        break
                except Exception:
                    continue

            if not email_input:
                if attempt == 0:
                    await login_target.wait_for_timeout(5000)
                    await _dismiss_cookie_banner(login_target)
                    await _dismiss_overlays(login_target)
                    continue
                break

            print("  Waiting for form to be ready...")
            await login_target.wait_for_timeout(3000)
            await _dismiss_overlays(login_target)

            print("  Filling credentials (keystroke mode)...")
            await email_input.click()
            await login_target.wait_for_timeout(300)
            await email_input.press("Control+a")
            await email_input.press("Backspace")
            await email_input.type(F1_EMAIL, delay=50)
            await login_target.wait_for_timeout(500)

            pw_input = None
            for sel in ['input[placeholder*="password" i]', 'input[type="password"]',
                       'input[name="password"]']:
                try:
                    loc = target.locator(sel).first
                    if await loc.is_visible(timeout=3000):
                        pw_input = loc
                        break
                except Exception:
                    continue

            if pw_input:
                await pw_input.click()
                await login_target.wait_for_timeout(300)
                await pw_input.press("Control+a")
                await pw_input.press("Backspace")
                await pw_input.type(F1_PASSWORD, delay=50)
                await login_target.wait_for_timeout(1000)

            print("  Submitting login form (Enter key)...")
            if pw_input:
                await pw_input.press("Enter")
            else:
                await email_input.press("Enter")

            await login_target.wait_for_timeout(1000)
            for btn_sel in ['button:has-text("SIGN IN")', 'button:has-text("Sign In")',
                           'button[type="submit"]']:
                try:
                    btn = target.locator(btn_sel).first
                    if await btn.is_visible(timeout=1000):
                        print(f"  Also clicking submit button: {btn_sel}")
                        await btn.click(force=True)
                        break
                except Exception:
                    continue

            print("  Waiting for login redirect...")
            try:
                for _ in range(60):
                    await page.wait_for_timeout(500)
                    current = page.url
                    if current.startswith("https://fantasy.formula1.com"):
                        login_done = True
                        print("  Redirected to fantasy site!")
                        await page.wait_for_load_state("networkidle")
                        break
            except Exception:
                pass

            if not login_done:
                debug_path = DATA_DIR / "debug_after_login_submit.png"
                try:
                    await page.screenshot(path=str(debug_path), full_page=False)
                    print(f"  Login redirect timed out. URL: {page.url}")
                except Exception:
                    print(f"  Login redirect timed out. URL: {page.url}")

            break
        except Exception as e:
            print(f"  Login attempt {attempt + 1} error: {e}")
            if attempt == 0:
                try:
                    await login_target.wait_for_timeout(3000)
                except Exception:
                    pass
                continue
            break

    if login_done:
        await page.wait_for_timeout(5000)
        await _dismiss_cookie_banner(page)
        return await _check_logged_in(page)

    # Manual fallback
    print("\n" + "=" * 50)
    print("MANUAL LOGIN REQUIRED")
    print("Please log in to F1 Fantasy in the browser window.")
    print("The script will continue automatically once logged in.")
    print("=" * 50)

    for _ in range(36):
        try:
            await page.wait_for_timeout(5000)
        except Exception:
            await asyncio.sleep(5)
        try:
            if await _check_logged_in(page):
                print("  Login detected!")
                return True
            if "my-team" in page.url or "pick-team" in page.url:
                return True
        except Exception:
            continue

    print("  Login timed out after 3 minutes")
    return False


def save_history(state: dict):
    """Save a timestamped copy to history for trend tracking."""
    HISTORY_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = HISTORY_DIR / f"state_{ts}.json"
    history_file.write_text(json.dumps(state, indent=2))
    print(f"History saved: {history_file}")


async def main():
    # 1. Fetch price data from the fantasy.formula1.com feeds (preferred, no auth needed)
    feed_data = await fetch_feed_data(round_num=2)

    # 2. Authenticated data via browser (team, chips, budget)
    # Pass feed items so getteam can resolve player IDs to names
    raw_feed_items = []
    if feed_data:
        # Reconstruct the raw items from our parsed data for ID resolution
        # Actually, let's just re-fetch the raw feed for the ID map
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(f"{FEEDS_BASE}/drivers/2_en.json")
                if resp.status_code == 200:
                    raw_feed_items = resp.json().get("Data", {}).get("Value", [])
        except Exception:
            pass

    async with async_playwright() as p:
        auth_data = await scrape_authenticated_data(p, feed_items=raw_feed_items)

    # Use browser-scraped prices as fallback
    browser_players = auth_data.pop("all_players", [])
    browser_constructors = auth_data.pop("all_constructors", [])

    # Decide which price source to use: feed API > browser-scraped
    if feed_data and feed_data.get("players"):
        players = feed_data["players"]
        constructors_list = feed_data["constructors"]
        source = "feed_api"
    elif browser_players:
        players = browser_players
        constructors_list = browser_constructors
        source = "browser"
    else:
        players = []
        constructors_list = []
        source = "none"

    print(f"\n  Price source: {source} ({len(players)} drivers, {len(constructors_list)} constructors)")

    scoring_history = {}

    # 4. Assemble complete state
    state = {
        "gathered_at": datetime.now().isoformat(),
        "source": source,
        "current_round": None,  # Will be set by analyze.py from circuit data
        "drivers": players,
        "constructors": constructors_list,
        "my_team": auth_data.get("current_team", {}),
        "chips": auth_data.get("chips", {}),
        "scoring_history": scoring_history,
        "raw_api": {
            "picked_teams": auth_data.get("current_team_raw"),
            "boosters": auth_data.get("chips_raw"),
        },
    }

    # 6. Save
    OUTPUT_PATH.write_text(json.dumps(state, indent=2))
    print(f"\nState saved to: {OUTPUT_PATH}")
    save_history(state)

    # 7. Print summary
    print("\n" + "=" * 60)
    print("CURRENT STATE SUMMARY")
    print(f"Price source: {source}")
    print("=" * 60)

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

    if players:
        print(f"\nDriver prices ({len(players)}):")
        for p in sorted(players, key=lambda x: x.get("price", 0), reverse=True):
            name = p.get("display_name", p.get("last_name", "?"))
            price = p.get("price", 0)
            team_name = p.get("team_name", p.get("team", {}).get("name", "?"))
            print(f"  {name:25s} {team_name:20s} ${price:.1f}M")
    else:
        print("\n  WARNING: No driver prices available")

    if constructors_list:
        print(f"\nConstructor prices ({len(constructors_list)}):")
        for t in sorted(constructors_list, key=lambda x: x.get("price", 0), reverse=True):
            name = t.get("name", t.get("short_name", "?"))
            price = t.get("price", 0)
            print(f"  {name:25s} ${price:.1f}M")
    else:
        print("\n  WARNING: No constructor prices available")

    print(f"\nFull data cached at: {OUTPUT_PATH}")
    print("Now run: python scripts/analyze.py")


if __name__ == "__main__":
    asyncio.run(main())
