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


# Round 2: Chinese Grand Prix, Shanghai, March 13-15 2026 (Sprint Weekend)
# Antonelli maiden win + youngest pole-sitter ever. Mercedes 1-2 again.
# McLaren double DNS (Norris/Piastri PU electrical failures), Verstappen DNF (electrical)
# Aston Martin double DNF, Bortoleto/Albon DNS
ROUND_2_SPRINT_QUALIFYING = {
    "Russell": 1,
    "Antonelli": 2,
    "Norris": 3,
    "Hamilton": 4,
    "Piastri": 5,
    "Leclerc": 6,
    "Gasly": 7,
    "Verstappen": 8,
    "Bearman": 9,
    "Hadjar": 10,
    "Hulkenberg": 11,
    "Colapinto": 12,
    "Ocon": 13,
    "Lawson": 14,
    "Lindblad": 15,
    "Bortoleto": 16,
    "Sainz": 17,
    "Albon": 18,
    "Alonso": 19,
    "Bottas": 20,
    "Stroll": 21,
    "Perez": 22,  # Fuel pump issue, no time set in SQ1
}

ROUND_2_SPRINT = {
    "Russell": {"position": 1, "grid": 1, "dnf": False},
    "Leclerc": {"position": 2, "grid": 6, "dnf": False},
    "Hamilton": {"position": 3, "grid": 4, "dnf": False},
    "Norris": {"position": 4, "grid": 3, "dnf": False},
    "Antonelli": {"position": 5, "grid": 2, "dnf": False},  # 10s penalty for Hadjar contact
    "Piastri": {"position": 6, "grid": 5, "dnf": False},
    "Lawson": {"position": 7, "grid": 14, "dnf": False},
    "Bearman": {"position": 8, "grid": 9, "dnf": False},
    "Verstappen": {"position": 9, "grid": 8, "dnf": False},
    "Ocon": {"position": 10, "grid": 13, "dnf": False},
    "Gasly": {"position": 11, "grid": 7, "dnf": False},
    "Sainz": {"position": 12, "grid": 17, "dnf": False},
    "Bortoleto": {"position": 13, "grid": 16, "dnf": False},
    "Colapinto": {"position": 14, "grid": 12, "dnf": False},
    "Hadjar": {"position": 15, "grid": 10, "dnf": False},  # Damage from Antonelli contact
    "Albon": {"position": 16, "grid": 22, "dnf": False},   # Pit lane start
    "Alonso": {"position": 17, "grid": 19, "dnf": False},
    "Stroll": {"position": 18, "grid": 21, "dnf": False},
    "Perez": {"position": 19, "grid": 22, "dnf": False},
    "Hulkenberg": {"position": None, "grid": 11, "dnf": True},  # Hydraulics failure
    "Bottas": {"position": None, "grid": 20, "dnf": True},
    "Lindblad": {"position": None, "grid": 15, "dnf": True},
}

ROUND_2_QUALIFYING = {
    "Antonelli": 1,   # Youngest pole-sitter in F1 history
    "Russell": 2,     # Car issue in Q3, stuck in 1st gear
    "Hamilton": 3,
    "Leclerc": 4,
    "Piastri": 5,
    "Norris": 6,
    "Gasly": 7,
    "Verstappen": 8,
    "Hadjar": 9,
    "Bearman": 10,
    "Hulkenberg": 11,
    "Colapinto": 12,
    "Ocon": 13,
    "Lawson": 14,
    "Lindblad": 15,
    "Bortoleto": 16,
    "Sainz": 17,
    "Albon": 18,
    "Alonso": 19,
    "Bottas": 20,
    "Stroll": 21,
    "Perez": 22,
}

ROUND_2_RACE = {
    "Antonelli": {"position": 1, "points": 25, "grid": 1, "dnf": False},  # Maiden win + fastest lap + DOTD
    "Russell": {"position": 2, "points": 18, "grid": 2, "dnf": False},
    "Hamilton": {"position": 3, "points": 15, "grid": 3, "dnf": False},   # First Ferrari podium
    "Leclerc": {"position": 4, "points": 12, "grid": 4, "dnf": False},
    "Bearman": {"position": 5, "points": 10, "grid": 9, "dnf": False},    # +4 positions
    "Gasly": {"position": 6, "points": 8, "grid": 6, "dnf": False},
    "Lawson": {"position": 7, "points": 6, "grid": 13, "dnf": False},     # +6 positions
    "Hadjar": {"position": 8, "points": 4, "grid": 8, "dnf": False},
    "Sainz": {"position": 9, "points": 2, "grid": 16, "dnf": False},      # +7 positions
    "Colapinto": {"position": 10, "points": 1, "grid": 11, "dnf": False},
    "Hulkenberg": {"position": 11, "points": 0, "grid": 10, "dnf": False},
    "Lindblad": {"position": 12, "points": 0, "grid": 14, "dnf": False},
    "Bottas": {"position": 13, "points": 0, "grid": 18, "dnf": False},
    "Ocon": {"position": 14, "points": 0, "grid": 12, "dnf": False},      # Lost 2 positions, driving error
    "Perez": {"position": 15, "points": 0, "grid": 20, "dnf": False},
    "Verstappen": {"position": None, "points": 0, "grid": 7, "dnf": True},   # Electrical failure lap 46
    "Alonso": {"position": None, "points": 0, "grid": 17, "dnf": True},      # Retired lap 32
    "Stroll": {"position": None, "points": 0, "grid": 19, "dnf": True},      # Retired lap 10, caused SC
    "Piastri": {"position": None, "points": 0, "grid": 5, "dnf": True},      # DNS, PU electrical
    "Norris": {"position": None, "points": 0, "grid": None, "dnf": True},    # DNS, PU electrical, pit lane
    "Bortoleto": {"position": None, "points": 0, "grid": 15, "dnf": True},   # DNS, technical
    "Albon": {"position": None, "points": 0, "grid": None, "dnf": True},     # DNS, technical, pit lane
}

# Actual fantasy scores from API gameday_points for Round 2
ROUND_2_FANTASY_SCORES = {
    "Antonelli":  (10, 58, 68),   # Pole(10) + race win(25) + fastest lap(10) + DOTD(10) + sprint(4) - sprint penalty
    "Leclerc":    (8,  43, 51),   # Q4(8) + race P4(12) + sprint P2(7) + positions gained
    "Hamilton":   (8,  40, 48),   # Q3(8) + race P3(15) + sprint P3(6) + positions
    "Russell":    (9,  36, 45),   # Q2(9) + race P2(18) + sprint win(8)
    "Lawson":     (0,  35, 35),   # Out of Q2(0) + race P7 from P13(+6 positions) + sprint P7(2)
    "Bearman":    (1,  33, 34),   # Q10(1) + race P5 from P9(+4 positions, 10pts) + sprint P8(1)
    "Sainz":      (0,  28, 28),   # Out of Q2(0) + race P9 from P16(+7 positions, 2pts) + sprint P12
    "Ocon":       (0,  24, 24),   # Out of Q2(0) + race P14(lost positions) + sprint P10
    "Perez":      (0,  20, 20),   # Out of Q1(0) + race P15 from P20(+5 positions) + sprint P19
    "Gasly":      (4,  16, 20),   # Q7(4) + race P6(8) + sprint P11(lost positions)
    "Hadjar":     (2,  17, 19),   # Q9(2) + race P8(4) + sprint P15(-5 from contact)
    "Colapinto":  (0,  18, 18),   # Out of Q2(0) + race P10(1) + sprint P14 + positions gained
    "Verstappen": (3,  11, 14),   # Q8(3) + DNF(-20) + sprint P9 + positions
    "Lindblad":   (0,   7,  7),   # Out of Q2(0) + race P12 from P14 + sprint DNF(-10)
    "Hulkenberg": (0,   7,  7),   # Out of Q2(0) + race P11 + sprint DNF
    "Bottas":     (0,   3,  3),   # Out of Q1(0) + race P13 from P18(+5) + sprint DNF
    "Norris":     (-5, -5, -10),  # Q6 but DNS(-5) + DNS race(-20) + sprint P4(5)
    "Albon":      (-5, -2, -7),   # Out of Q1(0) + DNS race + sprint P16
    "Alonso":     (0,  -7, -7),   # Out of Q1(0) + DNF(-20) + sprint P17
    "Piastri":    (-5, -2, -7),   # Q5 but DNS(-5) + DNS(-20) + sprint P6(3)
    "Bortoleto":  (0, -14, -14),  # Out of Q2(0) + DNS(-20?) + sprint P13
    "Stroll":     (0, -14, -14),  # Out of Q1(0) + DNF(-20) + sprint P18
}

ROUND_2_CONSTRUCTOR_SCORES = {
    "Ferrari":       119,  # Leclerc P4 + Hamilton P3, both Q3(+10), strong pitstops
    "Mercedes":      115,  # Russell P2 + Antonelli P1, both Q3(+10), sprint 1-2
    "Haas F1 Team":   65,  # Bearman P5 + Ocon P14, one Q3(+3)
    "Racing Bulls":   50,  # Lawson P7 + Lindblad P12
    "Red Bull Racing": 45, # Hadjar P8, Verstappen DNF
    "Alpine":          45, # Gasly P6 + Colapinto P10
    "Williams":        22, # Sainz P9 + Albon DNS
    "Cadillac":        22, # Perez P15 + Bottas P13
    "McLaren":         -7, # Double DNS
    "Audi":            -4, # Bortoleto DNS + Hulkenberg P11
    "Aston Martin":   -20, # Double DNF
}


def get_completed_rounds() -> list[int]:
    """Return list of completed round numbers."""
    return [1, 2]


_FANTASY_SCORES_BY_ROUND = {
    1: ROUND_1_FANTASY_SCORES,
    2: ROUND_2_FANTASY_SCORES,
}

_CONSTRUCTOR_SCORES_BY_ROUND = {
    1: ROUND_1_CONSTRUCTOR_SCORES,
    2: ROUND_2_CONSTRUCTOR_SCORES,
}

_QUALIFYING_BY_ROUND = {
    1: ROUND_1_QUALIFYING,
    2: ROUND_2_QUALIFYING,
}

_RACE_BY_ROUND = {
    1: ROUND_1_RACE,
    2: ROUND_2_RACE,
}


def get_driver_fantasy_score(driver_name: str, round_num: int) -> float | None:
    """Get a driver's fantasy score for a specific round."""
    scores = _FANTASY_SCORES_BY_ROUND.get(round_num, {})
    entry = scores.get(driver_name)
    if entry:
        return entry[2] if isinstance(entry, tuple) else entry
    return None


def get_constructor_fantasy_score(constructor_name: str, round_num: int) -> float | None:
    """Get a constructor's fantasy score for a specific round."""
    return _CONSTRUCTOR_SCORES_BY_ROUND.get(round_num, {}).get(constructor_name)


def get_qualifying_position(driver_name: str, round_num: int) -> int | None:
    """Get a driver's qualifying position for a specific round."""
    return _QUALIFYING_BY_ROUND.get(round_num, {}).get(driver_name)


def get_race_result(driver_name: str, round_num: int) -> dict | None:
    """Get a driver's race result for a specific round."""
    return _RACE_BY_ROUND.get(round_num, {}).get(driver_name)


def get_all_driver_scores() -> dict[str, list[tuple[int, float]]]:
    """Get all driver scores as {name: [(round, score), ...]}."""
    scores = {}
    for round_num, round_scores in _FANTASY_SCORES_BY_ROUND.items():
        for name, entry in round_scores.items():
            score = entry[2] if isinstance(entry, tuple) else entry
            scores.setdefault(name, []).append((round_num, score))
    return scores


def get_all_constructor_scores() -> dict[str, list[tuple[int, float]]]:
    """Get all constructor scores as {name: [(round, score), ...]}."""
    scores = {}
    for round_num, round_scores in _CONSTRUCTOR_SCORES_BY_ROUND.items():
        for name, score in round_scores.items():
            scores.setdefault(name, []).append((round_num, score))
    return scores
