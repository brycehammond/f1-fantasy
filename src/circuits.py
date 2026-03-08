"""Circuit classification and track-type similarity for projections."""

from dataclasses import dataclass
from enum import Enum


class TrackType(Enum):
    STREET = "street"           # Tight, low-speed, safety cars likely (Monaco, Singapore, Baku, Vegas, Melbourne)
    HIGH_SPEED = "high_speed"   # Power-sensitive, long straights (Monza, Spa, Jeddah)
    TECHNICAL = "technical"     # High downforce, complex corners (Barcelona, Hungary, Suzuka)
    MIXED = "mixed"             # Balanced layouts (Silverstone, Austin, Bahrain)
    SPRINT = "sprint"           # Track type doesn't change but sprint weekends have extra scoring


@dataclass
class Circuit:
    round: int
    name: str
    country: str
    track_type: TrackType
    has_sprint: bool
    overtaking_difficulty: float  # 0.0 (easy to pass) to 1.0 (nearly impossible)
    safety_car_probability: float  # 0.0 to 1.0 based on historical data
    dnf_rate: float  # Historical average DNFs per race (fraction of grid)


# Full 2026 calendar with circuit characteristics
CIRCUITS_2026: dict[int, Circuit] = {
    1: Circuit(1, "Albert Park", "Australia", TrackType.STREET, False,
               overtaking_difficulty=0.5, safety_car_probability=0.65, dnf_rate=0.18),
    2: Circuit(2, "Shanghai", "China", TrackType.MIXED, True,
               overtaking_difficulty=0.35, safety_car_probability=0.40, dnf_rate=0.12),
    3: Circuit(3, "Suzuka", "Japan", TrackType.TECHNICAL, False,
               overtaking_difficulty=0.65, safety_car_probability=0.35, dnf_rate=0.10),
    4: Circuit(4, "Bahrain", "Bahrain", TrackType.MIXED, False,
               overtaking_difficulty=0.30, safety_car_probability=0.35, dnf_rate=0.12),
    5: Circuit(5, "Jeddah", "Saudi Arabia", TrackType.HIGH_SPEED, False,
               overtaking_difficulty=0.40, safety_car_probability=0.55, dnf_rate=0.15),
    6: Circuit(6, "Miami", "USA", TrackType.STREET, True,
               overtaking_difficulty=0.45, safety_car_probability=0.50, dnf_rate=0.13),
    7: Circuit(7, "Montreal", "Canada", TrackType.MIXED, True,
               overtaking_difficulty=0.35, safety_car_probability=0.55, dnf_rate=0.16),
    8: Circuit(8, "Monaco", "Monaco", TrackType.STREET, False,
               overtaking_difficulty=0.95, safety_car_probability=0.60, dnf_rate=0.14),
    9: Circuit(9, "Barcelona-Catalunya", "Spain", TrackType.TECHNICAL, False,
               overtaking_difficulty=0.55, safety_car_probability=0.25, dnf_rate=0.08),
    10: Circuit(10, "Red Bull Ring", "Austria", TrackType.HIGH_SPEED, False,
                overtaking_difficulty=0.30, safety_car_probability=0.40, dnf_rate=0.14),
    11: Circuit(11, "Silverstone", "UK", TrackType.MIXED, True,
                overtaking_difficulty=0.40, safety_car_probability=0.35, dnf_rate=0.10),
    12: Circuit(12, "Spa-Francorchamps", "Belgium", TrackType.HIGH_SPEED, False,
                overtaking_difficulty=0.25, safety_car_probability=0.45, dnf_rate=0.14),
    13: Circuit(13, "Hungaroring", "Hungary", TrackType.TECHNICAL, False,
                overtaking_difficulty=0.75, safety_car_probability=0.25, dnf_rate=0.08),
    14: Circuit(14, "Zandvoort", "Netherlands", TrackType.TECHNICAL, True,
                overtaking_difficulty=0.70, safety_car_probability=0.35, dnf_rate=0.09),
    15: Circuit(15, "Monza", "Italy", TrackType.HIGH_SPEED, False,
                overtaking_difficulty=0.20, safety_car_probability=0.35, dnf_rate=0.12),
    16: Circuit(16, "Madrid", "Spain", TrackType.MIXED, False,
                overtaking_difficulty=0.40, safety_car_probability=0.40, dnf_rate=0.12),
    17: Circuit(17, "Baku", "Azerbaijan", TrackType.STREET, False,
                overtaking_difficulty=0.35, safety_car_probability=0.70, dnf_rate=0.20),
    18: Circuit(18, "Marina Bay", "Singapore", TrackType.STREET, True,
                overtaking_difficulty=0.60, safety_car_probability=0.70, dnf_rate=0.18),
    19: Circuit(19, "COTA", "USA", TrackType.MIXED, False,
                overtaking_difficulty=0.35, safety_car_probability=0.40, dnf_rate=0.11),
    20: Circuit(20, "Autodromo Hermanos Rodriguez", "Mexico", TrackType.MIXED, False,
                overtaking_difficulty=0.40, safety_car_probability=0.35, dnf_rate=0.10),
    21: Circuit(21, "Interlagos", "Brazil", TrackType.MIXED, False,
                overtaking_difficulty=0.30, safety_car_probability=0.55, dnf_rate=0.16),
    22: Circuit(22, "Las Vegas", "USA", TrackType.STREET, False,
                overtaking_difficulty=0.35, safety_car_probability=0.50, dnf_rate=0.15),
    23: Circuit(23, "Losail", "Qatar", TrackType.MIXED, False,
                overtaking_difficulty=0.40, safety_car_probability=0.30, dnf_rate=0.10),
    24: Circuit(24, "Yas Marina", "Abu Dhabi", TrackType.MIXED, False,
                overtaking_difficulty=0.40, safety_car_probability=0.25, dnf_rate=0.08),
}


def get_circuit(round_num: int) -> Circuit | None:
    return CIRCUITS_2026.get(round_num)


def track_type_similarity(type_a: TrackType, type_b: TrackType) -> float:
    """How similar two track types are (0.0 to 1.0). Used to weight historical performances."""
    if type_a == type_b:
        return 1.0

    # Similarity matrix
    similarity = {
        frozenset({TrackType.STREET, TrackType.TECHNICAL}): 0.5,    # Both favor precision
        frozenset({TrackType.HIGH_SPEED, TrackType.MIXED}): 0.6,    # Both have straights
        frozenset({TrackType.TECHNICAL, TrackType.MIXED}): 0.5,     # Some overlap
        frozenset({TrackType.STREET, TrackType.MIXED}): 0.3,        # Less similar
        frozenset({TrackType.STREET, TrackType.HIGH_SPEED}): 0.2,   # Opposite ends
        frozenset({TrackType.HIGH_SPEED, TrackType.TECHNICAL}): 0.3, # Different demands
    }

    return similarity.get(frozenset({type_a, type_b}), 0.3)


def get_similar_circuits(round_num: int) -> list[tuple[int, float]]:
    """Get other circuits similar to the given round, with similarity weights.

    Returns list of (round_number, similarity_weight) sorted by similarity.
    """
    target = get_circuit(round_num)
    if not target:
        return []

    similar = []
    for r, circuit in CIRCUITS_2026.items():
        if r == round_num:
            continue
        sim = track_type_similarity(target.track_type, circuit.track_type)
        similar.append((r, sim))

    return sorted(similar, key=lambda x: x[1], reverse=True)
