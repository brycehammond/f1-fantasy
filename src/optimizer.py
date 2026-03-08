"""Team selection optimizer — budget-constrained selection of 5 drivers + 2 constructors.

Two modes:
1. Unconstrained — best possible team from scratch (for wildcard/limitless or initial team)
2. Transfer-constrained — best team reachable with N transfers from current team
"""

from dataclasses import dataclass
from itertools import combinations

from src.projections import Projection


EXTRA_TRANSFER_PENALTY = 10  # points lost per transfer beyond free allowance


@dataclass
class Asset:
    id: int
    name: str
    price: float
    projected_points: float
    team: str
    asset_type: str  # "driver" or "constructor"
    ppm: float = 0.0                      # Points-per-million
    projection: Projection | None = None  # Full projection details


@dataclass
class OptimalTeam:
    drivers: list[Asset]
    constructors: list[Asset]
    total_cost: float
    total_projected_points: float
    drs_boost: Asset | None            # Driver to DRS boost
    transfers_needed: list[tuple[Asset, Asset]]  # (out, in) pairs
    transfers_cost: int                # penalty points for extra transfers
    net_gain: float = 0.0              # projected points gained minus transfer penalties


def find_optimal_team(
    drivers: list[Asset],
    constructors: list[Asset],
    budget: float = 100.0,
    max_drivers: int = 5,
    max_constructors: int = 2,
    ppm_weight: float = 0.0,
) -> OptimalTeam:
    """Find the highest-scoring team within budget (unconstrained by transfers).

    Use this for wildcard/limitless chips or building an initial team.
    For normal race weeks, use find_best_transfers() instead.
    """
    best_score = -float("inf")
    best_drivers = []
    best_constructors = []

    for driver_combo in combinations(drivers, max_drivers):
        driver_cost = sum(d.price for d in driver_combo)
        if driver_cost > budget:
            continue

        driver_points = sum(d.projected_points for d in driver_combo)
        driver_ppm = sum(d.ppm for d in driver_combo)
        remaining_budget = budget - driver_cost

        for constructor_combo in combinations(constructors, max_constructors):
            constructor_cost = sum(c.price for c in constructor_combo)
            if constructor_cost > remaining_budget:
                continue

            raw_total = driver_points + sum(c.projected_points for c in constructor_combo)
            ppm_total = driver_ppm + sum(c.ppm for c in constructor_combo)
            score = raw_total * (1 - ppm_weight) + ppm_total * ppm_weight * 10

            if score > best_score:
                best_score = score
                best_drivers = list(driver_combo)
                best_constructors = list(constructor_combo)

    total_cost = sum(d.price for d in best_drivers) + sum(c.price for c in best_constructors)
    total_points = sum(d.projected_points for d in best_drivers) + sum(
        c.projected_points for c in best_constructors
    )
    drs_driver = max(best_drivers, key=lambda d: d.projected_points) if best_drivers else None

    return OptimalTeam(
        drivers=best_drivers,
        constructors=best_constructors,
        total_cost=total_cost,
        total_projected_points=total_points,
        drs_boost=drs_driver,
        transfers_needed=[],
        transfers_cost=0,
        net_gain=0.0,
    )


def find_best_transfers(
    current_drivers: list[Asset],
    current_constructors: list[Asset],
    all_drivers: list[Asset],
    all_constructors: list[Asset],
    budget: float = 100.0,
    free_transfers: int = 2,
    max_transfers: int | None = None,
    ppm_weight: float = 0.0,
) -> OptimalTeam:
    """Find the best team reachable within the transfer limit.

    Evaluates every possible combination of 0..max_transfers swaps and picks
    the one with the highest net score (projected points minus transfer penalties).

    Args:
        current_drivers: Your current 5 drivers.
        current_constructors: Your current 2 constructors.
        all_drivers: All available drivers (including current ones).
        all_constructors: All available constructors (including current ones).
        budget: Total team budget cap.
        free_transfers: Number of free transfers available.
        max_transfers: Cap on total transfers to consider. Defaults to free_transfers
                       (no penalty moves). Set higher to allow penalty transfers when
                       the gain outweighs the cost.
        ppm_weight: PPM vs raw points blend (0=raw, 1=pure PPM).
    """
    if max_transfers is None:
        max_transfers = free_transfers + 2  # Consider up to 2 penalty transfers

    current_driver_ids = {d.id for d in current_drivers}
    current_constructor_ids = {c.id for c in current_constructors}
    current_points = (
        sum(d.projected_points for d in current_drivers)
        + sum(c.projected_points for c in current_constructors)
    )
    current_cost = (
        sum(d.price for d in current_drivers)
        + sum(c.price for c in current_constructors)
    )

    # Available replacements (not already on team)
    available_drivers = [d for d in all_drivers if d.id not in current_driver_ids]
    available_constructors = [c for c in all_constructors if c.id not in current_constructor_ids]

    # Build list of all possible individual swaps with their value
    driver_swaps = []  # (out, in, point_delta, cost_delta)
    for out_d in current_drivers:
        for in_d in available_drivers:
            delta_pts = in_d.projected_points - out_d.projected_points
            delta_ppm = in_d.ppm - out_d.ppm
            delta_cost = in_d.price - out_d.price
            score = delta_pts * (1 - ppm_weight) + delta_ppm * ppm_weight * 10
            driver_swaps.append((out_d, in_d, delta_pts, delta_cost, score))

    constructor_swaps = []
    for out_c in current_constructors:
        for in_c in available_constructors:
            delta_pts = in_c.projected_points - out_c.projected_points
            delta_cost = in_c.price - out_c.price
            delta_ppm = in_c.ppm - out_c.ppm
            score = delta_pts * (1 - ppm_weight) + delta_ppm * ppm_weight * 10
            constructor_swaps.append((out_c, in_c, delta_pts, delta_cost, score))

    all_swaps = driver_swaps + constructor_swaps

    best_result = None
    best_net_score = 0.0  # Baseline: make no transfers at all

    # Try every combination of 1..max_transfers swaps
    cap = min(max_transfers, len(all_swaps))
    for n_swaps in range(1, cap + 1):
        penalty = max(0, n_swaps - free_transfers) * EXTRA_TRANSFER_PENALTY

        for swap_combo in combinations(all_swaps, n_swaps):
            # Check no player appears twice (can't swap out same player twice)
            out_ids = [s[0].id for s in swap_combo]
            in_ids = [s[1].id for s in swap_combo]
            if len(set(out_ids)) != len(out_ids):
                continue  # Same player swapped out twice
            if len(set(in_ids)) != len(in_ids):
                continue  # Same player swapped in twice
            # Can't swap in someone already on team (who isn't being swapped out)
            remaining_ids = current_driver_ids | current_constructor_ids
            remaining_ids -= set(out_ids)
            if any(i in remaining_ids for i in in_ids):
                continue

            total_cost_delta = sum(s[3] for s in swap_combo)
            if current_cost + total_cost_delta > budget:
                continue  # Over budget

            total_score_delta = sum(s[4] for s in swap_combo)
            net_score = total_score_delta - penalty

            if net_score > best_net_score:
                best_net_score = net_score
                best_result = (swap_combo, penalty, net_score)

    # Build the result
    if best_result is None:
        # No transfers improve the team — keep current
        drs_driver = max(current_drivers, key=lambda d: d.projected_points) if current_drivers else None
        return OptimalTeam(
            drivers=list(current_drivers),
            constructors=list(current_constructors),
            total_cost=current_cost,
            total_projected_points=current_points,
            drs_boost=drs_driver,
            transfers_needed=[],
            transfers_cost=0,
            net_gain=0.0,
        )

    swap_combo, penalty, net_score = best_result
    transfers = [(s[0], s[1]) for s in swap_combo]

    # Build new team
    out_ids = {s[0].id for s in swap_combo}
    in_assets = {s[1].id: s[1] for s in swap_combo}

    new_drivers = [d for d in current_drivers if d.id not in out_ids]
    new_constructors = [c for c in current_constructors if c.id not in out_ids]
    for asset in in_assets.values():
        if asset.asset_type == "driver":
            new_drivers.append(asset)
        else:
            new_constructors.append(asset)

    total_cost = sum(d.price for d in new_drivers) + sum(c.price for c in new_constructors)
    total_points = sum(d.projected_points for d in new_drivers) + sum(
        c.projected_points for c in new_constructors
    )
    drs_driver = max(new_drivers, key=lambda d: d.projected_points) if new_drivers else None

    return OptimalTeam(
        drivers=new_drivers,
        constructors=new_constructors,
        total_cost=total_cost,
        total_projected_points=total_points,
        drs_boost=drs_driver,
        transfers_needed=transfers,
        transfers_cost=-penalty,
        net_gain=net_score,
    )


def plan_transfers(
    current_drivers: list[Asset],
    current_constructors: list[Asset],
    optimal: OptimalTeam,
    free_transfers: int = 2,
) -> OptimalTeam:
    """Diff an unconstrained optimal team against current and calculate penalties.

    Use this with find_optimal_team() for wildcard/limitless scenarios.
    For normal weeks, use find_best_transfers() which already handles this.
    """
    current_driver_ids = {d.id for d in current_drivers}
    optimal_driver_ids = {d.id for d in optimal.drivers}
    current_constructor_ids = {c.id for c in current_constructors}
    optimal_constructor_ids = {c.id for c in optimal.constructors}

    drivers_out = [d for d in current_drivers if d.id not in optimal_driver_ids]
    drivers_in = [d for d in optimal.drivers if d.id not in current_driver_ids]
    constructors_out = [c for c in current_constructors if c.id not in optimal_constructor_ids]
    constructors_in = [c for c in optimal.constructors if c.id not in current_constructor_ids]

    transfers = list(zip(drivers_out, drivers_in)) + list(zip(constructors_out, constructors_in))
    extra_transfers = max(0, len(transfers) - free_transfers)

    optimal.transfers_needed = transfers
    optimal.transfers_cost = extra_transfers * -10

    return optimal
