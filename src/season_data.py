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


# Round 3: Japanese Grand Prix, Suzuka, April 12 2026
# Antonelli won from pole (dropped to P6 off start, won via safety car strategy + fastest lap).
# Bearman 50G crash at Spoon, bruised knee, +10 penalty points (10/12 — 2 more = race ban).
# Verstappen knocked out in Q2, recovered to P8.
ROUND_3_QUALIFYING = {
    "Antonelli": 1,    # Pole
    "Russell": 2,
    "Piastri": 3,
    "Leclerc": 4,
    "Norris": 5,
    "Hamilton": 6,
    "Gasly": 7,
    "Hadjar": 8,
    "Bortoleto": 9,
    "Lindblad": 10,
    "Verstappen": 11,  # Out of Q2
    "Ocon": 12,
    "Hulkenberg": 13,
    "Lawson": 14,
    "Colapinto": 15,
    "Sainz": 16,
    "Albon": 17,
    "Bearman": 18,
    "Perez": 19,
    "Bottas": 20,
    "Alonso": 21,
    "Stroll": 22,
}

ROUND_3_RACE = {
    "Antonelli": {"position": 1, "points": 25, "grid": 1, "dnf": False},   # + fastest lap
    "Piastri": {"position": 2, "points": 18, "grid": 3, "dnf": False},     # +1 position
    "Leclerc": {"position": 3, "points": 15, "grid": 4, "dnf": False},     # +1 position
    "Russell": {"position": 4, "points": 12, "grid": 2, "dnf": False},     # -2 positions, poor race
    "Norris": {"position": 5, "points": 10, "grid": 5, "dnf": False},
    "Hamilton": {"position": 6, "points": 8, "grid": 6, "dnf": False},
    "Gasly": {"position": 7, "points": 6, "grid": 7, "dnf": False},
    "Verstappen": {"position": 8, "points": 4, "grid": 11, "dnf": False},  # +3 positions
    "Lawson": {"position": 9, "points": 2, "grid": 14, "dnf": False},      # +5 positions
    "Ocon": {"position": 10, "points": 1, "grid": 12, "dnf": False},       # +2 positions
    "Hulkenberg": {"position": 11, "points": 0, "grid": 13, "dnf": False},
    "Hadjar": {"position": 12, "points": 0, "grid": 8, "dnf": False},      # -4 positions
    "Bortoleto": {"position": 13, "points": 0, "grid": 9, "dnf": False},   # -4 positions
    "Lindblad": {"position": 14, "points": 0, "grid": 10, "dnf": False},   # -4 positions
    "Sainz": {"position": 15, "points": 0, "grid": 16, "dnf": False},
    "Colapinto": {"position": 16, "points": 0, "grid": 15, "dnf": False},
    "Perez": {"position": 17, "points": 0, "grid": 19, "dnf": False},
    "Alonso": {"position": 18, "points": 0, "grid": 21, "dnf": False},
    "Bottas": {"position": 19, "points": 0, "grid": 20, "dnf": False},
    "Albon": {"position": 20, "points": 0, "grid": 17, "dnf": False},      # -3 positions
    "Stroll": {"position": None, "points": 0, "grid": 22, "dnf": True},    # Water pressure lap 30
    "Bearman": {"position": None, "points": 0, "grid": 18, "dnf": True},   # Massive crash at Spoon lap 20
}

# Estimated fantasy scores for Round 3 (quali + race + bonuses; rough approximations)
ROUND_3_FANTASY_SCORES = {
    "Antonelli":  (10, 35, 45),   # Pole(10) + win(25) + fastest lap(10)
    "Piastri":    (8,  19, 27),   # Q3(8) + P2(18) + +1 position
    "Leclerc":    (7,  16, 23),   # Q4(7) + P3(15) + +1 position
    "Russell":    (9,  10, 19),   # Q2(9) + P4(12) - 2 positions
    "Norris":     (6,  10, 16),   # Q5(6) + P5(10)
    "Hamilton":   (5,   8, 13),   # Q6(5) + P6(8)
    "Gasly":      (4,   6, 10),   # Q7(4) + P7(6)
    "Verstappen": (0,   7,  7),   # Out Q2(0) + P8 from P11 (+3 positions + overtakes)
    "Lawson":     (0,   7,  7),   # Out Q2(0) + P9 from P14 (+5 positions)
    "Ocon":       (0,   3,  3),   # Out Q3(0) + P10 from P12 (+2)
    "Hulkenberg": (0,   2,  2),   # P11 from P13 (+2)
    "Hadjar":     (3,  -4, -1),   # Q8(3) + P12 from P8 (-4 positions)
    "Bortoleto":  (2,  -4, -2),   # Q9(2) + P13 from P9 (-4)
    "Lindblad":   (1,  -4, -3),   # Q10(1) + P14 from P10 (-4)
    "Sainz":      (0,   1,  1),   # P15 from P16 (+1)
    "Colapinto":  (0,  -1, -1),   # P16 from P15 (-1)
    "Perez":      (0,   2,  2),   # P17 from P19 (+2)
    "Alonso":     (0,   3,  3),   # P18 from P21 (+3)
    "Bottas":     (0,   1,  1),   # P19 from P20 (+1)
    "Albon":      (0,  -3, -3),   # P20 from P17 (-3)
    "Bearman":    (0, -20, -20),  # DNF, 50G accident
    "Stroll":     (0, -20, -20),  # DNF water pressure
}

# Constructor scores Round 3 (rough estimates)
ROUND_3_CONSTRUCTOR_SCORES = {
    "Mercedes":         55,  # Antonelli win(25) + Russell P4(12) + both Q3(+10) + pitstop est
    "McLaren":          38,  # Piastri P2(18) + Norris P5(10) + both Q3(+10)
    "Ferrari":          33,  # Leclerc P3(15) + Hamilton P6(8) + both Q3(+10)
    "Alpine":            9,  # Gasly P7(6) + Colapinto P16(-1 net) + one Q3(+3)
    "Red Bull Racing":   7,  # Verstappen P8(+7 net) + Hadjar P12(-4 net) + one Q3(+3)
    "Racing Bulls":      5,  # Lawson P9(+7 net) + Lindblad P14(-4 net) + one Q3(+3)
    "Audi":              3,  # Bortoleto P13(-4 net) + Hulkenberg P11(+2 net) + one Q3(+3)
    "Williams":         -2,  # Sainz P15(+1) + Albon P20(-3)
    "Cadillac":          3,  # Perez P17(+2) + Bottas P19(+1)
    "Haas F1 Team":    -19,  # Bearman DNF(-20) + Ocon P10(+3 net)
    "Aston Martin":    -17,  # Stroll DNF(-20) + Alonso P18(+3)
}


# Round 4: Miami Grand Prix, May 3 2026 (Sprint Weekend)
# Antonelli's 3rd straight pole-to-win (F1 first for 3 maiden poles).
# Norris won the sprint — McLaren's first 2026 win + first non-Mercedes win of season.
# Leclerc had nightmare final lap with late penalties.
# Verstappen spun lap 1, recovered to P5. Hadjar pit lane start (DSQ in quali).
# Hulkenberg DNF (engine), Gasly DNF, Lawson DNF (contact with Gasly), Hadjar DNF.
# Sprint DNS: Hulkenberg (engine), Lindblad (technical). Sprint DSQ: Bortoleto (engine intake).
ROUND_4_SPRINT_QUALIFYING = {
    "Norris": 1,       # Pole — first win of 2026 incoming
    "Antonelli": 2,
    "Piastri": 3,
    "Leclerc": 4,
    "Verstappen": 5,
    "Russell": 6,
    "Hamilton": 7,
    "Colapinto": 8,
    "Hadjar": 9,
    "Gasly": 10,
    "Bortoleto": 11,
    "Hulkenberg": 12,
    "Bearman": 13,
    "Sainz": 14,
    "Lindblad": 15,    # Pit lane start in sprint
    "Lawson": 16,
    "Ocon": 17,
    "Perez": 18,
    "Albon": 19,
    "Bottas": 20,
    "Alonso": 21,
    "Stroll": 22,
}

ROUND_4_SPRINT = {
    "Norris": {"position": 1, "grid": 1, "dnf": False},
    "Piastri": {"position": 2, "grid": 3, "dnf": False},
    "Leclerc": {"position": 3, "grid": 4, "dnf": False},
    "Russell": {"position": 4, "grid": 6, "dnf": False},
    "Verstappen": {"position": 5, "grid": 5, "dnf": False},
    "Antonelli": {"position": 6, "grid": 2, "dnf": False},   # -4 positions
    "Hamilton": {"position": 7, "grid": 7, "dnf": False},
    "Gasly": {"position": 8, "grid": 10, "dnf": False},
    "Hadjar": {"position": 9, "grid": 9, "dnf": False},
    "Colapinto": {"position": 10, "grid": 8, "dnf": False},
    "Ocon": {"position": 11, "grid": 17, "dnf": False},      # +6
    "Bearman": {"position": 12, "grid": 13, "dnf": False},
    "Sainz": {"position": 13, "grid": 14, "dnf": False},
    "Lawson": {"position": 14, "grid": 16, "dnf": False},
    "Alonso": {"position": 15, "grid": 21, "dnf": False},    # +6
    "Perez": {"position": 16, "grid": 18, "dnf": False},
    "Stroll": {"position": 17, "grid": 22, "dnf": False},    # +5
    "Albon": {"position": 18, "grid": 19, "dnf": False},
    "Bottas": {"position": 19, "grid": 20, "dnf": False},
    "Hulkenberg": {"position": None, "grid": 12, "dnf": True},   # DNS engine
    "Lindblad": {"position": None, "grid": 15, "dnf": True},     # DNS technical
    "Bortoleto": {"position": None, "grid": 11, "dnf": True},    # DSQ engine intake
}

ROUND_4_QUALIFYING = {
    "Antonelli": 1,    # 3rd straight pole
    "Verstappen": 2,
    "Leclerc": 3,
    "Norris": 4,
    "Russell": 5,
    "Hamilton": 6,
    "Piastri": 7,
    "Colapinto": 8,
    "Gasly": 9,
    "Hulkenberg": 10,
    "Lawson": 11,
    "Bearman": 12,
    "Sainz": 13,
    "Ocon": 14,
    "Albon": 15,
    "Lindblad": 16,
    "Alonso": 17,
    "Stroll": 18,
    "Bottas": 19,
    "Perez": 20,
    "Bortoleto": 21,
    "Hadjar": None,    # DSQ — pit lane start
}

ROUND_4_RACE = {
    "Antonelli": {"position": 1, "points": 25, "grid": 1, "dnf": False},
    "Norris": {"position": 2, "points": 18, "grid": 4, "dnf": False},      # + fastest lap
    "Piastri": {"position": 3, "points": 15, "grid": 7, "dnf": False},     # +4 positions
    "Russell": {"position": 4, "points": 12, "grid": 5, "dnf": False},
    "Verstappen": {"position": 5, "points": 10, "grid": 2, "dnf": False},  # -3, spun lap 1
    "Hamilton": {"position": 6, "points": 8, "grid": 6, "dnf": False},
    "Colapinto": {"position": 7, "points": 6, "grid": 8, "dnf": False},
    "Leclerc": {"position": 8, "points": 4, "grid": 3, "dnf": False},      # -5, late-race penalties
    "Sainz": {"position": 9, "points": 2, "grid": 13, "dnf": False},       # +4
    "Albon": {"position": 10, "points": 1, "grid": 15, "dnf": False},      # +5
    "Bearman": {"position": 11, "points": 0, "grid": 12, "dnf": False},
    "Bortoleto": {"position": 12, "points": 0, "grid": 21, "dnf": False},  # +9
    "Ocon": {"position": 13, "points": 0, "grid": 14, "dnf": False},
    "Lindblad": {"position": 14, "points": 0, "grid": 16, "dnf": False},
    "Alonso": {"position": 15, "points": 0, "grid": 17, "dnf": False},
    "Perez": {"position": 16, "points": 0, "grid": 20, "dnf": False},      # +4
    "Stroll": {"position": 17, "points": 0, "grid": 18, "dnf": False},
    "Bottas": {"position": 18, "points": 0, "grid": 19, "dnf": False},
    "Hulkenberg": {"position": None, "points": 0, "grid": 10, "dnf": True},
    "Lawson": {"position": None, "points": 0, "grid": 11, "dnf": True},    # contact with Gasly
    "Gasly": {"position": None, "points": 0, "grid": 9, "dnf": True},
    "Hadjar": {"position": None, "points": 0, "grid": 22, "dnf": True},    # Pit lane start
}

# Estimated fantasy scores for Round 4 (quali + sprint + race + bonuses)
ROUND_4_FANTASY_SCORES = {
    "Norris":     (7,  38, 45),   # Q4(7) + sprint win(8) + P2(18) +2 pos + FL(10)
    "Antonelli":  (10, 24, 34),   # Pole(10) + sprint P6 from P2(3-4=-1) + win(25)
    "Piastri":    (4,  27, 31),   # Q7(4) + sprint P2(7+1=8) + P3 from P7(15+4=19)
    "Russell":    (6,  20, 26),   # Q5(6) + sprint P4 from P6(5+2=7) + P4(12+1=13)
    "Verstappen": (9,  11, 20),   # Q2(9) + sprint P5(4) + P5 from P2(10-3=7)
    "Hamilton":   (5,  10, 15),   # Q6(5) + sprint P7(2) + P6(8)
    "Leclerc":    (8,   6, 14),   # Q3(8) + sprint P3(6+1=7) + P8 from P3(4-5=-1)
    "Colapinto":  (3,   5,  8),   # Q8(3) + sprint P10 from P8(-2) + P7 from P8(+1)(6+1=7)
    "Sainz":      (0,   7,  7),   # Out Q3(0) + sprint P13(0+1=1) + P9 from P13(2+4=6)
    "Albon":      (0,   6,  6),   # P10 from P15(1+5=6) + sprint P18(0)
    "Ocon":       (0,   6,  6),   # Sprint P11 from P17(+6=5? capped 0+5) + P13 from P14(+1)
    "Alonso":     (0,   7,  7),   # Sprint P15 from P21(+6) + P15 from P17(+2)
    "Stroll":     (0,   5,  5),   # Sprint P17 from P22(+5) + P17 from P18(+1)
    "Perez":      (0,   5,  5),   # Sprint P16 from P18(+2) + P16 from P20(+4)
    "Bearman":    (0,   2,  2),   # Sprint P12 from P13(+1) + P11 from P12(+1)
    "Bottas":     (0,   1,  1),   # Sprint P19(0) + P18 from P19(+1)
    "Bortoleto":  (0,  -6, -6),   # Sprint DSQ(-15) + P12 from P21(+9)
    "Lindblad":   (0,  -8, -8),   # Sprint DNS(-10) + P14 from P16(+2)
    "Gasly":      (2, -17, -15),  # Q9(2) + sprint P8 from P10(1+2=3) + race DNF(-20)
    "Lawson":     (0, -19, -19),  # Sprint P14 from P16(+1) + race DNF(-20)
    "Hulkenberg": (1, -30, -29),  # Q10(1) + sprint DNS(-10) + race DNF(-20)
    "Hadjar":   (-15, -20, -35),  # DSQ quali(-15) + sprint P9(0) + race DNF(-20)
}

# Constructor scores Round 4 (rough estimates including sprint contribution)
ROUND_4_CONSTRUCTOR_SCORES = {
    "Mercedes":         85,  # Antonelli win + Russell P4 + sprint P4+P6 + both Q3 + pitstop
    "McLaren":          78,  # Norris P2+sprint win + Piastri P3+sprint P2 + both Q3
    "Ferrari":          35,  # Leclerc P8 + Hamilton P6 + sprint P3+P7 + both Q3
    "Williams":         12,  # Sainz P9 + Albon P10 + sprint P13+P18
    "Alpine":            6,  # Colapinto P7 + Gasly DNF + sprint P10+P8 + one Q3(+3)
    "Cadillac":          0,  # Perez P16 + Bottas P18 + sprint P16+P19
    "Haas F1 Team":      0,  # Bearman P11 + Ocon P13 + sprint P12+P11
    "Aston Martin":     -2,  # Stroll P17 + Alonso P15 + sprint P15+P17
    "Red Bull Racing":  -8,  # Verstappen P5 + Hadjar DNF + sprint P5+P9 + one Q3(+3)
    "Racing Bulls":    -23,  # Lawson DNF + Lindblad P14 + sprint P14 + sprint DNS
    "Audi":            -42,  # Hulkenberg DNF + Bortoleto P12 + sprint DNS + sprint DSQ
}


def get_completed_rounds() -> list[int]:
    """Return list of completed round numbers."""
    return [1, 2, 3, 4]


_FANTASY_SCORES_BY_ROUND = {
    1: ROUND_1_FANTASY_SCORES,
    2: ROUND_2_FANTASY_SCORES,
    3: ROUND_3_FANTASY_SCORES,
    4: ROUND_4_FANTASY_SCORES,
}

_CONSTRUCTOR_SCORES_BY_ROUND = {
    1: ROUND_1_CONSTRUCTOR_SCORES,
    2: ROUND_2_CONSTRUCTOR_SCORES,
    3: ROUND_3_CONSTRUCTOR_SCORES,
    4: ROUND_4_CONSTRUCTOR_SCORES,
}

_QUALIFYING_BY_ROUND = {
    1: ROUND_1_QUALIFYING,
    2: ROUND_2_QUALIFYING,
    3: ROUND_3_QUALIFYING,
    4: ROUND_4_QUALIFYING,
}

_RACE_BY_ROUND = {
    1: ROUND_1_RACE,
    2: ROUND_2_RACE,
    3: ROUND_3_RACE,
    4: ROUND_4_RACE,
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
