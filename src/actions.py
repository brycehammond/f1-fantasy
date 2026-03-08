"""Browser actions — make transfers, activate chips, set DRS boost via Playwright."""

from playwright.async_api import Page

from src.config import FANTASY_BASE_URL


async def make_transfers(page: Page, transfers: list[tuple[dict, dict]]) -> bool:
    """Execute transfers on the F1 Fantasy website.

    Args:
        transfers: List of (player_out, player_in) pairs.
                   Each dict has at minimum a 'name' key.
    """
    if not transfers:
        print("No transfers to make")
        return True

    await page.goto(f"{FANTASY_BASE_URL}my-team", wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # Click "Transfers" or "Edit Team" button
    edit_btn = page.locator(
        'button:has-text("Transfers"), button:has-text("Edit Team"), '
        'a:has-text("Transfers"), a:has-text("Edit")'
    ).first
    await edit_btn.click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    for player_out, player_in in transfers:
        out_name = player_out.get("name", player_out.get("display_name", ""))
        in_name = player_in.get("name", player_in.get("display_name", ""))

        print(f"Transfer: {out_name} → {in_name}")

        # Click on the player to remove
        player_card = page.locator(f'text="{out_name}"').first
        await player_card.click()
        await page.wait_for_timeout(1000)

        # In the replacement picker, search for and select the new player
        search_input = page.locator(
            'input[placeholder*="Search"], input[type="search"], input[class*="search"]'
        ).first
        if await search_input.is_visible(timeout=5000):
            await search_input.fill(in_name)
            await page.wait_for_timeout(1500)

        # Click the replacement player
        replacement = page.locator(f'text="{in_name}"').first
        await replacement.click()
        await page.wait_for_timeout(1000)

    # Confirm transfers
    confirm_btn = page.locator(
        'button:has-text("Confirm"), button:has-text("Save"), '
        'button:has-text("Apply"), button:has-text("Submit")'
    ).first
    if await confirm_btn.is_visible(timeout=5000):
        await confirm_btn.click()
        await page.wait_for_timeout(3000)
        print("Transfers confirmed")
        return True

    print("Could not find confirm button — transfers may not have been saved")
    return False


async def set_drs_boost(page: Page, driver_name: str) -> bool:
    """Set the DRS boost on the specified driver."""
    await page.goto(f"{FANTASY_BASE_URL}my-team", wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # Look for DRS boost button/section
    drs_section = page.locator('[class*="drs"], [class*="DRS"], text="DRS"').first
    try:
        if await drs_section.is_visible(timeout=5000):
            await drs_section.click()
            await page.wait_for_timeout(1000)
    except Exception:
        pass

    # Select the driver for DRS boost
    driver_option = page.locator(f'text="{driver_name}"').first
    await driver_option.click()
    await page.wait_for_timeout(1000)

    # Confirm
    confirm = page.locator(
        'button:has-text("Confirm"), button:has-text("Save"), button:has-text("Apply")'
    ).first
    if await confirm.is_visible(timeout=5000):
        await confirm.click()
        print(f"DRS boost set on {driver_name}")
        return True

    print(f"Could not confirm DRS boost on {driver_name}")
    return False


async def activate_chip(page: Page, chip_name: str) -> bool:
    """Activate a chip/booster for the current race."""
    await page.goto(f"{FANTASY_BASE_URL}my-team", wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # Navigate to chips/boosters section
    chips_btn = page.locator(
        'button:has-text("Chips"), button:has-text("Boosters"), '
        'a:has-text("Chips"), a:has-text("Boosters"), '
        '[class*="chip"], [class*="booster"]'
    ).first

    try:
        if await chips_btn.is_visible(timeout=5000):
            await chips_btn.click()
            await page.wait_for_timeout(1500)
    except Exception:
        pass

    # Chip names as they might appear on the site
    chip_display_names = {
        "wildcard": "Wildcard",
        "limitless": "Limitless",
        "extra_drs": "Extra DRS",
        "autopilot": "Autopilot",
        "no_negative": "No Negative",
        "final_fix": "Final Fix",
    }

    display_name = chip_display_names.get(chip_name, chip_name)

    # Click the chip
    chip_el = page.locator(f'text="{display_name}"').first
    await chip_el.click()
    await page.wait_for_timeout(1000)

    # Activate / confirm
    activate_btn = page.locator(
        'button:has-text("Activate"), button:has-text("Use"), '
        'button:has-text("Confirm"), button:has-text("Play")'
    ).first
    if await activate_btn.is_visible(timeout=5000):
        await activate_btn.click()
        await page.wait_for_timeout(2000)
        print(f"Chip '{display_name}' activated")
        return True

    print(f"Could not activate chip '{display_name}'")
    return False
