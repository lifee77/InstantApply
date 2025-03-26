import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

async def enable_test_mode(page: Page):
    """
    Enables test mode by preventing form submission and
    adding visual indicators to submit buttons.
    
    Args:
        page: The Playwright page
        
    Returns:
        bool: True if test mode was enabled
    """
    try:
        submit_buttons = await page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Apply")')
        
        if submit_buttons:
            logger.info(f"Found {len(submit_buttons)} submit buttons - enabling test mode")
            
            # Highlight the buttons to show we found them
            for i, button in enumerate(submit_buttons):
                await page.evaluate('''(button, index) => {
                    // Disable the button
                    button.disabled = true;
                    
                    // Style the button
                    button.style.border = '3px solid red';
                    button.style.position = 'relative';
                    
                    // Add a "TEST MODE" overlay
                    const overlay = document.createElement('div');
                    overlay.innerText = 'TEST MODE - NO SUBMIT';
                    overlay.style.position = 'absolute';
                    overlay.style.top = '0';
                    overlay.style.left = '0';
                    overlay.style.right = '0';
                    overlay.style.bottom = '0';
                    overlay.style.backgroundColor = 'rgba(255, 0, 0, 0.7)';
                    overlay.style.color = 'white';
                    overlay.style.display = 'flex';
                    overlay.style.alignItems = 'center';
                    overlay.style.justifyContent = 'center';
                    overlay.style.fontWeight = 'bold';
                    overlay.style.zIndex = '9999';
                    overlay.style.pointerEvents = 'none'; // Allow clicks to pass through
                    
                    // Make sure parent has relative position for absolute positioning
                    if (button.parentElement) {
                        button.parentElement.style.position = 'relative';
                        button.parentElement.appendChild(overlay);
                    }
                }''', button, i)
            
            # Also add a script to prevent form submission
            await page.add_script_tag({
                'content': '''
                document.addEventListener('submit', function(e) {
                    console.log('Form submission prevented by test mode');
                    e.preventDefault();
                    alert('Form submission prevented - TEST MODE');
                    return false;
                }, true);
                '''
            })
            
            logger.info("Test mode enabled - form submission prevented")
            return True
        
        logger.info("No submit buttons found to enable test mode")
        return False
    except Exception as e:
        logger.error(f"Error enabling test mode: {str(e)}")
        return False

async def disable_test_mode(page: Page):
    """
    Disables test mode by removing overlay and re-enabling submit buttons.
    
    Args:
        page: The Playwright page
        
    Returns:
        bool: True if test mode was disabled
    """
    try:
        await page.evaluate('''() => {
            // Re-enable submit buttons
            const buttons = document.querySelectorAll('button[type="submit"], input[type="submit"]');
            buttons.forEach(btn => {
                btn.disabled = false;
                btn.style.border = '';
            });
            
            // Remove TEST MODE overlays
            const overlays = document.querySelectorAll('div:contains("TEST MODE")');
            overlays.forEach(overlay => overlay.remove());
        }''')
        
        logger.info("Test mode disabled - form submission re-enabled")
        return True
    except Exception as e:
        logger.error(f"Error disabling test mode: {str(e)}")
        return False