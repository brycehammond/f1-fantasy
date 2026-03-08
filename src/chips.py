"""Chip usage strategy — decides when to deploy each chip for maximum impact."""

from dataclasses import dataclass


@dataclass
class ChipRecommendation:
    chip: str | None
    reason: str
    confidence: float  # 0.0 to 1.0


# Sprint weekends in 2026 (rounds with sprint races = more points available)
SPRINT_ROUNDS = {2, 6, 7, 11, 14, 18}

# Historically high-scoring circuits (lots of overtaking, DNFs, variability)
HIGH_VARIANCE_ROUNDS = {
    1,   # Australia (street-ish, safety cars)
    17,  # Azerbaijan (street circuit, chaos)
    18,  # Singapore (street circuit, safety cars)
    21,  # Brazil (weather, overtaking)
    22,  # Las Vegas (street, cold temps)
}


def recommend_chip(
    current_round: int,
    total_rounds: int,
    available_chips: list[str],
    transfers_needed: int,
    free_transfers: int,
    projected_gain_from_transfers: float,
    is_sprint_weekend: bool,
) -> ChipRecommendation:
    """Recommend which chip to play (if any) for the current round."""

    if not available_chips:
        return ChipRecommendation(chip=None, reason="No chips remaining", confidence=1.0)

    # --- Wildcard logic ---
    # Use wildcard when many transfers are needed but it's not worth paying penalties
    if "wildcard" in available_chips and transfers_needed > free_transfers + 1:
        extra_cost = (transfers_needed - free_transfers) * 10
        if extra_cost >= 20 and projected_gain_from_transfers > extra_cost:
            return ChipRecommendation(
                chip="wildcard",
                reason=f"Need {transfers_needed} transfers (saving {extra_cost} penalty points)",
                confidence=0.85,
            )

    # --- Limitless logic ---
    # Best on sprint weekends (more points available) or when expensive drivers are in form
    if "limitless" in available_chips and current_round >= 2:
        if is_sprint_weekend and current_round in HIGH_VARIANCE_ROUNDS:
            return ChipRecommendation(
                chip="limitless",
                reason=f"Sprint weekend + high-variance circuit (round {current_round})",
                confidence=0.8,
            )
        # Save limitless for a sprint weekend if one is coming soon
        if not is_sprint_weekend:
            upcoming_sprints = [r for r in SPRINT_ROUNDS if r > current_round]
            if upcoming_sprints and (upcoming_sprints[0] - current_round) <= 3:
                pass  # Don't use now, sprint coming soon

    # --- Extra DRS logic ---
    # Use when your top driver has a dominant track (e.g., Verstappen at circuits he dominates)
    # For now, save for sprint weekends where the 3x multiplier has more impact
    if "extra_drs" in available_chips and is_sprint_weekend:
        if current_round >= total_rounds * 0.4:  # Don't waste early
            return ChipRecommendation(
                chip="extra_drs",
                reason="Sprint weekend — 3x DRS boost on top driver for max points",
                confidence=0.7,
            )

    # --- No Negative logic ---
    # Best at high-variance circuits where DNFs are likely
    if "no_negative" in available_chips and current_round in HIGH_VARIANCE_ROUNDS:
        if current_round >= total_rounds * 0.3:
            return ChipRecommendation(
                chip="no_negative",
                reason=f"High-variance circuit (round {current_round}) — protect against DNFs",
                confidence=0.7,
            )

    # --- Autopilot logic ---
    # Good when you're unsure who will be fastest (e.g., new regs, variable conditions)
    if "autopilot" in available_chips:
        if current_round <= 3:  # Early season, hard to predict
            return ChipRecommendation(
                chip="autopilot",
                reason="Early season uncertainty — auto-pick best DRS boost",
                confidence=0.5,
            )

    # --- Final Fix logic ---
    # Save for when a driver has a qualifying crash or unexpected DNS
    # This is reactive, not proactive — best used in the automation's final check
    if "final_fix" in available_chips and current_round >= total_rounds * 0.7:
        # Late season, use it or lose it
        return ChipRecommendation(
            chip="final_fix",
            reason="Late season — Final Fix should be used before season ends",
            confidence=0.4,
        )

    # --- Don't use a chip if nothing is compelling ---
    # As season progresses, lower the bar for using remaining chips
    rounds_remaining = total_rounds - current_round
    if rounds_remaining <= len(available_chips):
        # Must start using chips — not enough races left
        # Pick the least impactful remaining chip
        priority = ["autopilot", "final_fix", "no_negative", "extra_drs", "wildcard", "limitless"]
        for chip in priority:
            if chip in available_chips:
                return ChipRecommendation(
                    chip=chip,
                    reason=f"Only {rounds_remaining} races left with {len(available_chips)} chips unused",
                    confidence=0.6,
                )

    return ChipRecommendation(
        chip=None,
        reason="No compelling reason to use a chip this round",
        confidence=0.7,
    )
