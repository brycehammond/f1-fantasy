"""Main orchestrator — login, analyze, optimize, and update F1 Fantasy team."""

import asyncio
import argparse

from playwright.async_api import async_playwright

from src.config import BUDGET_CAP, SEASON_YEAR
from src.auth import create_browser_context, login
from src.api import get_players, get_constructors, get_season_info
from src.scraper import get_current_team, get_chip_status
from src.optimizer import Asset, find_optimal_team, plan_transfers
from src.projections import project_driver, project_constructor, rank_by_value, Projection
from src.circuits import get_circuit
from src.chips import recommend_chip, SPRINT_ROUNDS
from src.actions import make_transfers, set_drs_boost, activate_chip


async def run(dry_run: bool = False, ppm_weight: float = 0.3):
    print("=" * 60)
    print(f"F1 Fantasy Automation — {SEASON_YEAR} Season")
    print("=" * 60)

    # Step 1: Fetch public data (no auth needed)
    print("\n  Fetching public data...")
    players_data, constructors_data, season_data = await asyncio.gather(
        get_players(),
        get_constructors(),
        get_season_info(),
    )
    print(f"  Found {len(players_data)} drivers, {len(constructors_data)} constructors")

    # Determine current round
    current_round = _get_current_round(season_data)
    total_rounds = _get_total_rounds(season_data)
    is_sprint = current_round in SPRINT_ROUNDS
    circuit = get_circuit(current_round)
    circuit_name = circuit.name if circuit else "Unknown"
    print(f"  Round {current_round}/{total_rounds}: {circuit_name} {'(Sprint)' if is_sprint else ''}")

    # Build asset lists with advanced projections
    drivers = _build_driver_assets(players_data, current_round)
    constructors = _build_constructor_assets(constructors_data, current_round)

    # Show projections ranked by raw points
    print(f"\n  Top projected drivers (Round {current_round}):")
    print(f"  {'Name':25s} {'Price':>7s} {'Proj':>6s} {'PPM':>5s} {'Conf':>5s}")
    print(f"  {'-'*25} {'-'*7} {'-'*6} {'-'*5} {'-'*5}")
    for d in sorted(drivers, key=lambda x: x.projected_points, reverse=True)[:12]:
        print(f"  {d.name:25s} ${d.price:5.1f}M {d.projected_points:5.1f}  {d.ppm:4.2f}  "
              f"{d.projection.confidence:.0%}" if d.projection else "")

    # Show value picks (PPM ranking)
    print(f"\n  Best value picks (PPM):")
    print(f"  {'Name':25s} {'Price':>7s} {'Proj':>6s} {'PPM':>5s}")
    print(f"  {'-'*25} {'-'*7} {'-'*6} {'-'*5}")
    value_drivers = sorted(drivers, key=lambda x: x.ppm, reverse=True)
    for d in value_drivers[:8]:
        print(f"  {d.name:25s} ${d.price:5.1f}M {d.projected_points:5.1f}  {d.ppm:4.2f}")

    print(f"\n  Top projected constructors:")
    print(f"  {'Name':25s} {'Price':>7s} {'Proj':>6s} {'PPM':>5s}")
    print(f"  {'-'*25} {'-'*7} {'-'*6} {'-'*5}")
    for c in sorted(constructors, key=lambda x: x.projected_points, reverse=True)[:6]:
        print(f"  {c.name:25s} ${c.price:5.1f}M {c.projected_points:5.1f}  {c.ppm:4.2f}")

    # Step 2: Find optimal team with PPM blending
    print(f"\n  Computing optimal team (PPM weight: {ppm_weight:.0%})...")
    optimal = find_optimal_team(drivers, constructors, budget=BUDGET_CAP, ppm_weight=ppm_weight)
    print(f"  Optimal team (${optimal.total_cost:.1f}M / ${BUDGET_CAP:.0f}M budget):")
    print(f"  Drivers:")
    for d in optimal.drivers:
        print(f"    {d.name:25s} ${d.price:5.1f}M  proj: {d.projected_points:5.1f}  PPM: {d.ppm:.2f}")
    print(f"  Constructors:")
    for c in optimal.constructors:
        print(f"    {c.name:25s} ${c.price:5.1f}M  proj: {c.projected_points:5.1f}  PPM: {c.ppm:.2f}")
    print(f"  DRS Boost: {optimal.drs_boost.name}")
    print(f"  Total projected: {optimal.total_projected_points:.1f} pts")

    # Show projection breakdown for DRS boost pick
    if optimal.drs_boost and optimal.drs_boost.projection:
        bp = optimal.drs_boost.projection.breakdown
        print(f"\n  DRS boost reasoning ({optimal.drs_boost.name}):")
        for signal, (value, weight) in sorted(bp.items(), key=lambda x: x[1][1], reverse=True):
            print(f"    {signal:20s}: {value:6.1f} pts (weight: {weight:.2f})")

    # Step 3: Browser session for authenticated operations
    print("\n  Launching browser...")
    async with async_playwright() as p:
        context = await create_browser_context(p)
        page = await context.new_page()

        # Login
        print("  Logging in...")
        logged_in = await login(page)
        if not logged_in:
            print("  Login failed. Please check credentials in .env")
            await context.close()
            return

        # Get current team
        print("\n  Reading current team...")
        current_team = await get_current_team(page)
        print(f"  Current drivers: {', '.join(d.get('name', '?') for d in current_team.drivers)}")
        print(f"  Current constructors: {', '.join(c.get('name', '?') for c in current_team.constructors)}")
        print(f"  Budget remaining: ${current_team.budget_remaining:.1f}M")
        print(f"  Free transfers: {current_team.free_transfers}")

        # Get chip status
        chip_status = await get_chip_status(page)
        print(f"  Available chips: {', '.join(chip_status.available) or 'none'}")

        # Plan transfers
        current_driver_assets = _match_assets(current_team.drivers, drivers)
        current_constructor_assets = _match_assets(current_team.constructors, constructors)

        optimal = plan_transfers(
            current_driver_assets,
            current_constructor_assets,
            optimal,
            free_transfers=current_team.free_transfers,
        )

        if optimal.transfers_needed:
            print(f"\n  Planned transfers ({len(optimal.transfers_needed)}):")
            for out_asset, in_asset in optimal.transfers_needed:
                delta = in_asset.projected_points - out_asset.projected_points
                print(f"  OUT: {out_asset.name:20s} (${out_asset.price:5.1f}M, {out_asset.projected_points:5.1f} pts)")
                print(f"   IN: {in_asset.name:20s} (${in_asset.price:5.1f}M, {in_asset.projected_points:5.1f} pts, "
                      f"delta: {delta:+.1f})")
            if optimal.transfers_cost:
                print(f"  Transfer penalty: {optimal.transfers_cost} points")
        else:
            print("\n  Current team is already optimal — no transfers needed")

        # Chip recommendation
        projected_gain = sum(
            a_in.projected_points - a_out.projected_points
            for a_out, a_in in optimal.transfers_needed
        )
        chip_rec = recommend_chip(
            current_round=current_round,
            total_rounds=total_rounds,
            available_chips=chip_status.available,
            transfers_needed=len(optimal.transfers_needed),
            free_transfers=current_team.free_transfers,
            projected_gain_from_transfers=projected_gain,
            is_sprint_weekend=is_sprint,
        )
        if chip_rec.chip:
            print(f"\n  Chip recommendation: {chip_rec.chip} (confidence: {chip_rec.confidence:.0%})")
            print(f"   Reason: {chip_rec.reason}")
        else:
            print(f"\n  No chip recommended: {chip_rec.reason}")

        # Execute actions
        if dry_run:
            print("\n  DRY RUN — no changes made")
            _print_summary(optimal, chip_rec)
        else:
            print("\n  Executing changes...")

            if chip_rec.chip and chip_rec.confidence >= 0.6:
                print(f"  Activating chip: {chip_rec.chip}")
                await activate_chip(page, chip_rec.chip)

            if optimal.transfers_needed:
                transfer_pairs = [
                    ({"name": out_a.name}, {"name": in_a.name})
                    for out_a, in_a in optimal.transfers_needed
                ]
                await make_transfers(page, transfer_pairs)

            if optimal.drs_boost:
                await set_drs_boost(page, optimal.drs_boost.name)

            print("\n  All changes applied!")

        await context.close()


def _get_current_round(season_data: dict) -> int:
    """Extract current round number from season data."""
    try:
        periods = season_data.get("game_periods", [])
        for period in periods:
            if period.get("is_current"):
                return period.get("game_period_id", 1)
        for period in periods:
            if not period.get("is_finished"):
                return period.get("game_period_id", 1)
    except Exception:
        pass
    return 2  # Default to round 2 (post-Australia)


def _get_total_rounds(season_data: dict) -> int:
    try:
        return len(season_data.get("game_periods", []))
    except Exception:
        return 24


def _build_driver_assets(players_data: list[dict], target_round: int) -> list[Asset]:
    """Convert raw player data to Asset objects with advanced projections."""
    assets = []
    for p in players_data:
        name = p.get("display_name", p.get("last_name", "Unknown"))
        price = p.get("price", 10.0)
        team = p.get("team_name", p.get("team", {}).get("name", ""))

        proj = project_driver(name, price, team, target_round)

        asset = Asset(
            id=p.get("id", 0),
            name=name,
            price=price,
            projected_points=proj.raw_points,
            team=team,
            asset_type="driver",
            ppm=proj.ppm,
            projection=proj,
        )
        assets.append(asset)
    return assets


def _build_constructor_assets(constructors_data: list[dict], target_round: int) -> list[Asset]:
    """Convert raw constructor data to Asset objects with advanced projections."""
    assets = []
    for t in constructors_data:
        name = t.get("name", t.get("short_name", "Unknown"))
        price = t.get("price", 10.0)

        proj = project_constructor(name, price, target_round)

        asset = Asset(
            id=t.get("id", 0),
            name=name,
            price=price,
            projected_points=proj.raw_points,
            team=name,
            asset_type="constructor",
            ppm=proj.ppm,
            projection=proj,
        )
        assets.append(asset)
    return assets


def _match_assets(team_entries: list[dict], all_assets: list[Asset]) -> list[Asset]:
    """Match current team entries (by name) to full Asset objects."""
    matched = []
    for entry in team_entries:
        name = entry.get("name", "")
        for asset in all_assets:
            if asset.name and name and (
                asset.name.lower() in name.lower() or name.lower() in asset.name.lower()
            ):
                matched.append(asset)
                break
    return matched


def _print_summary(optimal, chip_rec):
    print("\n" + "=" * 60)
    print("SUMMARY (dry run)")
    print("=" * 60)
    print(f"Drivers:      {', '.join(d.name for d in optimal.drivers)}")
    print(f"Constructors: {', '.join(c.name for c in optimal.constructors)}")
    print(f"DRS Boost:    {optimal.drs_boost.name if optimal.drs_boost else 'N/A'}")
    print(f"Transfers:    {len(optimal.transfers_needed)}")
    if optimal.transfers_cost:
        print(f"Penalty:      {optimal.transfers_cost} points")
    if chip_rec.chip:
        print(f"Chip:         {chip_rec.chip} ({chip_rec.reason})")
    print(f"Projected:    {optimal.total_projected_points:.1f} pts")
    print(f"Budget used:  ${optimal.total_cost:.1f}M / $100.0M")


def main():
    parser = argparse.ArgumentParser(description="F1 Fantasy Team Automation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze and recommend without making changes",
    )
    parser.add_argument(
        "--ppm-weight",
        type=float,
        default=0.3,
        help="PPM vs raw points blend (0.0=pure points, 1.0=pure value). Default: 0.3",
    )
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run, ppm_weight=args.ppm_weight))


if __name__ == "__main__":
    main()
