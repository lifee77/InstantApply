import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

async def handle_visa_questions(page: Page):
    """
    Handles visa and work authorization questions by selecting appropriate options.
    
    Args:
        page: The Playwright page
        
    Returns:
        bool: True if any visa-related questions were answered
    """
    try:
        # Look for labels containing visa-related text
        visa_labels = await page.query_selector_all('label:has-text("visa"), label:has-text("Visa"), span:has-text("visa"), span:has-text("Visa"), label:has-text("authorized"), label:has-text("Authorized")')
        
        found_any = False
        for label in visa_labels:
            label_text = await label.inner_text()
            logger.info(f"Found visa-related question: '{label_text}'")
            
            # Find related radio buttons or regular buttons
            parent = label
            for _ in range(3):  # Go up to 3 levels to find container
                parent = await page.evaluate('(el) => el.parentElement', parent)
                if not parent:
                    break
                    
                # Look for radio inputs within this container
                radio_inputs = await page.query_selector_all('input[type="radio"]')
                if radio_inputs:
                    # Check if this is a work authorization or visa sponsorship question
                    needs_visa = "sponsorship" in label_text.lower() or ("visa" in label_text.lower() and "need" in label_text.lower())
                    
                    target_value = "no" if needs_visa else "yes"
                    for radio in radio_inputs:
                        value = await radio.get_attribute('value') or ''
                        if value.lower() in [target_value]:
                            await radio.check()
                            logger.info(f"✅ Selected '{target_value}' for visa question")
                            found_any = True
                            break
                    break
                
                # Look for yes/no buttons
                buttons = await page.query_selector_all('button, .btn')
                for button in buttons:
                    button_text = await button.inner_text()
                    if button_text.lower() == ("no" if "sponsorship" in label_text.lower() else "yes"):
                        await button.click()
                        logger.info(f"✅ Clicked '{button_text}' button for visa question")
                        found_any = True
                        break
        
        return found_any
    except Exception as e:
        logger.error(f"Error handling visa questions: {str(e)}")
        return False

async def handle_radio_groups(page: Page):
    """
    Maps and handles radio button groups based on question context.
    
    Args:
        page: The Playwright page
    
    Returns:
        bool: True if any radio groups were handled
    """
    try:
        # Find all radio groups by looking for multiple radio buttons with the same name
        radio_groups = {}
        all_radios = await page.query_selector_all('input[type="radio"]')
        
        for radio in all_radios:
            name = await radio.get_attribute('name')
            if name:
                if name not in radio_groups:
                    radio_groups[name] = []
                radio_groups[name].append(radio)
        
        # Process each group
        handled_any = False
        for name, radios in radio_groups.items():
            if not radios:
                continue
                
            # Try to identify what kind of question this is
            parent_text = await page.evaluate('''(radio) => {
                let el = radio;
                for (let i = 0; i < 5; i++) {
                    el = el.parentElement;
                    if (!el) break;
                    if (el.textContent) return el.textContent.trim();
                }
                return "";
            }''', radios[0])
            
            logger.info(f"Found radio group '{name}' with question: '{parent_text[:50]}...'")
            
            # Logic for selecting appropriate radio option based on question text
            if "visa" in parent_text.lower() or "authorized" in parent_text.lower() or "sponsorship" in parent_text.lower():
                # For visa/authorization questions, select "yes" to work authorization or "no" to needing visa
                if "authorized" in parent_text.lower() or "legally" in parent_text.lower():
                    # Select "Yes" for "Are you authorized to work?"
                    target_value = "yes"
                else:
                    # Select "No" for "Do you need a visa?"
                    target_value = "no"
                    
                selected = False
                for radio in radios:
                    value = await radio.get_attribute('value') or ''
                    label_text = await page.evaluate('''(radio) => {
                        const id = radio.id;
                        if (id) {
                            const label = document.querySelector(`label[for="${id}"]`);
                            return label ? label.textContent.trim() : "";
                        }
                        return "";
                    }''', radio)
                    
                    if (value.lower() == target_value or 
                        label_text.lower() == target_value):
                        await radio.check()
                        logger.info(f"✅ Selected '{target_value}' for question: '{parent_text[:30]}...'")
                        selected = True
                        handled_any = True
                        break
                
                if not selected and radios:
                    # If we couldn't match by value/label, just pick the first one
                    await radios[0].check()
                    logger.info(f"✅ Selected first option for '{parent_text[:30]}...' (fallback)")
                    handled_any = True
            elif "relocate" in parent_text.lower() or "relocation" in parent_text.lower():
                # For relocation questions, select "Yes"
                target_value = "yes"
                selected = False
                for radio in radios:
                    value = await radio.get_attribute('value') or ''
                    label_text = await page.evaluate('''(radio) => {
                        const id = radio.id;
                        if (id) {
                            const label = document.querySelector(`label[for="${id}"]`);
                            return label ? label.textContent.trim() : "";
                        }
                        return "";
                    }''', radio)
                    
                    if (value.lower() == target_value or 
                        label_text.lower() == target_value):
                        await radio.check()
                        logger.info(f"✅ Selected '{target_value}' for relocation question")
                        selected = True
                        handled_any = True
                        break
                
                if not selected and radios:
                    await radios[0].check()
                    logger.info(f"✅ Selected first option for relocation question (fallback)")
                    handled_any = True
            else:
                # For other radio groups, just select the first option
                await radios[0].check()
                logger.info(f"✅ Selected first option for radio group '{name}'")
                handled_any = True
                
        return handled_any
    except Exception as e:
        logger.error(f"Error handling radio button groups: {str(e)}")
        return False