import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
STATE_DIR = PROJECT_ROOT / "playwright-state"
STATE_DIR.mkdir(exist_ok=True)

# Credentials
F1_EMAIL = os.getenv("F1_FANTASY_EMAIL", "")
F1_PASSWORD = os.getenv("F1_FANTASY_PASSWORD", "")

# URLs
FANTASY_BASE_URL = "https://fantasy.formula1.com/en/"
API_BASE_URL = "https://fantasy-api.formula1.com/f1/2026"

# Game rules
SEASON_YEAR = 2026
BUDGET_CAP = 100.0  # $100M
MAX_DRIVERS = 5
MAX_CONSTRUCTORS = 2
FREE_TRANSFERS_PER_RACE = 2
MAX_CARRY_OVER_TRANSFERS = 1
EXTRA_TRANSFER_PENALTY = -10

# Chips (each usable once per season)
CHIPS = [
    "wildcard",       # Unlimited free transfers within budget
    "limitless",      # Unlimited transfers, no budget cap (reverts next week). Available from Round 2
    "extra_drs",      # Triple points on DRS boost driver (3x instead of 2x)
    "autopilot",      # Auto-assigns DRS boost to highest scorer after race
    "no_negative",    # All negative points set to zero
    "final_fix",      # Replace one driver after transfer deadline
]
