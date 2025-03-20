import asyncio
import logging

logger = logging.getLogger(__name__)

async def scroll_and_click(page_or_frame, selector, max_scrolls=5):
    for _ in range(max_scrolls):
        element = await page_or_frame.query_selector(selector)
        if element and await element.is_visible():
            await page_or_frame.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})", element)
            await asyncio.sleep(0.5)
            await element.click()
            logger.info(f"✅ Clicked (after scroll): {selector}")
            return True
        await page_or_frame.evaluate("window.scrollBy(0, window.innerHeight / 2)")
        await asyncio.sleep(0.5)
    return False

async def scroll_and_click_dropdowns_and_modals(page_or_frame, max_scrolls=5):
    selectors = [
        'button:has-text("Continue")',
        'button:has-text("Next")',
        'button:has-text("OK")',
        'button:has-text("Close")',
        'button:has-text("Save and continue")',
        'button:has-text("Submit application")',
        'button:has-text("Send application")',
        'button:has-text("Finish")',
        'button:has-text("Review")',
        'button:has-text("Complete")',
        'button:has-text("Done")',
        'button:has-text("Confirm")',
        'button:has-text("Proceed")'
    ]
    for _ in range(max_scrolls):
        for selector in selectors:
            element = await page_or_frame.query_selector(selector)
            if element and await element.is_visible():
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await element.click()
                logger.info(f"✅ Clicked dropdown/modal button: {selector}")
                return True
        await page_or_frame.evaluate("window.scrollBy(0, window.innerHeight / 2)")
        await asyncio.sleep(0.5)
    return False


async def click_accept_or_apply_buttons(page_or_frame):
    """
    Attempts to click common consent or apply buttons if found on the page.

    Args:
        page: The Playwright page object.
    """
    try:
        selectors = [
            # Accept/Consent buttons
            'button:has-text("Accept")',
            'button:has-text("I accept")',
            'button:has-text("I Agree")',
            'button:has-text("Agree")',
            'button:has-text("Accept all")',
            'button:has-text("Accept and continue")',
            'button:has-text("Accept cookies")',
            'button:has-text("Consent")',
            'button:has-text("Continue with Accept")',
            'a:has-text("Accept")',
            'a:has-text("I accept")',
            'a:has-text("I Agree")',
            'a:has-text("Agree")',
            'a:has-text("Accept all")',
            'a:has-text("Accept and continue")',
            'a:has-text("Accept cookies")',
            'a:has-text("Consent")',
            'a:has-text("Continue with Accept")',
            'input[type="checkbox"][name*="terms"], input[type="checkbox"][id*="terms"]',

            # Apply buttons (pre-form opening) - updated selectors
            'button:has-text("Apply")',
            'button:has-text("Apply Now")',
            'button:has-text("Apply →")',
            'button:has-text("Apply→")',
            'a:has-text("Apply")',
            'a:has-text("Apply Now")',
            'a:has-text("Apply →")',
            'a:has-text("Apply→")',
            'button:has-text("Apply") i',
            'button span:has-text("Apply")',
            'a span:has-text("Apply")',
            'button[aria-label*="Apply"]',
            'button[title*="Apply"]'
        ]

        clicked = False
        for selector in selectors:
            element = await page_or_frame.query_selector(selector)
            if element:
                await page_or_frame.evaluate("el => el.scrollIntoView({behavior: 'smooth', block: 'center'})", element)
                element_type = await element.get_attribute("type")
            if element_type == "checkbox":
                await element.check()
                logger.info(f"✅ Checked checkbox: {selector}")
                clicked = True
            else:
                did_click = await scroll_and_click(page_or_frame, selector)
                if did_click:
                    clicked = True

        # Recursive search in popups (new pages)
        if hasattr(page_or_frame, "context"):
            for popup in page_or_frame.context.pages:
                if popup != page_or_frame:
                    logger.info("🔍 Found popup window. Searching for apply/accept buttons in popup.")
                    await click_accept_or_apply_buttons(popup)

        # Recursive search in iframes
        if hasattr(page_or_frame, "frames"):
            for frame in page_or_frame.frames:
                if frame != page_or_frame.main_frame:
                    logger.info("🔍 Found iframe. Searching for apply/accept buttons in iframe.")
                    await click_accept_or_apply_buttons(frame)

        if not clicked:
            logger.info("No accept or apply buttons found.")
        return clicked

    except Exception as e:
        logger.error(f"❌ Error in click_accept_or_apply_buttons: {str(e)}")
        return False