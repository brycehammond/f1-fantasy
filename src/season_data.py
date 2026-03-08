"""Seed data from completed 2026 races and qualifying results.

This module provides hardcoded results for races that have already happened,
used to bootstrap projections before the API has full historical data.
It also serves as a fallback if the API is unavailable.

Data is updated after each race weekend.
"""


# Round 1: Australian Grand Prix, Melbourne, March 8 2026
# Russell dominated from pole, Mercedes 1-2 in new regulation era
ROUND_1_QUALIFYING = {
    "Russell": 1,
    "Antonelli": 2,
    "Leclerc": 3,
    "Hamilton": 4,
    "Norris": 5,
    "Bearman": 6,
    "Gasly": 7,
    "Bortoleto": 8,
    "Lawson": 9,
    "Lindblad": 10,
    "Albon": 11,
    "Sainz": 12,
    "Colapinto": 13,
    "Stroll": 14,
    "Alonso": 15,
    "Ocon": 16,
    "Bottas": 17,
    "Perez": 18,
    "Hadjar": 19,
    "Verstappen": 20,  # Crashed in qualifying
    # Piastri: DNS (crashed on way to grid)
    # Hulkenberg: DNS
}

ROUND_1_RACE = {
    "Russell": {"position": 1, "points": 25, "grid": 1, "dnf": False},
    "Antonelli": {"position": 2, "points": 18, "grid": 2, "dnf": False},
    "Leclerc": {"position": 3, "points": 15, "grid": 3, "dnf": False},
    "Hamilton": {"position": 4, "points": 12, "grid": 4, "dnf": False},
    "Norris": {"position": 5, "points": 10, "grid": 5, "dnf": False},
    "Verstappen": {"position": 6, "points": 8, "grid": 20, "dnf": False},  # P20→P6, +14 positions gained
    "Bearman": {"position": 7, "points": 6, "grid": 6, "dnf": False},
    "Lindblad": {"position": 8, "points": 4, "grid": 10, "dnf": False},
    "Bortoleto": {"position": 9, "points": 2, "grid": 8, "dnf": False},
    "Gasly": {"position": 10, "points": 1, "grid": 7, "dnf": False},
    "Albon": {"position": 11, "points": 0, "grid": 11, "dnf": False},
    "Sainz": {"position": 12, "points": 0, "grid": 12, "dnf": False},
    "Colapinto": {"position": 13, "points": 0, "grid": 13, "dnf": False},
    "Lawson": {"position": 14, "points": 0, "grid": 9, "dnf": False},
    "Stroll": {"position": 15, "points": 0, "grid": 14, "dnf": False},
    "Alonso": {"position": 16, "points": 0, "grid": 15, "dnf": False},
    "Ocon": {"position": 17, "points": 0, "grid": 16, "dnf": False},
    "Bottas": {"position": 18, "points": 0, "grid": 17, "dnf": False},
    "Perez": {"position": 19, "points": 0, "grid": 18, "dnf": False},
    "Hadjar": {"position": 20, "points": 0, "grid": 19, "dnf": False},
    # Piastri: DNS, Hulkenberg: DNS
}

# Estimated fantasy scores for Round 1 (race result points + qualifying + overtakes + positions gained/lost)
# These are approximations based on the scoring system
ROUND_1_FANTASY_SCORES = {
    # Driver: (qualifying_score, race_score, total_fantasy_score)
    "Russell":    (10, 25 + 0,  47),   # Pole(10) + P1(25) + no positions gained + est overtakes
    "Antonelli":  (9,  18 + 0,  37),   # P2 quali(9) + P2(18) + no positions
    "Leclerc":    (8,  15 + 0,  30),   # P3 quali(8) + P3(15)
    "Hamilton":   (7,  12 + 0,  25),   # P4 quali(7) + P4(12)
    "Norris":     (6,  10 + 0,  21),   # P5 quali(6) + P5(10)
    "Verstappen": (-5, 8 + 14, 32),    # No time set(-5) + P6(8) + 14 positions gained(+14) + overtakes(~15)
    "Bearman":    (5,  6 - 1,  14),    # P6 quali(5) + P7(6) + lost 1 position(-1)
    "Lindblad":   (1,  4 + 2,  10),    # P10 quali(1) + P8(4) + gained 2(+2) + overtakes
    "Bortoleto":  (3,  2 - 1,   7),    # P8 quali(3) + P9(2) + lost 1(-1)
    "Gasly":      (4,  1 - 3,   4),    # P7 quali(4) + P10(1) + lost 3(-3)
    "Albon":      (0,  0 + 0,   2),    # P11 quali(0) + P11(0)
    "Sainz":      (0,  0 + 0,   1),    # P12(0) + P12(0)
    "Colapinto":  (0,  0 + 0,   1),    # P13(0) + P13(0)
    "Lawson":     (2,  0 - 5,  -1),    # P9 quali(2) + P14(0) + lost 5(-5)
    "Stroll":     (0,  0 - 1,  -1),    # P14(0) + P15(0) + lost 1(-1)
    "Alonso":     (0,  0 - 1,  -1),    # P15(0) + P16(0) + lost 1(-1)
    "Ocon":       (0,  0 - 1,  -1),    # P16(0) + P17(0) + lost 1(-1)
    "Bottas":     (0,  0 - 1,  -1),    # P17(0) + P18(0)
    "Perez":      (0,  0 - 1,  -1),    # P18(0) + P19(0)
    "Hadjar":     (0,  0 - 1,  -1),    # P19(0) + P20(0)
    "Piastri":    (-5, -20,   -25),    # DNS (crashed on way to grid)
    "Hulkenberg": (-5, -20,   -25),    # DNS
}

# Constructor scores for Round 1
ROUND_1_CONSTRUCTOR_SCORES = {
    "Mercedes":      85,   # Russell P1 + Antonelli P2, both Q3, fast pitstops
    "Ferrari":       55,   # Leclerc P3 + Hamilton P4, both Q3
    "McLaren":       -5,   # Norris P5 but Piastri DNS
    "Red Bull":      15,   # Verstappen P6 (from P20!) but Hadjar P20
    "Haas":          12,   # Bearman P7, Ocon P17
    "Racing Bulls":   5,   # Lindblad P8, Lawson P14
    "Audi":          -8,   # Bortoleto P9, Hulkenberg DNS
    "Alpine":         3,   # Gasly P10, Colapinto P13
    "Williams":       1,   # Albon P11, Sainz P12
    "Aston Martin":  -3,   # Stroll P15, Alonso P16
    "Cadillac":      -3,   # Bottas P18, Perez P19
}


def get_completed_rounds() -> list[int]:
    """Return list of completed round numbers."""
    return [1]


def get_driver_fantasy_score(driver_name: str, round_num: int) -> float | None:
    """Get a driver's fantasy score for a specific round."""
    if round_num == 1:
        entry = ROUND_1_FANTASY_SCORES.get(driver_name)
        if entry:
            return entry[2] if isinstance(entry, tuple) else entry
    return None


def get_constructor_fantasy_score(constructor_name: str, round_num: int) -> float | None:
    """Get a constructor's fantasy score for a specific round."""
    if round_num == 1:
        return ROUND_1_CONSTRUCTOR_SCORES.get(constructor_name)
    return None


def get_qualifying_position(driver_name: str, round_num: int) -> int | None:
    """Get a driver's qualifying position for a specific round."""
    if round_num == 1:
        return ROUND_1_QUALIFYING.get(driver_name)
    return None


def get_race_result(driver_name: str, round_num: int) -> dict | None:
    """Get a driver's race result for a specific round."""
    if round_num == 1:
        return ROUND_1_RACE.get(driver_name)
    return None


def get_all_driver_scores() -> dict[str, list[tuple[int, float]]]:
    """Get all driver scores as {name: [(round, score), ...]}."""
    scores = {}
    for name, entry in ROUND_1_FANTASY_SCORES.items():
        score = entry[2] if isinstance(entry, tuple) else entry
        scores[name] = [(1, score)]
    return scores


def get_all_constructor_scores() -> dict[str, list[tuple[int, float]]]:
    """Get all constructor scores as {name: [(round, score), ...]}."""
    scores = {}
    for name, score in ROUND_1_CONSTRUCTOR_SCORES.items():
        scores[name] = [(1, score)]
    return scores
