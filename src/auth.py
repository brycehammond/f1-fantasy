"""Playwright-based authentication for F1 Fantasy."""

from playwright.async_api import async_playwright, BrowserContext, Page
from src.config import F1_EMAIL, F1_PASSWORD, FANTASY_BASE_URL, STATE_DIR


STORAGE_STATE_PATH = STATE_DIR / "auth_state.json"


async def create_browser_context(playwright) -> BrowserContext:
    """Create a browser context, reusing saved auth state if available."""
    browser = await playwright.chromium.launch(headless=False)

    if STORAGE_STATE_PATH.exists():
        context = await browser.new_context(storage_state=str(STORAGE_STATE_PATH))
    else:
        context = await browser.new_context()

    return context


async def login(page: Page) -> bool:
    """Log into F1 Fantasy. Returns True if login succeeded."""
    if not F1_EMAIL or not F1_PASSWORD:
        raise ValueError(
            "F1_FANTASY_EMAIL and F1_FANTASY_PASSWORD must be set in .env"
        )

    await page.goto(FANTASY_BASE_URL)
    await page.wait_for_load_state("networkidle")

    # Check if already logged in by looking for user menu or team page elements
    if await _is_logged_in(page):
        print("Already logged in (session restored)")
        return True

    # Click sign in / log in button
    sign_in_btn = page.locator("text=Sign In").first
    if await sign_in_btn.is_visible():
        await sign_in_btn.click()
        await page.wait_for_load_state("networkidle")

    # Fill login form — F1 uses a multi-step auth flow
    # Step 1: Email
    email_input = page.locator('input[type="email"], input[name="email"], input#email')
    await email_input.wait_for(state="visible", timeout=15000)
    await email_input.fill(F1_EMAIL)

    # Look for a "Next" or "Continue" button after email
    next_btn = page.locator('button:has-text("Next"), button:has-text("Continue"), button[type="submit"]').first
    await next_btn.click()
    await page.wait_for_timeout(2000)

    # Step 2: Password
    password_input = page.locator('input[type="password"], input[name="password"]')
    await password_input.wait_for(state="visible", timeout=15000)
    await password_input.fill(F1_PASSWORD)

    # Submit
    login_btn = page.locator('button:has-text("Log In"), button:has-text("Sign In"), button[type="submit"]').first
    await login_btn.click()

    # Wait for redirect back to fantasy site
    await page.wait_for_url(f"**fantasy.formula1.com**", timeout=30000)
    await page.wait_for_load_state("networkidle")

    if await _is_logged_in(page):
        # Save auth state for future runs
        await page.context.storage_state(path=str(STORAGE_STATE_PATH))
        print("Login successful, session saved")
        return True

    print("Login may have failed — could not confirm logged-in state")
    return False


async def _is_logged_in(page: Page) -> bool:
    """Check if we're currently logged in."""
    # Look for elements that only appear when logged in
    # The fantasy site shows "My Team" or user avatar when logged in
    indicators = [
        page.locator("text=My Team").first,
        page.locator('[data-testid="user-menu"]').first,
        page.locator('a[href*="my-team"]').first,
    ]
    for indicator in indicators:
        try:
            if await indicator.is_visible(timeout=3000):
                return True
        except Exception:
            continue
    return False
