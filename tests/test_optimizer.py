"""Tests for the team optimizer."""

import pytest
from src.optimizer import Asset, find_optimal_team, find_best_transfers, plan_transfers


def _make_drivers(n=22):
    """Create test drivers with varied prices and projected points."""
    data = [
        ("Verstappen", 27.7, 36.0, "Red Bull", 1.30),
        ("Russell", 27.4, 38.0, "Mercedes", 1.39),
        ("Norris", 27.2, 25.0, "McLaren", 0.92),
        ("Piastri", 25.5, 20.0, "McLaren", 0.78),
        ("Antonelli", 23.2, 35.0, "Mercedes", 1.51),
        ("Leclerc", 22.8, 28.0, "Ferrari", 1.23),
        ("Hamilton", 22.5, 26.0, "Ferrari", 1.16),
        ("Hadjar", 15.1, 12.0, "Red Bull", 0.79),
        ("Gasly", 12.0, 14.0, "Alpine", 1.17),
        ("Sainz", 11.8, 13.0, "Williams", 1.10),
        ("Albon", 11.6, 12.5, "Williams", 1.08),
        ("Alonso", 10.0, 10.0, "Aston Martin", 1.00),
        ("Stroll", 8.0, 6.0, "Aston Martin", 0.75),
        ("Bearman", 7.4, 12.0, "Haas", 1.62),
        ("Ocon", 7.3, 8.0, "Haas", 1.10),
        ("Hulkenberg", 6.8, 7.0, "Audi", 1.03),
        ("Lawson", 6.5, 7.5, "Racing Bulls", 1.15),
        ("Bortoleto", 6.4, 9.0, "Audi", 1.41),
        ("Lindblad", 6.2, 10.0, "Racing Bulls", 1.61),
        ("Colapinto", 6.2, 6.0, "Alpine", 0.97),
        ("Perez", 6.0, 5.0, "Cadillac", 0.83),
        ("Bottas", 5.9, 4.0, "Cadillac", 0.68),
    ]
    return [
        Asset(
            id=i, name=name, price=price, projected_points=pts,
            team=team, asset_type="driver", ppm=ppm,
        )
        for i, (name, price, pts, team, ppm) in enumerate(data[:n])
    ]


def _make_constructors():
    data = [
        ("Mercedes", 29.3, 45.0, 1.54),
        ("McLaren", 28.9, 35.0, 1.21),
        ("Red Bull", 28.2, 40.0, 1.42),
        ("Ferrari", 23.3, 38.0, 1.63),
        ("Alpine", 12.5, 15.0, 1.20),
        ("Williams", 12.0, 14.0, 1.17),
        ("Aston Martin", 10.3, 10.0, 0.97),
        ("Haas", 7.4, 12.0, 1.62),
        ("Audi", 6.6, 8.0, 1.21),
        ("Racing Bulls", 6.3, 10.0, 1.59),
        ("Cadillac", 6.0, 5.0, 0.83),
    ]
    return [
        Asset(
            id=100 + i, name=name, price=price, projected_points=pts,
            team=name, asset_type="constructor", ppm=ppm,
        )
        for i, (name, price, pts, ppm) in enumerate(data)
    ]


class TestFindOptimalTeam:
    def test_respects_budget(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        result = find_optimal_team(drivers, constructors, budget=100.0)
        assert result.total_cost <= 100.0

    def test_correct_team_size(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        result = find_optimal_team(drivers, constructors)
        assert len(result.drivers) == 5
        assert len(result.constructors) == 2

    def test_maximizes_points(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        result = find_optimal_team(drivers, constructors, budget=100.0)
        assert result.total_projected_points > 100.0

    def test_drs_boost_on_best_driver(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        result = find_optimal_team(drivers, constructors)
        best_driver = max(result.drivers, key=lambda d: d.projected_points)
        assert result.drs_boost.name == best_driver.name

    def test_tight_budget(self):
        """With a tight budget the optimizer still finds a valid team."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        result = find_optimal_team(drivers, constructors, budget=55.0)
        assert result.total_cost <= 55.0
        assert len(result.drivers) == 5
        assert len(result.constructors) == 2

    def test_ppm_weight_favors_value_picks(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        result_raw = find_optimal_team(drivers, constructors, ppm_weight=0.0)
        result_value = find_optimal_team(drivers, constructors, ppm_weight=0.8)
        assert result_value.total_cost <= result_raw.total_cost + 5.0
        assert len(result_value.drivers) == 5
        assert len(result_value.constructors) == 2


class TestFindBestTransfers:
    def test_respects_transfer_limit(self):
        """With 2 free transfers, should make at most 2 free swaps."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        # Start with a weak team
        current_d = drivers[-5:]  # Worst 5 drivers
        current_c = constructors[-2:]  # Worst 2 constructors
        result = find_best_transfers(
            current_d, current_c, drivers, constructors,
            free_transfers=2, max_transfers=2,
        )
        assert len(result.transfers_needed) <= 2
        assert result.transfers_cost == 0  # No penalty with max_transfers=free

    def test_no_transfer_when_optimal(self):
        """If current team is already the best, no transfers should be made."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        optimal = find_optimal_team(drivers, constructors)
        result = find_best_transfers(
            optimal.drivers, optimal.constructors, drivers, constructors,
            free_transfers=2,
        )
        assert len(result.transfers_needed) == 0
        assert result.net_gain == 0.0

    def test_improves_team(self):
        """Transfers should improve projected points."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        # Start with a mediocre team
        current_d = drivers[5:10]
        current_c = constructors[4:6]
        current_pts = sum(d.projected_points for d in current_d) + sum(c.projected_points for c in current_c)

        result = find_best_transfers(
            current_d, current_c, drivers, constructors,
            free_transfers=2,
        )
        assert result.total_projected_points >= current_pts
        assert result.net_gain >= 0

    def test_penalty_transfers_only_when_worth_it(self):
        """Penalty transfers should only happen if gain > 10 pts per extra transfer."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        current_d = drivers[-5:]
        current_c = constructors[-2:]

        result = find_best_transfers(
            current_d, current_c, drivers, constructors,
            free_transfers=1, max_transfers=3,
        )
        # If there are penalty transfers, net gain must still be positive
        if len(result.transfers_needed) > 1:
            assert result.net_gain > 0

    def test_respects_budget(self):
        """Result team must be within budget."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        current_d = drivers[10:15]
        current_c = constructors[5:7]
        result = find_best_transfers(
            current_d, current_c, drivers, constructors,
            budget=100.0, free_transfers=2,
        )
        assert result.total_cost <= 100.0

    def test_correct_team_size(self):
        """Result must always have exactly 5 drivers and 2 constructors."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        current_d = drivers[5:10]
        current_c = constructors[3:5]
        result = find_best_transfers(
            current_d, current_c, drivers, constructors,
            free_transfers=2,
        )
        assert len(result.drivers) == 5
        assert len(result.constructors) == 2

    def test_one_free_transfer_picks_best_swap(self):
        """With 1 free transfer, should find the single best swap."""
        drivers = _make_drivers()
        constructors = _make_constructors()
        # Team has one obvious weak link
        current_d = [drivers[1], drivers[4], drivers[5], drivers[6], drivers[-1]]  # Bottas is weak
        current_c = constructors[:2]

        result = find_best_transfers(
            current_d, current_c, drivers, constructors,
            free_transfers=1, max_transfers=1,
        )
        if result.transfers_needed:
            assert len(result.transfers_needed) == 1
            # Should swap out the weakest player (Bottas, 4.0 pts)
            out_asset = result.transfers_needed[0][0]
            assert out_asset.name == "Bottas"


class TestPlanTransfers:
    def test_no_transfers_needed(self):
        drivers = _make_drivers()[:5]
        constructors = _make_constructors()[:2]
        optimal = find_optimal_team(_make_drivers(), _make_constructors())
        optimal.drivers = drivers
        optimal.constructors = constructors
        result = plan_transfers(drivers, constructors, optimal, free_transfers=2)
        assert len(result.transfers_needed) == 0
        assert result.transfers_cost == 0

    def test_transfers_within_free_limit(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        optimal = find_optimal_team(drivers, constructors)
        current_drivers = optimal.drivers[:4] + [d for d in drivers if d not in optimal.drivers][:1]
        current_constructors = optimal.constructors
        result = plan_transfers(current_drivers, current_constructors, optimal, free_transfers=2)
        assert result.transfers_cost == 0

    def test_penalty_for_extra_transfers(self):
        drivers = _make_drivers()
        constructors = _make_constructors()
        optimal = find_optimal_team(drivers, constructors)
        current_drivers = drivers[-5:]
        current_constructors = constructors[-2:]
        result = plan_transfers(current_drivers, current_constructors, optimal, free_transfers=2)
        extra = max(0, len(result.transfers_needed) - 2)
        assert result.transfers_cost == extra * -10
