"""
Browser manager module for handling browser initialization and configuration
"""
import os
import asyncio
import logging
import platform
import subprocess
from typing import Dict, Any, Tuple, Optional

from playwright.async_api import async_playwright, Playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Browser Manager class for handling browser initialization and configuration
    Designed to handle browser crashes and provide a stable browser environment
    """
    
    def __init__(self):
        """Initialize the browser manager"""
        self.browser_type = self._determine_best_browser()
        self.browser_args = self._get_browser_args()
        self.browser_prefs = self._get_browser_prefs()
        self.playwright = None
        self.browser = None
        self.context = None
    
    def _determine_best_browser(self) -> str:
        """
        Determine the best browser to use based on the platform
        
        Returns:
            str: Browser type to use ('chromium', 'firefox', or 'webkit')
        """
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            # On macOS, Firefox tends to be more stable for automation
            return 'firefox'
        elif system == 'Windows':
            # Windows typically works best with Chromium
            return 'chromium'
        else:
            # Linux and other systems tend to work well with Firefox
            return 'firefox'

    def _get_browser_args(self) -> Dict[str, list]:
        """
        Get browser-specific arguments
        
        Returns:
            Dict with browser arguments for each browser type
        """
        return {
            'chromium': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-infobars',
                '--window-size=1280,720',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process,NetworkService,NetworkServiceInProcess',
                '--allow-running-insecure-content',
                '--disable-blink-features=AutomationControlled',
            ],
            'firefox': [
                '-width=1280', 
                '-height=720',
                '--disable-extensions',
                '--disable-infobars',
            ],
            'webkit': [
                # WebKit-specific arguments
            ]
        }
    
    def _get_browser_prefs(self) -> Dict[str, Dict]:
        """
        Get browser-specific preferences
        
        Returns:
            Dict with browser preferences for each browser type
        """
        return {
            'chromium': {},
            'firefox': {
                'media.navigator.permission.disabled': True,
                'permissions.default.image': 2,
                'browser.cache.disk.enable': False,
                'browser.cache.memory.enable': False,
                'network.http.pipelining': True,
                'network.http.proxy.pipelining': True,
            },
            'webkit': {}
        }
    
    async def _pre_launch_checks(self):
        """Run system checks before launching browser"""
        try:
            # Check for sufficient memory
            if platform.system() == 'Darwin':  # macOS
                # Get available memory on macOS using vm_stat
                vm_stat = subprocess.check_output(['vm_stat']).decode('utf-8')
                for line in vm_stat.splitlines():
                    if 'Pages free' in line:
                        free_pages = int(line.split(':')[1].strip().strip('.'))
                        # Convert pages to MB (page size is 4096 bytes on macOS)
                        free_mb = free_pages * 4096 / 1024 / 1024
                        if free_mb < 500:  # If less than 500MB free
                            logger.warning(f"Low memory available: {free_mb:.2f}MB. Browser may be unstable.")
                        break
            
            # Clear playwright browser cache if exists
            cache_path = os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright')
            if os.path.exists(cache_path):
                logger.info(f"Found Playwright cache at {cache_path}")
        except Exception as e:
            logger.warning(f"Error during pre-launch checks: {str(e)}")

    async def _configure_context(self, context: BrowserContext):
        """Configure browser context with event listeners and settings"""
        # Set up console message logging
        context.on("console", lambda msg: self._log_console_message(msg))
        
        # Set up page error logging
        context.on("page", lambda page: page.on("pageerror", lambda err: 
            logger.error(f"Page error: {err}")))
        
        # Setup default timeout
        context.set_default_timeout(60000)  # 60 seconds
        
        # Setup default navigation timeout
        context.set_default_navigation_timeout(90000)  # 90 seconds

    def _log_console_message(self, msg):
        """Log console messages with appropriate level"""
        text = msg.text if hasattr(msg, 'text') else str(msg)
        msg_type = msg.type if hasattr(msg, 'type') else "info"
        
        if msg_type in ["error", "warning"]:
            logger.warning(f"Browser console {msg_type}: {text}")
        else:
            logger.debug(f"Browser console: {text}")

    async def _setup_page_handlers(self, page: Page):
        """Set up page-specific handlers and settings"""
        # Block unnecessary resources to improve performance
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,otf,eot}", 
            lambda route: route.abort())
        
        # Block tracking and analytics scripts
        await page.route("**/(analytics|tracking|gtm|tagmanager|facebook|google-analytics|hotjar)",
            lambda route: route.abort())
        
        # Emulate desktop device
        await page.emulate_media(media="screen")
        
        # Set viewport size
        await page.set_viewport_size({"width": 1280, "height": 720})
        
        # Set default timeout
        page.set_default_timeout(60000)
        
        # Set default navigation timeout
        page.set_default_navigation_timeout(90000)

    async def create_browser(self) -> Tuple[Browser, BrowserContext, Page]:
        """
        Create a new browser instance with optimal settings for form filling
        
        Returns:
            Tuple with browser, context and page objects
        """
        # Set environment variables to prevent browser crashes
        os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "0"
        
        try:
            # Run pre-launch checks
            await self._pre_launch_checks()
            
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            
            # Get browser engine based on platform
            browser_engine = getattr(self.playwright, self.browser_type)
            
            # Launch browser with appropriate arguments - ALWAYS use headful mode for stability
            self.browser = await browser_engine.launch(
                headless=False,  # Always use headful mode for better stability with forms
                slow_mo=100,     # Add delay between actions for stability
                args=self.browser_args[self.browser_type],
                firefox_user_prefs=self.browser_prefs['firefox'] if self.browser_type == 'firefox' else None,
                timeout=120000   # 2 minute timeout for browser launch
            )
            
            # Create browser context
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=self._get_user_agent(),
                locale="en-US",
                timezone_id="America/Los_Angeles",
                ignore_https_errors=True  # Ignore SSL errors
            )
            
            # Configure context
            await self._configure_context(self.context)
            
            # Create page
            page = await self.context.new_page()
            
            # Set up page handlers
            await self._setup_page_handlers(page)
            
            logger.info(f"Successfully initialized {self.browser_type} browser in visible (non-headless) mode")
            return self.browser, self.context, page
            
        except Exception as e:
            logger.error(f"Failed to create browser: {str(e)}")
            await self.cleanup()
            raise
    
    def _get_user_agent(self) -> str:
        """
        Get appropriate user agent string based on browser and platform
        
        Returns:
            User agent string
        """
        if self.browser_type == 'chromium':
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.94 Safari/537.36"
        elif self.browser_type == 'firefox':
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0"
        else:  # webkit
            return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    
    async def navigate_with_retry(self, page: Page, url: str, max_retries: int = 3) -> bool:
        """
        Navigate to a URL with retry mechanism
        
        Args:
            page: Playwright page object
            url: URL to navigate to
            max_retries: Maximum number of retry attempts
        
        Returns:
            bool: True if navigation succeeded, False otherwise
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_retries})")
                
                response = await page.goto(
                    url, 
                    timeout=90000,  # 90 seconds
                    wait_until="domcontentloaded"
                )
                
                # Wait for network to be mostly idle
                try:
                    await page.wait_for_load_state("networkidle", timeout=30000)
                except Exception as e:
                    logger.warning(f"Network didn't become idle, but continuing: {str(e)}")
                
                # Additional wait for stability
                await asyncio.sleep(2)
                
                if response and response.status < 400:
                    logger.info(f"Successfully navigated to {url}")
                    return True
                else:
                    status = response.status if response else "unknown"
                    logger.warning(f"Navigation response status: {status}")
                    
                    if status >= 400:
                        if attempt < max_retries - 1:
                            logger.warning(f"Retrying navigation due to status code {status}")
                            await asyncio.sleep(2)  # Wait before retry
                            continue
                    return True  # Continue anyway if last attempt
                        
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
                    continue
                else:
                    logger.error(f"All navigation attempts to {url} failed")
                    return False
        
        return False
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    logger.warning(f"Error closing context: {str(e)}")
                
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser: {str(e)}")
            
            if self.playwright:
                try:
                    await self.playwright.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing playwright: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")