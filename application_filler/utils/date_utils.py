import logging
import asyncio
from playwright.async_api import Page

logger = logging.getLogger(__name__)

async def handle_date_picker(page: Page, target_date: str = "2025-03-25"):
    """
    Handles various types of date picker inputs.
    
    Args:
        page: The Playwright page
        target_date: Date string in YYYY-MM-DD format (default: March 25, 2025)
    
    Returns:
        bool: True if any date picker was successfully handled
    """
    # Extract date parts for easier matching
    year, month, day = target_date.split('-')
    month_int = int(month)
    month_names = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
    month_name = month_names[month_int - 1]
    
    try:
        # Approach 1: Find date fields by labels
        date_labels = await page.query_selector_all('label:has-text("start date"), label:has-text("Start date"), span:has-text("start date"), div:has-text("When can you start")')
        
        for label in date_labels:
            logger.info(f"Found a start date question element")
            
            # Try to find related input fields
            parent = label
            for _ in range(3):  # Go up to 3 levels to find container
                parent = await page.evaluate('(el) => el.parentElement', parent)
                if not parent:
                    break
                    
                # Look for input fields within this container
                container_inputs = await page.evaluate('''(container) => {
                    const inputs = container.querySelectorAll('input, textarea, [contenteditable="true"]');
                    return Array.from(inputs).map(el => el.id || el.name || '');
                }''', parent)
                
                if container_inputs:
                    logger.info(f"Found input elements related to date: {container_inputs}")
                    # Try to find and fill each input
                    for input_id in container_inputs:
                        if not input_id:
                            continue
                            
                        input_el = await page.query_selector(f'#{input_id}')
                        if input_el:
                            await input_el.fill(target_date)
                            logger.info(f"✅ Filled start date field with: '{target_date}'")
                            return True
        
        # Approach 2: Find date picker components
        date_pickers = await page.query_selector_all('div[role="calendar"], [data-testid="datepicker"], .calendar-input, .date-picker')
        
        if date_pickers:
            logger.info(f"Found {len(date_pickers)} potential date picker elements")
            for i, picker in enumerate(date_pickers):
                if await picker.is_visible():
                    logger.info(f"Attempting to interact with date picker {i+1}")
                    await picker.click()
                    await asyncio.sleep(1)  # Wait for calendar to appear
                    
                    # Try to select a specific date
                    try:
                        # Click the month/year selector if available
                        month_selectors = await page.query_selector_all('[class*="month-select"], [class*="year-select"], [aria-label*="month"], button:has-text("March")')
                        if month_selectors:
                            await month_selectors[0].click()
                            await asyncio.sleep(0.5)
                            
                            # Try to click on target month/year
                            month_option = await page.query_selector(f'option:has-text("{month_name}"), div:has-text("{month_name} {year}")')
                            if month_option:
                                await month_option.click()
                                await asyncio.sleep(0.5)
                                
                                # Now try to find the day
                                day_element = await page.query_selector(f'td:has-text("{int(day)}"), div:has-text("{int(day)}")')
                                if day_element:
                                    await day_element.click()
                                    logger.info(f"✅ Selected {month_name} {day}, {year} in date picker")
                                    return True
                    except Exception as e:
                        logger.warning(f"Error navigating date picker: {str(e)}")
                    
                    # Fallback - just select any available day
                    day_cells = await page.query_selector_all('.calendar-day, .day, [role="gridcell"]')
                    if day_cells:
                        # Find a selectable day (not disabled)
                        for day_cell in day_cells:
                            if await day_cell.is_visible() and not (await day_cell.get_attribute('disabled')):
                                await day_cell.click()
                                logger.info(f"✅ Selected a date in date picker {i+1} (fallback)")
                                return True
    except Exception as e:
        logger.error(f"Error handling date pickers: {str(e)}")
    
    return False