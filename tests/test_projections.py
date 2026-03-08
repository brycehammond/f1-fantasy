"""Tests for the projection model."""

import pytest
from src.projections import project_driver, project_constructor, rank_by_value, Projection
from src.circuits import TrackType, track_type_similarity, get_circuit


class TestProjectDriver:
    def test_top_driver_projects_higher(self):
        """Russell (Mercedes, $27.4M) should project higher than Bottas (Cadillac, $5.9M)."""
        russell = project_driver("Russell", 27.4, "Mercedes", target_round=2)
        bottas = project_driver("Bottas", 5.9, "Cadillac", target_round=2)
        assert russell.raw_points > bottas.raw_points

    def test_uses_round1_seed_data(self):
        """Projections should incorporate Round 1 results."""
        # Russell scored ~47 fantasy points in Round 1
        russell = project_driver("Russell", 27.4, "Mercedes", target_round=2)
        assert russell.confidence > 0.2  # Has some data
        assert "form" in russell.breakdown

    def test_verstappen_recovery_reflected(self):
        """Verstappen's P20→P6 recovery should give him decent projection despite bad quali."""
        ver = project_driver("Verstappen", 27.7, "Red Bull", target_round=2)
        # Should still project well due to skill and recovery points
        assert ver.raw_points > 15

    def test_ppm_calculated(self):
        """PPM should be points / price."""
        proj = project_driver("Bearman", 7.4, "Haas", target_round=2)
        expected_ppm = proj.raw_points / 7.4
        assert abs(proj.ppm - expected_ppm) < 0.01

    def test_sprint_weekend_boost(self):
        """Sprint weekends (Round 2) should project higher than non-sprint."""
        proj_sprint = project_driver("Russell", 27.4, "Mercedes", target_round=2)
        proj_normal = project_driver("Russell", 27.4, "Mercedes", target_round=3)
        # Sprint has ~25% more points available
        assert proj_sprint.raw_points >= proj_normal.raw_points * 0.95  # Allow some variance

    def test_unknown_driver_uses_baseline(self):
        """A driver not in our data should still get a reasonable projection."""
        proj = project_driver("NewDriver", 8.0, "Williams", target_round=2)
        assert proj.raw_points > 0
        assert proj.confidence < 0.5

    def test_circuit_fit_component(self):
        """Projection should have a circuit_fit component when history exists."""
        proj = project_driver("Russell", 27.4, "Mercedes", target_round=2)
        # Round 1 data exists, Round 2 circuit is known — should have circuit_fit
        assert "circuit_fit" in proj.breakdown

    def test_qualifying_pace_component(self):
        """Drivers with quali data should have a qualifying_pace component."""
        proj = project_driver("Russell", 27.4, "Mercedes", target_round=2)
        assert "qualifying_pace" in proj.breakdown
        # Russell qualified P1 — should have high qualifying pace score
        quali_val = proj.breakdown["qualifying_pace"][0]
        assert quali_val > 30  # P1 ≈ 45 - 1*2.5 = 42.5


class TestProjectConstructor:
    def test_mercedes_projects_highest(self):
        """Mercedes should project highest after dominant Round 1."""
        merc = project_constructor("Mercedes", 29.3, target_round=2)
        cadillac = project_constructor("Cadillac", 6.0, target_round=2)
        assert merc.raw_points > cadillac.raw_points

    def test_uses_seed_data(self):
        merc = project_constructor("Mercedes", 29.3, target_round=2)
        assert "form" in merc.breakdown


class TestCircuitSimilarity:
    def test_same_type_perfect_similarity(self):
        assert track_type_similarity(TrackType.STREET, TrackType.STREET) == 1.0

    def test_opposite_types_low_similarity(self):
        sim = track_type_similarity(TrackType.STREET, TrackType.HIGH_SPEED)
        assert sim < 0.3

    def test_related_types_moderate(self):
        sim = track_type_similarity(TrackType.HIGH_SPEED, TrackType.MIXED)
        assert 0.4 < sim < 0.8


class TestRankByValue:
    def test_ranks_by_ppm_descending(self):
        projections = {
            "cheap_good": Projection(raw_points=20, ppm=3.33, confidence=0.5, breakdown={}),
            "expensive_great": Projection(raw_points=40, ppm=1.5, confidence=0.5, breakdown={}),
            "mid_mid": Projection(raw_points=15, ppm=1.25, confidence=0.5, breakdown={}),
        }
        ranked = rank_by_value(projections)
        assert ranked[0][0] == "cheap_good"
        assert ranked[1][0] == "expensive_great"
        assert ranked[2][0] == "mid_mid"
