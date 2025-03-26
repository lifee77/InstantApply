import logging
from playwright.async_api import Page
import asyncio

logger = logging.getLogger(__name__)

async def review_form_entries(page: Page):
    """
    Reviews and logs what data has been entered in the form.
    
    Args:
        page: The Playwright page
    """
    logger.info("Reviewing form entries...")
    
    try:
        # Scroll through the page to show all filled fields
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        # Verify what was entered in each field
        all_inputs = await page.query_selector_all('input:not([type="file"]), textarea')
        for i, input_el in enumerate(all_inputs):
            try:
                name = await input_el.get_attribute('name') or ''
                placeholder = await input_el.get_attribute('placeholder') or ''
                id_attr = await input_el.get_attribute('id') or ''
                current_value = await input_el.input_value()
                
                if current_value:
                    field_name = name or placeholder or id_attr or f"field_{i+1}"
                    logger.info(f"Field '{field_name}' contains: '{current_value[:30]}{'...' if len(current_value) > 30 else ''}'")
            except Exception as e:
                logger.debug(f"Could not check field {i+1}: {str(e)}")
                
        # Log selected radio buttons
        radios = await page.query_selector_all('input[type="radio"]:checked')
        for radio in radios:
            try:
                name = await radio.get_attribute('name') or ''
                value = await radio.get_attribute('value') or ''
                
                # Try to get the label text
                label_text = await page.evaluate('''(radio) => {
                    const id = radio.id;
                    if (id) {
                        const label = document.querySelector(`label[for="${id}"]`);
                        return label ? label.textContent.trim() : "";
                    }
                    return "";
                }''', radio)
                
                logger.info(f"Radio '{name}' selected: '{value}' ({label_text})")
            except Exception as e:
                logger.debug(f"Could not check radio button: {str(e)}")
                
        # Log selected checkboxes
        checkboxes = await page.query_selector_all('input[type="checkbox"]:checked')
        for checkbox in checkboxes:
            try:
                name = await checkbox.get_attribute('name') or ''
                
                # Try to get the label text
                label_text = await page.evaluate('''(checkbox) => {
                    const id = checkbox.id;
                    if (id) {
                        const label = document.querySelector(`label[for="${id}"]`);
                        return label ? label.textContent.trim() : "";
                    }
                    return "";
                }''', checkbox)
                
                logger.info(f"Checkbox '{name}' checked: {label_text}")
            except Exception as e:
                logger.debug(f"Could not check checkbox: {str(e)}")
                
        return True
    except Exception as e:
        logger.error(f"Error reviewing form entries: {str(e)}")
        return False