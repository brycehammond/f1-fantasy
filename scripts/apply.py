#!/usr/bin/env python3
"""
Apply script — shows both lineup recommendations and applies the chosen one.

Displays:
1. Algorithm's lineup (from data/algorithm_lineup.json) with reasoning
2. Claude's lineup (from data/claude_lineup.json) with reasoning
3. Side-by-side comparison
4. Optionally applies the chosen lineup via Playwright

Usage:
    python scripts/apply.py                    # Show both, prompt to apply
    python scripts/apply.py --show             # Just show comparison, don't apply
    python scripts/apply.py --apply algorithm  # Apply the algorithm's pick
    python scripts/apply.py --apply claude     # Apply Claude's pick
    python scripts/apply.py --apply FILE       # Apply a specific lineup file
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from src.config import DATA_DIR, FANTASY_BASE_URL, STATE_DIR

STORAGE_STATE_PATH = STATE_DIR / "auth_state.json"
ALGO_PATH = DATA_DIR / "algorithm_lineup.json"
CLAUDE_PATH = DATA_DIR / "claude_lineup.json"

CHIP_DISPLAY_NAMES = {
    "wildcard": "Wildcard",
    "limitless": "Limitless",
    "extra_drs": "Extra DRS",
    "autopilot": "Autopilot",
    "no_negative": "No Negative",
    "final_fix": "Final Fix",
}


def load_lineup(path: Path) -> dict | None:
    if path.exists():
        return json.loads(path.read_text())
    return None


def print_lineup(lineup: dict, label: str):
    """Print a lineup recommendation with full reasoning."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    if lineup.get("target_round"):
        circuit = lineup.get("circuit", "?")
        print(f"  Round {lineup['target_round']} — {circuit}")

    # Reasoning
    reasoning = lineup.get("reasoning", "")
    if reasoning:
        print(f"\n  WHY THIS LINEUP:")
        for line in reasoning.split("\n"):
            print(f"    {line}")

    # Team
    team = lineup.get("team", {})
    drivers = team.get("drivers", [])
    constructors = team.get("constructors", [])

    print(f"\n  DRIVERS:")
    for d in drivers:
        why = d.get("reasoning", "")
        proj = d.get("projected_points", "")
        proj_str = f"  proj: {proj}" if proj else ""
        ppm = d.get("ppm", "")
        ppm_str = f"  PPM: {ppm}" if ppm else ""
        print(f"    {d['name']:25s} ${d.get('price', 0):5.1f}M{proj_str}{ppm_str}")
        if why:
            print(f"      -> {why}")

    print(f"\n  CONSTRUCTORS:")
    for c in constructors:
        why = c.get("reasoning", "")
        proj = c.get("projected_points", "")
        proj_str = f"  proj: {proj}" if proj else ""
        print(f"    {c['name']:25s} ${c.get('price', 0):5.1f}M{proj_str}")
        if why:
            print(f"      -> {why}")

    # DRS
    drs = lineup.get("drs_boost")
    drs_why = lineup.get("drs_reasoning", "")
    if drs:
        print(f"\n  DRS BOOST: {drs}")
        if drs_why:
            print(f"      -> {drs_why}")

    # Chip
    chip = lineup.get("chip")
    chip_why = lineup.get("chip_reasoning", "")
    if chip:
        print(f"\n  CHIP: {CHIP_DISPLAY_NAMES.get(chip, chip)}")
        if chip_why:
            print(f"      -> {chip_why}")

    # Transfers
    transfers = lineup.get("transfers", [])
    if transfers:
        penalty = lineup.get("transfer_penalty", 0)
        print(f"\n  TRANSFERS ({len(transfers)}):")
        for t in transfers:
            delta = t.get("delta", "")
            delta_str = f" ({delta:+.1f})" if delta else ""
            why = t.get("reasoning", "")
            print(f"    OUT: {t['out']}")
            print(f"     IN: {t['in']}{delta_str}")
            if why:
                print(f"      -> {why}")
        if penalty:
            print(f"    Penalty: {penalty} points")
    else:
        print(f"\n  NO TRANSFERS")

    # Total
    cost = lineup.get("total_cost")
    proj_total = lineup.get("projected_points")
    if cost:
        print(f"\n  Budget: ${cost:.1f}M / $100.0M")
    if proj_total:
        print(f"  Projected: {proj_total:.1f} pts")


def print_comparison(algo: dict | None, claude: dict | None):
    """Side-by-side diff of the two lineups."""
    if not algo or not claude:
        return

    print(f"\n{'=' * 60}")
    print(f"  SIDE-BY-SIDE COMPARISON")
    print(f"{'=' * 60}")

    algo_drivers = {d["name"] for d in algo.get("team", {}).get("drivers", [])}
    claude_drivers = {d["name"] for d in claude.get("team", {}).get("drivers", [])}
    algo_constructors = {c["name"] for c in algo.get("team", {}).get("constructors", [])}
    claude_constructors = {c["name"] for c in claude.get("team", {}).get("constructors", [])}

    shared_d = algo_drivers & claude_drivers
    algo_only_d = algo_drivers - claude_drivers
    claude_only_d = claude_drivers - algo_drivers
    shared_c = algo_constructors & claude_constructors
    algo_only_c = algo_constructors - claude_constructors
    claude_only_c = claude_constructors - algo_constructors

    if shared_d:
        print(f"\n  Both agree on drivers:       {', '.join(sorted(shared_d))}")
    if algo_only_d:
        print(f"  Algorithm only (drivers):    {', '.join(sorted(algo_only_d))}")
    if claude_only_d:
        print(f"  Claude only (drivers):       {', '.join(sorted(claude_only_d))}")
    if shared_c:
        print(f"  Both agree on constructors:  {', '.join(sorted(shared_c))}")
    if algo_only_c:
        print(f"  Algorithm only (constr.):    {', '.join(sorted(algo_only_c))}")
    if claude_only_c:
        print(f"  Claude only (constr.):       {', '.join(sorted(claude_only_c))}")

    print(f"\n  {'':25s} {'Algorithm':>12s} {'Claude':>12s}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")

    algo_cost = algo.get("total_cost", 0)
    claude_cost = claude.get("total_cost", 0)
    print(f"  {'Budget used':25s} ${algo_cost:>9.1f}M ${claude_cost:>9.1f}M")

    algo_proj = algo.get("projected_points", 0)
    claude_proj = claude.get("projected_points", "N/A")
    print(f"  {'Projected points':25s} {str(algo_proj):>12s} {str(claude_proj):>12s}")

    algo_drs = algo.get("drs_boost", "—")
    claude_drs = claude.get("drs_boost", "—")
    drs_match = " *" if algo_drs == claude_drs else ""
    print(f"  {'DRS Boost':25s} {algo_drs:>12s} {claude_drs:>12s}{drs_match}")

    algo_chip = algo.get("chip") or "none"
    claude_chip = claude.get("chip") or "none"
    chip_match = " *" if algo_chip == claude_chip else ""
    print(f"  {'Chip':25s} {algo_chip:>12s} {claude_chip:>12s}{chip_match}")

    algo_tx = len(algo.get("transfers", []))
    claude_tx = len(claude.get("transfers", []))
    print(f"  {'Transfers':25s} {algo_tx:>12d} {claude_tx:>12d}")


async def apply_lineup_to_site(lineup: dict):
    """Execute a lineup via Playwright."""
    transfers = lineup.get("transfers", [])
    drs_boost = lineup.get("drs_boost")
    chip = lineup.get("chip")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        if not STORAGE_STATE_PATH.exists():
            print("ERROR: No saved session. Run gather.py first.")
            await browser.close()
            return

        context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))
        page = await context.new_page()

        await page.goto(f"{FANTASY_BASE_URL}my-team", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Verify login
        logged_in = False
        for sel in ["text=My Team", '[data-testid="user-menu"]', 'a[href*="my-team"]']:
            try:
                if await page.locator(sel).first.is_visible(timeout=3000):
                    logged_in = True
                    break
            except Exception:
                continue

        if not logged_in:
            print("ERROR: Session expired. Run gather.py again.")
            await browser.close()
            return

        # Chip first
        if chip:
            print(f"Activating chip: {CHIP_DISPLAY_NAMES.get(chip, chip)}")
            await _activate_chip(page, chip)

        # Transfers
        if transfers:
            print(f"Making {len(transfers)} transfers...")
            await _make_transfers(page, transfers)

        # DRS
        if drs_boost:
            print(f"Setting DRS boost: {drs_boost}")
            await _set_drs_boost(page, drs_boost)

        screenshot = DATA_DIR / "post_apply_screenshot.png"
        await page.screenshot(path=str(screenshot), full_page=True)
        print(f"Confirmation screenshot: {screenshot}")

        await context.storage_state(path=str(STORAGE_STATE_PATH))
        await browser.close()

    print("Done!")


async def _make_transfers(page, transfers):
    edit_btn = page.locator(
        'button:has-text("Transfers"), button:has-text("Edit Team"), '
        'a:has-text("Transfers"), a:has-text("Edit")'
    ).first
    try:
        await edit_btn.click()
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  Warning: could not find edit button: {e}")

    for t in transfers:
        out_name = t["out"]
        in_name = t["in"]
        print(f"  {out_name} -> {in_name}")
        try:
            await page.locator(f'text="{out_name}"').first.click()
            await page.wait_for_timeout(1500)

            search = page.locator('input[placeholder*="Search"], input[type="search"]').first
            if await search.is_visible(timeout=5000):
                await search.fill(in_name)
                await page.wait_for_timeout(2000)

            await page.locator(f'text="{in_name}"').first.click()
            await page.wait_for_timeout(1500)
        except Exception as e:
            print(f"    Warning: transfer failed: {e}")

    confirm = page.locator('button:has-text("Confirm"), button:has-text("Save")').first
    try:
        if await confirm.is_visible(timeout=5000):
            await confirm.click()
            await page.wait_for_timeout(3000)
            print("  Transfers confirmed!")
    except Exception:
        print("  Warning: could not confirm")


async def _set_drs_boost(page, driver_name):
    drs = page.locator('[class*="drs"], [class*="DRS"], text="DRS"').first
    try:
        if await drs.is_visible(timeout=5000):
            await drs.click()
            await page.wait_for_timeout(1000)
    except Exception:
        pass
    try:
        await page.locator(f'text="{driver_name}"').first.click()
        await page.wait_for_timeout(1000)
        confirm = page.locator('button:has-text("Confirm"), button:has-text("Save")').first
        if await confirm.is_visible(timeout=5000):
            await confirm.click()
            print(f"  DRS boost set on {driver_name}")
    except Exception as e:
        print(f"  Warning: DRS boost failed: {e}")


async def _activate_chip(page, chip_name):
    btn = page.locator('button:has-text("Chips"), a:has-text("Chips"), [class*="chip"]').first
    try:
        if await btn.is_visible(timeout=5000):
            await btn.click()
            await page.wait_for_timeout(1500)
    except Exception:
        pass

    display = CHIP_DISPLAY_NAMES.get(chip_name, chip_name)
    try:
        await page.locator(f'text="{display}"').first.click()
        await page.wait_for_timeout(1000)
        activate = page.locator('button:has-text("Activate"), button:has-text("Use"), button:has-text("Confirm")').first
        if await activate.is_visible(timeout=5000):
            await activate.click()
            await page.wait_for_timeout(2000)
            print(f"  Chip '{display}' activated!")
    except Exception as e:
        print(f"  Warning: chip activation failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Compare and apply F1 Fantasy lineup recommendations")
    parser.add_argument("--show", action="store_true", help="Show comparison only, don't apply")
    parser.add_argument("--apply", type=str, help="Apply a lineup: 'algorithm', 'claude', or path to JSON")
    args = parser.parse_args()

    algo = load_lineup(ALGO_PATH)
    claude = load_lineup(CLAUDE_PATH)

    if algo:
        print_lineup(algo, "ALGORITHM RECOMMENDATION")
    else:
        print(f"\nNo algorithm lineup found ({ALGO_PATH}). Run: python scripts/analyze.py")

    if claude:
        print_lineup(claude, "CLAUDE RECOMMENDATION")
    else:
        print(f"\nNo Claude lineup found ({CLAUDE_PATH}).")
        print("Ask Claude to read data/state.json, research the race, and write data/claude_lineup.json")

    if algo and claude:
        print_comparison(algo, claude)

    if args.show:
        return

    if args.apply:
        if args.apply == "algorithm" and algo:
            lineup = algo
        elif args.apply == "claude" and claude:
            lineup = claude
        else:
            path = Path(args.apply)
            lineup = load_lineup(path)
            if not lineup:
                print(f"ERROR: Could not load {path}")
                return

        print(f"\n--- Applying lineup ---")
        asyncio.run(apply_lineup_to_site(lineup))


if __name__ == "__main__":
    main()
