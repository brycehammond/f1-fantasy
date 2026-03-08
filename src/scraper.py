"""Browser-based scraping for authenticated data (current team, chips, budget)."""

from dataclasses import dataclass, field
from playwright.async_api import Page

from src.config import FANTASY_BASE_URL


@dataclass
class CurrentTeam:
    drivers: list[dict] = field(default_factory=list)       # [{name, id, price, points}]
    constructors: list[dict] = field(default_factory=list)   # [{name, id, price, points}]
    budget_remaining: float = 0.0
    total_value: float = 0.0
    free_transfers: int = 2
    drs_boost_driver: str | None = None


@dataclass
class ChipStatus:
    available: list[str] = field(default_factory=list)
    used: dict = field(default_factory=dict)  # {chip_name: round_used}


async def get_current_team(page: Page) -> CurrentTeam:
    """Scrape the current team from the My Team page."""
    team = CurrentTeam()

    await page.goto(f"{FANTASY_BASE_URL}my-team", wait_until="networkidle")
    await page.wait_for_timeout(3000)

    # Intercept API calls to get team data directly
    # The React app makes API calls we can capture
    team_data = await _intercept_team_api(page)
    if team_data:
        return team_data

    # Fallback: scrape from DOM
    # Driver cards typically have player name, price, and points
    driver_cards = page.locator('[class*="driver"], [class*="player"], [data-type="driver"]')
    count = await driver_cards.count()
    for i in range(count):
        card = driver_cards.nth(i)
        name = await card.locator('[class*="name"]').first.text_content()
        if name:
            team.drivers.append({"name": name.strip()})

    constructor_cards = page.locator('[class*="constructor"], [data-type="constructor"]')
    count = await constructor_cards.count()
    for i in range(count):
        card = constructor_cards.nth(i)
        name = await card.locator('[class*="name"]').first.text_content()
        if name:
            team.constructors.append({"name": name.strip()})

    # Budget
    budget_el = page.locator('[class*="budget"], [class*="remaining"]').first
    try:
        budget_text = await budget_el.text_content()
        if budget_text:
            team.budget_remaining = float(budget_text.replace("$", "").replace("M", "").strip())
    except Exception:
        pass

    return team


async def get_chip_status(page: Page) -> ChipStatus:
    """Scrape which chips are available vs used."""
    status = ChipStatus()

    # Navigate to chips/boosters section if not already there
    chips_link = page.locator('a:has-text("Chips"), a:has-text("Boosters")').first
    try:
        if await chips_link.is_visible(timeout=3000):
            await chips_link.click()
            await page.wait_for_load_state("networkidle")
    except Exception:
        pass

    # Also try intercepting the boosters API call
    booster_data = await _intercept_boosters_api(page)
    if booster_data:
        return booster_data

    return status


async def _intercept_team_api(page: Page) -> CurrentTeam | None:
    """Try to capture the picked_teams API response from network traffic."""
    team = CurrentTeam()
    captured = {}

    def handle_response(response):
        if "picked_teams" in response.url and response.status == 200:
            captured["data"] = True

    page.on("response", handle_response)

    # Reload to trigger API calls
    await page.reload(wait_until="networkidle")
    await page.wait_for_timeout(3000)

    # Use page.evaluate to fetch from the API with the page's cookies
    try:
        result = await page.evaluate("""
            async () => {
                const resp = await fetch('/api/picked_teams?my_current_picked_teams=true&my_next_picked_teams=true');
                if (resp.ok) return await resp.json();
                return null;
            }
        """)
        if result:
            _parse_picked_teams(result, team)
            return team
    except Exception:
        pass

    return None


async def _intercept_boosters_api(page: Page) -> ChipStatus | None:
    """Try to capture boosters API response."""
    try:
        result = await page.evaluate("""
            async () => {
                const resp = await fetch('/api/boosters');
                if (resp.ok) return await resp.json();
                return null;
            }
        """)
        if result:
            status = ChipStatus()
            for booster in result.get("boosters", []):
                name = booster.get("name", "").lower().replace(" ", "_")
                if booster.get("is_used"):
                    status.used[name] = booster.get("game_period_id")
                else:
                    status.available.append(name)
            return status
    except Exception:
        pass
    return None


def _parse_picked_teams(data: dict, team: CurrentTeam):
    """Parse the picked_teams API response into our CurrentTeam model."""
    picks = data if isinstance(data, list) else data.get("picked_teams", [data])
    if not picks:
        return

    current = picks[0]
    for player in current.get("picked_players", []):
        entry = {
            "name": player.get("player", {}).get("display_name", ""),
            "id": player.get("player", {}).get("id"),
            "price": player.get("player", {}).get("price"),
            "points": player.get("score"),
        }
        if player.get("player", {}).get("position") == "Driver":
            team.drivers.append(entry)
        else:
            team.constructors.append(entry)

        if player.get("is_drs_boosted"):
            team.drs_boost_driver = entry["name"]

    team.budget_remaining = current.get("budget_remaining", 0.0)
    team.free_transfers = current.get("free_transfers", 2)
