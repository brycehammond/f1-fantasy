"""Advanced driver/constructor projection model.

Combines multiple signals to project fantasy points for the next race:
1. Historical fantasy scores (weighted recent form)
2. Points-per-million (PPM) value metric
3. Circuit-specific performance (weighted by track-type similarity)
4. Qualifying pace as a predictor of race performance
5. Seed data from completed 2026 races
"""

from dataclasses import dataclass

from src.circuits import get_circuit, track_type_similarity, TrackType
from src.season_data import (
    get_all_driver_scores,
    get_all_constructor_scores,
    get_qualifying_position,
    get_completed_rounds,
    ROUND_1_QUALIFYING,
)


@dataclass
class Projection:
    raw_points: float          # Projected fantasy points
    ppm: float                 # Points-per-million (value metric)
    confidence: float          # 0.0-1.0, how much data backs this projection
    breakdown: dict            # Component contributions for explainability


# --- Known team strength tiers based on 2026 pre-season and Round 1 ---
# Maps constructor to a base strength multiplier
TEAM_STRENGTH = {
    "Mercedes": 1.30,
    "Ferrari": 1.15,
    "McLaren": 1.10,
    "Red Bull": 1.10,
    "Haas": 0.80,
    "Racing Bulls": 0.75,
    "Alpine": 0.75,
    "Williams": 0.70,
    "Audi": 0.65,
    "Aston Martin": 0.65,
    "Cadillac": 0.55,
}

# Driver skill modifier relative to their teammate (based on form, reputation)
DRIVER_SKILL = {
    "Verstappen": 1.25,    # GOAT-tier recovery drives, but Red Bull car is weaker
    "Russell": 1.15,
    "Norris": 1.10,
    "Leclerc": 1.10,
    "Hamilton": 1.05,
    "Antonelli": 1.05,     # Impressive debut, P2 in first race
    "Piastri": 1.05,
    "Albon": 0.95,
    "Sainz": 0.95,
    "Gasly": 0.90,
    "Bearman": 0.90,       # Strong debut season
    "Hadjar": 0.85,
    "Lindblad": 0.85,      # Rookie but showed pace
    "Bortoleto": 0.85,
    "Lawson": 0.80,
    "Alonso": 0.80,
    "Ocon": 0.75,
    "Hulkenberg": 0.75,
    "Stroll": 0.70,
    "Colapinto": 0.70,
    "Bottas": 0.65,
    "Perez": 0.60,
}


def project_driver(
    name: str,
    price: float,
    team: str,
    target_round: int,
    race_history: list[dict] | None = None,
) -> Projection:
    """Project fantasy points for a driver at a specific upcoming race.

    Blends multiple signals with weights that shift as more data becomes available.
    """
    components = {}
    weights = {}

    completed = get_completed_rounds()
    n_completed = len(completed)

    # --- Signal 1: Seed data (actual fantasy scores from completed rounds) ---
    all_scores = get_all_driver_scores()
    historical_scores = all_scores.get(name, [])

    if historical_scores:
        # Weighted average favoring recent races
        race_weights = list(range(1, len(historical_scores) + 1))
        scores = [s for _, s in historical_scores]
        weighted_avg = sum(s * w for s, w in zip(scores, race_weights)) / sum(race_weights)
        components["form"] = weighted_avg
        weights["form"] = min(0.45, 0.15 * n_completed)  # Grows with more data

    # --- Signal 2: Circuit-specific weighting ---
    target_circuit = get_circuit(target_round)
    if target_circuit and historical_scores:
        circuit_weighted_scores = []
        circuit_weights = []
        for rd, score in historical_scores:
            past_circuit = get_circuit(rd)
            if past_circuit:
                sim = track_type_similarity(target_circuit.track_type, past_circuit.track_type)
                circuit_weighted_scores.append(score * sim)
                circuit_weights.append(sim)

        if circuit_weights:
            circuit_avg = sum(circuit_weighted_scores) / sum(circuit_weights)
            components["circuit_fit"] = circuit_avg
            weights["circuit_fit"] = min(0.20, 0.07 * n_completed)

    # --- Signal 3: Qualifying pace predictor ---
    # Strong qualifying correlates with strong race result (~0.7 correlation historically)
    quali_positions = []
    for rd in completed:
        pos = get_qualifying_position(name, rd)
        if pos is not None:
            quali_positions.append(pos)

    if quali_positions:
        avg_quali = sum(quali_positions) / len(quali_positions)
        # Convert quali position to expected fantasy points
        # P1 ≈ 40pts, P5 ≈ 20pts, P10 ≈ 8pts, P15 ≈ 0pts, P20 ≈ -5pts
        quali_projection = max(-10, 45 - (avg_quali * 2.5))
        components["qualifying_pace"] = quali_projection
        weights["qualifying_pace"] = min(0.20, 0.07 * n_completed)

    # --- Signal 4: Team strength + driver skill baseline ---
    team_mult = TEAM_STRENGTH.get(team, 0.70)
    driver_mult = DRIVER_SKILL.get(name, 0.75)
    baseline = price * 1.1 * team_mult * driver_mult

    # Adjust for circuit characteristics
    if target_circuit:
        # High overtaking difficulty hurts drivers who tend to recover from bad qualifying
        # (Verstappen, aggressive drivers) — but helps front-runners
        if name in ("Verstappen", "Hamilton", "Norris"):
            baseline *= (1.0 - target_circuit.overtaking_difficulty * 0.15)
        # Safety car probability benefits aggressive/brave drivers
        baseline *= (1.0 + target_circuit.safety_car_probability * 0.1)
        # Sprint weekends have ~30% more points available
        if target_circuit.has_sprint:
            baseline *= 1.25
        # DNF risk — slight haircut to expected value
        baseline *= (1.0 - target_circuit.dnf_rate * 0.5)

    components["baseline"] = baseline
    # Baseline weight decreases as we get more actual data
    weights["baseline"] = max(0.20, 1.0 - 0.15 * n_completed)

    # --- Signal 5: PPM-aware adjustment ---
    # Identify value picks: drivers scoring above their price-implied expectation
    if historical_scores:
        actual_avg = sum(s for _, s in historical_scores) / len(historical_scores)
        price_implied = price * 1.3
        overperformance = actual_avg - price_implied
        if overperformance > 5:
            components["value_bonus"] = overperformance * 0.3
            weights["value_bonus"] = 0.10

    # --- Combine all signals ---
    total_weight = sum(weights.values())
    if total_weight == 0:
        raw_points = price * 1.3
        confidence = 0.1
    else:
        raw_points = sum(
            components[k] * (weights[k] / total_weight)
            for k in components
            if k in weights
        )
        confidence = min(1.0, 0.15 + 0.12 * n_completed)

    ppm = raw_points / price if price > 0 else 0

    return Projection(
        raw_points=raw_points,
        ppm=ppm,
        confidence=confidence,
        breakdown={k: (components[k], weights.get(k, 0)) for k in components},
    )


def project_constructor(
    name: str,
    price: float,
    target_round: int,
    race_history: list[dict] | None = None,
) -> Projection:
    """Project fantasy points for a constructor at a specific upcoming race."""
    components = {}
    weights = {}

    completed = get_completed_rounds()
    n_completed = len(completed)

    # Seed data
    all_scores = get_all_constructor_scores()
    historical_scores = all_scores.get(name, [])

    if historical_scores:
        race_weights = list(range(1, len(historical_scores) + 1))
        scores = [s for _, s in historical_scores]
        weighted_avg = sum(s * w for s, w in zip(scores, race_weights)) / sum(race_weights)
        components["form"] = weighted_avg
        weights["form"] = min(0.45, 0.15 * n_completed)

    # Circuit weighting for constructors
    target_circuit = get_circuit(target_round)
    if target_circuit and historical_scores:
        circuit_weighted = []
        circuit_w = []
        for rd, score in historical_scores:
            past = get_circuit(rd)
            if past:
                sim = track_type_similarity(target_circuit.track_type, past.track_type)
                circuit_weighted.append(score * sim)
                circuit_w.append(sim)
        if circuit_w:
            components["circuit_fit"] = sum(circuit_weighted) / sum(circuit_w)
            weights["circuit_fit"] = min(0.20, 0.07 * n_completed)

    # Baseline from team strength
    team_mult = TEAM_STRENGTH.get(name, 0.70)
    baseline = price * 1.3 * team_mult

    if target_circuit:
        if target_circuit.has_sprint:
            baseline *= 1.25
        baseline *= (1.0 - target_circuit.dnf_rate * 0.3)
        # Pitstop bonus potential (top teams tend to have faster stops)
        if team_mult >= 1.0:
            baseline *= 1.08

    components["baseline"] = baseline
    weights["baseline"] = max(0.20, 1.0 - 0.15 * n_completed)

    # Value bonus
    if historical_scores:
        actual_avg = sum(s for _, s in historical_scores) / len(historical_scores)
        price_implied = price * 1.5
        overperf = actual_avg - price_implied
        if overperf > 5:
            components["value_bonus"] = overperf * 0.3
            weights["value_bonus"] = 0.10

    # Combine
    total_weight = sum(weights.values())
    if total_weight == 0:
        raw_points = price * 1.5
        confidence = 0.1
    else:
        raw_points = sum(
            components[k] * (weights[k] / total_weight)
            for k in components
            if k in weights
        )
        confidence = min(1.0, 0.15 + 0.12 * n_completed)

    ppm = raw_points / price if price > 0 else 0

    return Projection(
        raw_points=raw_points,
        ppm=ppm,
        confidence=confidence,
        breakdown={k: (components[k], weights.get(k, 0)) for k in components},
    )


def rank_by_value(projections: dict[str, Projection]) -> list[tuple[str, Projection]]:
    """Rank assets by points-per-million (value picks first)."""
    return sorted(projections.items(), key=lambda x: x[1].ppm, reverse=True)
