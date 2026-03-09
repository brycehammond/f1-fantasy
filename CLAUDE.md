# F1 Fantasy Automation

## Overview
Automated F1 Fantasy team management for https://fantasy.formula1.com/en/
Two-step flow: gather data, Claude analyzes and recommends. User applies changes manually on the site.

## Quick Start
When the user says "run the F1 Fantasy flow", "update my F1 team", or similar:
1. Run `python scripts/gather.py` (activates venv: `source .venv/bin/activate`)
2. Run `python scripts/analyze.py`
3. Read `data/state.json` and `data/algorithm_lineup.json`
4. Research the upcoming race (web search for practice pace, weather, news, penalties, upgrades)
5. Write your recommendation to `data/claude_lineup.json` with reasoning on every pick
6. Present both lineups (algorithm + Claude) to the user with reasoning for each pick

## Credentials
Set in `.env` (copy from `.env.example`). Contains F1 Fantasy email/password.
Never committed to git. Required for gather.py to log in via Playwright.

## Workflow

### Step 1: Gather + Algorithm (`python scripts/gather.py && python scripts/analyze.py`)
- `gather.py` — logs into F1 Fantasy via Playwright, fetches all driver/constructor prices, your current team, budget, chips, scoring history. Saves to `data/state.json` + screenshot.
- `analyze.py` — runs the predictive algorithm on gathered data. Projects points using historical form, circuit-type similarity, qualifying pace, team strength, and PPM value metrics. Outputs optimal team to `data/algorithm_lineup.json`.

### Step 2: Claude Code analyzes and decides
Read these files:
1. `data/state.json` — your current team, all prices, budget, chips, history
2. `data/algorithm_lineup.json` — the algorithm's recommended team with projections
3. `data/my_team_screenshot.png` — visual of current team page

**CRITICAL CONSTRAINT — TRANSFER LIMITS:**
Check `my_team.free_transfers` in state.json. You MUST respect this limit:
- Your lineup can only differ from the current team by that many players (drivers + constructors combined)
- Each change beyond the free transfer limit costs -10 points penalty
- Only recommend more transfers than the free limit if the projected gain clearly exceeds the penalty
- If you want a drastically different team, recommend using the Wildcard chip (if available)
- The algorithm_lineup.json includes both a transfer-constrained pick and a "dream_team" for reference
- Always state how many transfers your recommendation uses and whether any incur penalties

Then:
1. **Review the algorithm's pick** — it's a useful quantitative baseline, but it can't account for qualitative factors
2. **Research the upcoming race** — search the web for:
   - Recent practice/qualifying pace and lap times
   - Weather forecasts for the race weekend
   - Breaking news: injuries, grid penalties, car upgrades, parts changes
   - Team orders, contract situations, motivation factors
   - Track-specific history and form
   - Expert predictions and community consensus
3. **Synthesize a recommendation** — agree with, modify, or override the algorithm. Explain *why* for each pick, especially where you diverge from the algorithm. Your recommendation must be reachable within the transfer limit (or explicitly recommend a chip to bypass it).
4. **Write `data/claude_lineup.json`** in this format:

```json
{
    "source": "claude",
    "target_round": 2,
    "circuit": "Shanghai",
    "team": {
        "drivers": [
            {"name": "George Russell", "price": 27.4, "reasoning": "Dominant in Round 1, Mercedes clearly has the best car under new regs. Shanghai is mixed layout which suits the Merc."},
            {"name": "Kimi Antonelli", "price": 23.2, "reasoning": "Impressive debut, P2 at Melbourne. Great PPM value at his price."}
        ],
        "constructors": [
            {"name": "Mercedes", "price": 29.3, "reasoning": "Clear #1 after Round 1. Both drivers in top 2, pitstop bonus likely."}
        ]
    },
    "drs_boost": "George Russell",
    "drs_reasoning": "Highest ceiling of any driver, on a track with DRS zones that suit Mercedes' straight-line speed.",
    "chip": null,
    "chip_reasoning": "Round 2 is too early — save chips for higher-leverage rounds.",
    "transfers": [
        {"out": "Max Verstappen", "in": "Kimi Antonelli", "reasoning": "Red Bull car looks weak in new regs. Verstappen's price will drop. Antonelli is cheaper and scored nearly as well."}
    ],
    "transfer_penalty": 0,
    "total_cost": 95.2,
    "projected_points": null,
    "reasoning": "Mercedes is the clear top team after Round 1. Loading up on Mercedes assets while they're dominant. Dropping Verstappen to free budget for value mid-field picks."
}
```

Key fields:
- Every driver, constructor, transfer, DRS choice, and chip decision has a `reasoning` field
- `projected_points` can be null — Claude's value is qualitative judgment, not a number
- The overall `reasoning` field explains the high-level strategy

### Step 3: User applies manually
The user applies the chosen lineup on https://fantasy.formula1.com/en/ themselves.

## Full Workflow Example
```bash
# 1. Gather all data from F1 Fantasy (opens browser, logs in)
python scripts/gather.py

# 2. Run predictive algorithm
python scripts/analyze.py

# 3. Ask Claude to analyze (in Claude Code conversation):
#    "Read data/state.json and data/algorithm_lineup.json.
#     Research the upcoming race and write your recommendation
#     to data/claude_lineup.json"

# 4. User applies chosen lineup manually on the F1 Fantasy site
```

## Project Structure
```
f1-fantasy/
├── CLAUDE.md
├── .env                     # F1 Fantasy credentials (gitignored)
├── .env.example
├── .gitignore
├── requirements.txt
├── scripts/
│   ├── gather.py            # Collect all data from F1 Fantasy
│   └── analyze.py           # Run predictive algorithm
├── src/
│   ├── config.py            # Settings, URLs, credentials
│   ├── auth.py              # Playwright login helpers
│   ├── api.py               # Public API client
│   ├── scraper.py           # Browser data extraction
│   ├── projections.py       # Multi-signal projection engine
│   ├── circuits.py          # Circuit classification and track types
│   ├── season_data.py       # Seed data from completed races
│   ├── optimizer.py         # Brute-force team optimizer
│   ├── chips.py             # Chip strategy heuristics
│   └── main.py              # Legacy standalone orchestrator
├── data/
│   ├── state.json           # Gathered state (Step 1)
│   ├── algorithm_lineup.json # Algorithm recommendation (Step 1)
│   ├── claude_lineup.json   # Claude recommendation (Step 2)
│   ├── my_team_screenshot.png
│   └── history/             # Timestamped state snapshots
└── tests/
    ├── test_optimizer.py
    └── test_projections.py
```

## Game Rules (2026 Season)
- **Team**: 5 drivers + 2 constructors, $100M budget cap
- **Transfers**: 2 free per race (carry over max 1), -10 pts per extra transfer
- **Transfer calc**: Net-based — reversals don't count
- **DRS Boost**: Select 1 driver for 2x points
- **Team lock**: Before qualifying (Friday/Saturday)
- **Chips** (each once/season, max 1 per race):
  - **Wildcard** — unlimited free transfers within budget
  - **Limitless** — unlimited transfers, no budget cap (reverts next race). From Round 2
  - **Extra DRS** — 3x points on DRS boost driver (instead of 2x)
  - **Autopilot** — auto-assigns DRS boost to highest scorer post-race
  - **No Negative** — all negative points zeroed (DNFs, lost positions, penalties)
  - **Final Fix** — replace 1 driver after transfer deadline before race start
- **Sprint rounds (2026)**: 2, 6, 7, 11, 14, 18 (~30% more points available)
- **11 teams, 22 drivers** (Cadillac is new for 2026)

## Scoring Quick Reference
- **Qualifying**: P1=10, P2=9, P3-P10=8→1, P11+=0, no time=-5, DSQ=-15
- **Race**: P1=25, P2=18, ..., P10=1; +1/position gained, -1/lost; +1/overtake; fastest lap=+10; DOTD=+10; DNF=-20
- **Sprint**: P1=8, ..., P8=1; ±1/position; +1/overtake; fastest lap=+5; DNF=-10
- **Constructor**: combined driver race points + qualifying bonuses (both Q3=+10, one Q3=+3) + pitstop bonuses (sub-2.0s=+10)

## Tech Stack
- Python 3.12+, Playwright (chromium), httpx, python-dotenv
- `playwright install chromium` needed after pip install
