"""Public F1 Fantasy API client for fetching driver/constructor data."""

import json
from pathlib import Path
from datetime import datetime

import httpx

from src.config import API_BASE_URL, DATA_DIR


async def get_players() -> list[dict]:
    """Fetch all drivers with current prices and IDs."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE_URL}/players")
        resp.raise_for_status()
        data = resp.json()

    # Cache response
    _cache("players", data)
    return data.get("players", data)


async def get_constructors() -> list[dict]:
    """Fetch all constructors with current prices and IDs."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE_URL}/teams")
        resp.raise_for_status()
        data = resp.json()

    _cache("teams", data)
    return data.get("teams", data)


async def get_season_info() -> dict:
    """Fetch season/fixture info from the root endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE_URL}/")
        resp.raise_for_status()
        data = resp.json()

    _cache("season_info", data)
    return data


async def get_player_scores(player_id: int) -> dict:
    """Fetch scoring history for a specific driver."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE_URL}/players/{player_id}/game_periods_scores",
            params={"season_name": "2026"},
        )
        resp.raise_for_status()
        return resp.json()


def _cache(name: str, data: dict):
    """Cache API response to disk with timestamp."""
    cache_file = DATA_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    cache_file.write_text(json.dumps(data, indent=2))

    # Also write a "latest" symlink-style file
    latest = DATA_DIR / f"{name}_latest.json"
    latest.write_text(json.dumps(data, indent=2))
