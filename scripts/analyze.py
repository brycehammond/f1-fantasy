#!/usr/bin/env python3
"""
Analyze script — runs the predictive algorithm on gathered state.

Produces two recommendations:
1. Transfer-constrained — best team reachable within your free transfers
2. Unconstrained — the dream team if you had a wildcard

Outputs to data/algorithm_lineup.json for Claude to review.

Usage:
    python scripts/analyze.py
    python scripts/analyze.py --ppm-weight 0.5   # Favor value picks more
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import BUDGET_CAP, DATA_DIR
from src.projections import project_driver, project_constructor
from src.optimizer import Asset, find_optimal_team, find_best_transfers, plan_transfers
from src.chips import recommend_chip, SPRINT_ROUNDS
from src.circuits import get_circuit

STATE_PATH = DATA_DIR / "state.json"
OUTPUT_PATH = DATA_DIR / "algorithm_lineup.json"


def load_state() -> dict:
    if not STATE_PATH.exists():
        print(f"ERROR: {STATE_PATH} not found. Run scripts/gather.py first.")
        sys.exit(1)
    return json.loads(STATE_PATH.read_text())


def determine_round(state: dict) -> int:
    cr = state.get("current_round")
    if cr:
        return cr.get("game_period_id", 2)
    # Fall back to mdid from raw API (matchday ID)
    raw = state.get("raw_api", {})
    picked = raw.get("picked_teams", {})
    data_val = picked.get("Data", {}).get("Value", {})
    mdid = data_val.get("mdid")
    if mdid:
        return mdid
    return 2


def build_assets(state: dict, target_round: int) -> tuple[list[Asset], list[Asset]]:
    drivers = []
    for p in state.get("drivers", []):
        name = p.get("display_name", p.get("last_name", "Unknown"))
        price = p.get("price", 10.0)
        team = p.get("team_name", p.get("team", {}).get("name", ""))

        proj = project_driver(name, price, team, target_round)
        drivers.append(Asset(
            id=p.get("id", 0), name=name, price=price,
            projected_points=proj.raw_points, team=team,
            asset_type="driver", ppm=proj.ppm, projection=proj,
        ))

    constructors = []
    for t in state.get("constructors", []):
        name = t.get("name", t.get("short_name", "Unknown"))
        price = t.get("price", 10.0)

        proj = project_constructor(name, price, target_round)
        constructors.append(Asset(
            id=t.get("id", 0), name=name, price=price,
            projected_points=proj.raw_points, team=name,
            asset_type="constructor", ppm=proj.ppm, projection=proj,
        ))

    return drivers, constructors


def match_current_team(my_team: dict, all_drivers: list[Asset], all_constructors: list[Asset]):
    def find(name, assets):
        name_lower = name.lower()
        for a in assets:
            if a.name.lower() in name_lower or name_lower in a.name.lower():
                return a
        return None

    current_drivers = []
    for d in my_team.get("drivers", []):
        match = find(d.get("name", ""), all_drivers)
        if match:
            current_drivers.append(match)

    current_constructors = []
    for c in my_team.get("constructors", []):
        match = find(c.get("name", ""), all_constructors)
        if match:
            current_constructors.append(match)

    return current_drivers, current_constructors


def run(ppm_weight: float = 0.3):
    state = load_state()
    target_round = determine_round(state)
    circuit = get_circuit(target_round)
    is_sprint = target_round in SPRINT_ROUNDS

    print("=" * 60)
    print("ALGORITHM ANALYSIS")
    print("=" * 60)
    print(f"Target: Round {target_round} — {circuit.name if circuit else '?'} "
          f"{'(Sprint)' if is_sprint else ''}")
    print(f"PPM weight: {ppm_weight:.0%}")

    drivers, constructors = build_assets(state, target_round)

    # Show all projections
    print(f"\n--- Driver Projections ---")
    print(f"{'Name':25s} {'Team':18s} {'Price':>7s} {'Proj':>6s} {'PPM':>5s}")
    for d in sorted(drivers, key=lambda x: x.projected_points, reverse=True):
        print(f"{d.name:25s} {d.team:18s} ${d.price:5.1f}M {d.projected_points:5.1f}  {d.ppm:.2f}")

    print(f"\n--- Constructor Projections ---")
    print(f"{'Name':25s} {'Price':>7s} {'Proj':>6s} {'PPM':>5s}")
    for c in sorted(constructors, key=lambda x: x.projected_points, reverse=True):
        print(f"{c.name:25s} ${c.price:5.1f}M {c.projected_points:5.1f}  {c.ppm:.2f}")

    my_team = state.get("my_team", {})
    free_transfers = my_team.get("free_transfers", 2)
    chips = state.get("chips", {})
    available_chips = chips.get("available", [])

    has_current_team = bool(my_team.get("drivers"))

    # =============================================
    # MODE 1: Transfer-constrained (the real recommendation)
    # =============================================
    constrained = None
    if has_current_team:
        current_drivers, current_constructors = match_current_team(my_team, drivers, constructors)

        print(f"\n{'=' * 60}")
        print(f"RECOMMENDED LINEUP (within {free_transfers} free transfers)")
        print(f"{'=' * 60}")

        current_pts = (
            sum(d.projected_points for d in current_drivers)
            + sum(c.projected_points for c in current_constructors)
        )
        print(f"Current team projected: {current_pts:.1f} pts")

        constrained = find_best_transfers(
            current_drivers, current_constructors,
            drivers, constructors,
            budget=BUDGET_CAP,
            free_transfers=free_transfers,
            ppm_weight=ppm_weight,
        )

        print(f"\nBest reachable team (${constrained.total_cost:.1f}M):")
        print("Drivers:")
        for d in sorted(constrained.drivers, key=lambda x: x.projected_points, reverse=True):
            marker = " (new)" if d.id not in {x.id for x in current_drivers} else ""
            print(f"  {d.name:25s} ${d.price:5.1f}M  proj: {d.projected_points:5.1f}  PPM: {d.ppm:.2f}{marker}")
        print("Constructors:")
        for c in sorted(constrained.constructors, key=lambda x: x.projected_points, reverse=True):
            marker = " (new)" if c.id not in {x.id for x in current_constructors} else ""
            print(f"  {c.name:25s} ${c.price:5.1f}M  proj: {c.projected_points:5.1f}  PPM: {c.ppm:.2f}{marker}")
        print(f"DRS Boost: {constrained.drs_boost.name if constrained.drs_boost else 'N/A'}")
        print(f"Projected: {constrained.total_projected_points:.1f} pts (net gain: {constrained.net_gain:+.1f})")

        if constrained.transfers_needed:
            print(f"\nTransfers ({len(constrained.transfers_needed)}, {free_transfers} free):")
            for out_a, in_a in constrained.transfers_needed:
                delta = in_a.projected_points - out_a.projected_points
                print(f"  OUT: {out_a.name:25s} (${out_a.price:5.1f}M, {out_a.projected_points:5.1f} pts)")
                print(f"   IN: {in_a.name:25s} (${in_a.price:5.1f}M, {in_a.projected_points:5.1f} pts, {delta:+.1f})")
            if constrained.transfers_cost:
                print(f"  Penalty: {constrained.transfers_cost} points")
                print(f"  Net gain after penalty: {constrained.net_gain:+.1f} pts")
        else:
            print("\nNo beneficial transfers found — keep current team")
    else:
        print("\nNo current team found in state — showing unconstrained only")

    # =============================================
    # MODE 2: Unconstrained (dream team / wildcard reference)
    # =============================================
    print(f"\n{'=' * 60}")
    print("DREAM TEAM (unconstrained / wildcard)")
    print(f"{'=' * 60}")

    unconstrained = find_optimal_team(drivers, constructors, budget=BUDGET_CAP, ppm_weight=ppm_weight)
    print(f"Best possible team (${unconstrained.total_cost:.1f}M):")
    print("Drivers:")
    for d in sorted(unconstrained.drivers, key=lambda x: x.projected_points, reverse=True):
        print(f"  {d.name:25s} ${d.price:5.1f}M  proj: {d.projected_points:5.1f}  PPM: {d.ppm:.2f}")
    print("Constructors:")
    for c in sorted(unconstrained.constructors, key=lambda x: x.projected_points, reverse=True):
        print(f"  {c.name:25s} ${c.price:5.1f}M  proj: {c.projected_points:5.1f}  PPM: {c.ppm:.2f}")
    print(f"DRS Boost: {unconstrained.drs_boost.name if unconstrained.drs_boost else 'N/A'}")
    print(f"Projected: {unconstrained.total_projected_points:.1f} pts")

    if has_current_team:
        unconstrained = plan_transfers(current_drivers, current_constructors, unconstrained, free_transfers)
        gap = unconstrained.total_projected_points - constrained.total_projected_points
        n_transfers = len(unconstrained.transfers_needed)
        print(f"\nWould require {n_transfers} transfers ({unconstrained.transfers_cost} penalty)")
        print(f"Gap vs constrained: {gap:+.1f} pts (before penalty)")

    # Chip recommendation (consider whether wildcard is worth it)
    use_lineup = constrained if constrained else unconstrained
    projected_gain = sum(
        i.projected_points - o.projected_points for o, i in use_lineup.transfers_needed
    ) if use_lineup.transfers_needed else 0

    chip_rec = recommend_chip(
        current_round=target_round,
        total_rounds=24,
        available_chips=available_chips,
        transfers_needed=len(use_lineup.transfers_needed),
        free_transfers=free_transfers,
        projected_gain_from_transfers=projected_gain,
        is_sprint_weekend=is_sprint,
    )

    # Also check: if the unconstrained team is much better, suggest wildcard
    if has_current_team and "wildcard" in available_chips:
        gap = unconstrained.total_projected_points - constrained.total_projected_points
        if gap > 15 and len(unconstrained.transfers_needed) > free_transfers + 1:
            chip_rec_override = f"Wildcard strongly recommended: dream team is {gap:.1f} pts better but needs {len(unconstrained.transfers_needed)} transfers"
            print(f"\n--- Chip Recommendation ---")
            print(f"  WILDCARD (gap: {gap:+.1f} pts)")
            print(f"  {chip_rec_override}")
            chip_name = "wildcard"
            chip_reason = chip_rec_override
        else:
            chip_name = chip_rec.chip if chip_rec.confidence >= 0.6 else None
            chip_reason = chip_rec.reason
            if chip_rec.chip:
                print(f"\n--- Chip Recommendation ---")
                print(f"  {chip_rec.chip} (confidence: {chip_rec.confidence:.0%})")
                print(f"  Reason: {chip_rec.reason}")
            else:
                print(f"\nNo chip recommended: {chip_rec.reason}")
    else:
        chip_name = chip_rec.chip if chip_rec.confidence >= 0.6 else None
        chip_reason = chip_rec.reason
        if chip_rec.chip:
            print(f"\n--- Chip Recommendation ---")
            print(f"  {chip_rec.chip} (confidence: {chip_rec.confidence:.0%})")
            print(f"  Reason: {chip_rec.reason}")
        else:
            print(f"\nNo chip recommended: {chip_rec.reason}")

    # Write the lineup file (constrained is the primary recommendation)
    primary = constrained if constrained else unconstrained

    lineup = {
        "source": "algorithm",
        "target_round": target_round,
        "circuit": circuit.name if circuit else None,
        "ppm_weight": ppm_weight,
        "free_transfers": free_transfers,
        "team": {
            "drivers": [
                {"name": d.name, "price": d.price, "projected_points": round(d.projected_points, 1), "ppm": round(d.ppm, 2), "team": d.team}
                for d in sorted(primary.drivers, key=lambda x: x.projected_points, reverse=True)
            ],
            "constructors": [
                {"name": c.name, "price": c.price, "projected_points": round(c.projected_points, 1), "ppm": round(c.ppm, 2)}
                for c in sorted(primary.constructors, key=lambda x: x.projected_points, reverse=True)
            ],
        },
        "drs_boost": primary.drs_boost.name if primary.drs_boost else None,
        "chip": chip_name,
        "chip_reasoning": chip_reason,
        "transfers": [
            {"out": o.name, "in": i.name, "delta": round(i.projected_points - o.projected_points, 1)}
            for o, i in primary.transfers_needed
        ],
        "transfer_penalty": primary.transfers_cost,
        "net_gain": round(primary.net_gain, 1),
        "total_cost": round(primary.total_cost, 1),
        "projected_points": round(primary.total_projected_points, 1),
        "dream_team": {
            "drivers": [d.name for d in sorted(unconstrained.drivers, key=lambda x: x.projected_points, reverse=True)],
            "constructors": [c.name for c in sorted(unconstrained.constructors, key=lambda x: x.projected_points, reverse=True)],
            "projected_points": round(unconstrained.total_projected_points, 1),
            "transfers_needed": len(unconstrained.transfers_needed) if has_current_team else 0,
        },
    }

    OUTPUT_PATH.write_text(json.dumps(lineup, indent=2))
    print(f"\nAlgorithm lineup saved to: {OUTPUT_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Run algorithm analysis on gathered state")
    parser.add_argument("--ppm-weight", type=float, default=0.3, help="PPM blend weight (0=raw, 1=pure value)")
    args = parser.parse_args()
    run(ppm_weight=args.ppm_weight)


if __name__ == "__main__":
    main()
