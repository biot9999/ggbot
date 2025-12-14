import asyncio
import json
import logging
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import config

logger = logging.getLogger(__name__)

def check_playwright_dependencies():
    """
    Check if Playwright dependencies are installed
    
    Returns:
        tuple: (success: bool, error_type: str or None)
    """
    try:
        from playwright.sync_api import sync_playwright
        # Just check if we can create the playwright instance and access chromium
        # Don't actually launch browser (expensive and unnecessary)
        with sync_playwright() as p:
            # Try to get the executable path - this will fail if dependencies missing
            try:
                _ = p.chromium.executable_path
                return True, None
            except Exception as e:
                error_str = str(e).lower()
                if "looks like playwright" in error_str or "browser" in error_str:
                    return False, "missing_browser"
                return False, str(e)
    except ImportError as e:
        return False, f"No module named 'playwright'"
    except Exception as e:
        error_str = str(e).lower()
        if "missing dependencies" in error_str or "host system" in error_str:
            return False, "missing_deps"
        elif "executable" in error_str or "browser" in error_str:
            return False, "missing_browser"
        return False, str(e)

class FragmentAutomation:
    def __init__(self):
        self.session_file = config.FRAGMENT_SESSION_FILE
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def init_browser(self):
        """Initialize Playwright browser"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
    
    async def load_session(self):
        """Load saved session"""
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
                return session_data
        except FileNotFoundError:
            logger.info("No saved session found")
            return None
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return None
    
    async def save_session(self, cookies, storage_state):
        """Save session to file"""
        try:
            session_data = {
                'cookies': cookies,
                'storage_state': storage_state
            }
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            logger.info("Session saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False
    
    async def login_with_telegram(self):
        """
        Interactive login with Telegram
        This requires manual QR code scanning
        Returns True if login successful
        """
        try:
            await self.init_browser()
            
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
            
            # Navigate to Fragment
            logger.info("Navigating to Fragment.com...")
            await self.page.goto('https://fragment.com', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Try to find and click login button with multiple selectors
            login_clicked = False
            login_selectors = [
                'button:has-text("Log in")',
                'a:has-text("Log in")',
                '.tm-button:has-text("Log in")',
                '[data-action="login"]'
            ]
            
            for selector in login_selectors:
                try:
                    logger.info(f"Trying login selector: {selector}")
                    await self.page.click(selector, timeout=3000)
                    login_clicked = True
                    logger.info("Login button clicked successfully")
                    await asyncio.sleep(3)
                    break
                except Exception as e:
                    logger.debug(f"Selector {selector} not found: {e}")
                    continue
            
            if not login_clicked:
                # Check if already logged in
                content = await self.page.content()
                if 'Balance' in content or 'My Items' in content:
                    logger.info("Already logged in")
                    await self.save_session(await self.context.cookies(), await self.context.storage_state())
                    return True
                else:
                    logger.error("Could not find login button and not logged in")
                    # Take screenshot for debugging
                    try:
                        await self.page.screenshot(path='/tmp/fragment_login_error.png')
                        logger.info("Screenshot saved to /tmp/fragment_login_error.png")
                    except Exception as e:
                        logger.debug(f"Could not save screenshot: {e}")
                    return False
            
            # Wait for QR code or login completion
            logger.info("Waiting for login... Please scan QR code")
            
            # Wait for either successful login or timeout
            try:
                # Wait for navigation away from login page or success indicators
                await self.page.wait_for_function(
                    """() => {
                        return document.body.innerText.includes('Balance') || 
                               document.body.innerText.includes('My Items') ||
                               window.location.href !== 'https://fragment.com/';
                    }""",
                    timeout=120000  # 2 minutes for QR scan
                )
                
                await asyncio.sleep(3)
                
                # Verify login success
                content = await self.page.content()
                if 'Balance' in content or 'My Items' in content or 'Log out' in content:
                    # Save session
                    cookies = await self.context.cookies()
                    storage_state = await self.context.storage_state()
                    await self.save_session(cookies, storage_state)
                    
                    logger.info("Login successful!")
                    return True
                else:
                    logger.warning("Login page changed but couldn't confirm success")
                    return False
                
            except Exception as e:
                logger.error(f"Login timeout or error: {e}")
                # Take screenshot for debugging
                try:
                    await self.page.screenshot(path='/tmp/fragment_login_timeout.png')
                    logger.info("Screenshot saved to /tmp/fragment_login_timeout.png")
                except Exception as screenshot_error:
                    logger.debug(f"Could not save screenshot: {screenshot_error}")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            # Take screenshot for debugging
            try:
                if self.page:
                    await self.page.screenshot(path='/tmp/fragment_login_exception.png')
                    logger.info("Screenshot saved to /tmp/fragment_login_exception.png")
            except Exception as screenshot_error:
                logger.debug(f"Could not save screenshot: {screenshot_error}")
            return False
        finally:
            # Don't close browser immediately, keep it for session
            pass
    
    async def restore_session(self):
        """Restore a saved session"""
        try:
            session_data = await self.load_session()
            if not session_data:
                logger.warning("No saved session to restore")
                return False
            
            await self.init_browser()
            
            # Create context with saved state
            self.context = await self.browser.new_context(
                storage_state=session_data.get('storage_state'),
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
            
            # Navigate to Fragment to verify session
            logger.info("Restoring session and navigating to Fragment...")
            await self.page.goto('https://fragment.com', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Check if we're logged in
            content = await self.page.content()
            if 'Log out' in content or 'Balance' in content or 'My Items' in content:
                logger.info("Session restored successfully")
                return True
            else:
                logger.warning("Session expired or invalid")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring session: {e}")
            return False
    
    async def get_balance(self):
        """Get Fragment account balance"""
        try:
            if not self.page:
                if not await self.restore_session():
                    logger.error("Cannot restore session for balance check")
                    return None
            
            await self.page.goto('https://fragment.com', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Try multiple selectors for balance
            balance_selectors = [
                '.tm-balance',
                '[class*="balance"]',
                'text=/[0-9.]+ TON/',
                '.header-balance'
            ]
            
            for selector in balance_selectors:
                try:
                    balance_element = await self.page.wait_for_selector(selector, timeout=3000)
                    if balance_element:
                        balance_text = await balance_element.text_content()
                        logger.info(f"Found balance text: {balance_text}")
                        # Parse balance from text
                        match = re.search(r'([\d,.]+)', balance_text)
                        if match:
                            balance_str = match.group(1).replace(',', '')
                            return float(balance_str)
                except Exception as e:
                    logger.debug(f"Balance selector {selector} failed: {e}")
                    continue
            
            logger.warning("Could not find balance element with any selector")
            return None
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
    
    async def gift_premium(self, user_id: int, months: int, max_retries: int = 3):
        """
        Gift Telegram Premium to a user with retry mechanism
        
        Args:
            user_id: Telegram user ID of the recipient
            months: Number of months (3, 6, or 12)
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to gift Premium (attempt {attempt + 1}/{max_retries})")
                
                if not self.page:
                    if not await self.restore_session():
                        logger.error("Cannot restore session for gifting")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(5)
                            continue
                        return False
                
                # Navigate to gift premium page
                logger.info("Navigating to Premium gift page...")
                await self.page.goto('https://fragment.com/gifts', wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # Try to find and click Premium gift option
                premium_selectors = [
                    'a:has-text("Telegram Premium")',
                    'text=/Telegram Premium/i',
                    '[href*="telegram-premium"]'
                ]
                
                premium_clicked = False
                for selector in premium_selectors:
                    try:
                        logger.info(f"Trying Premium selector: {selector}")
                        await self.page.click(selector, timeout=5000)
                        premium_clicked = True
                        await asyncio.sleep(2)
                        break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not premium_clicked:
                    logger.error("Could not find Premium gift option")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                    return False
                
                # Select duration
                logger.info(f"Selecting {months} months duration...")
                duration_selectors = [
                    f'button:has-text("{months} month")',
                    f'[data-months="{months}"]',
                    f'text=/{months} month/i'
                ]
                
                duration_clicked = False
                for selector in duration_selectors:
                    try:
                        await self.page.click(selector, timeout=5000)
                        duration_clicked = True
                        await asyncio.sleep(1)
                        break
                    except Exception as e:
                        logger.debug(f"Duration selector {selector} failed: {e}")
                        continue
                
                if not duration_clicked:
                    logger.warning(f"Could not select {months} months duration, may already be selected")
                
                # Enter recipient user ID
                logger.info(f"Entering recipient user ID: {user_id}")
                user_id_selectors = [
                    'input[name="user_id"]',
                    'input[placeholder*="User ID"]',
                    'input[placeholder*="username"]',
                    'input[type="text"]'
                ]
                
                user_id_entered = False
                for selector in user_id_selectors:
                    try:
                        await self.page.fill(selector, str(user_id), timeout=5000)
                        user_id_entered = True
                        await asyncio.sleep(1)
                        break
                    except Exception as e:
                        logger.debug(f"User ID input {selector} failed: {e}")
                        continue
                
                if not user_id_entered:
                    logger.error("Could not find user ID input field")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                    return False
                
                # Click gift/send button
                logger.info("Clicking gift button...")
                gift_selectors = [
                    'button:has-text("Gift")',
                    'button:has-text("Send")',
                    'button:has-text("Send Gift")',
                    'button[type="submit"]'
                ]
                
                gift_clicked = False
                for selector in gift_selectors:
                    try:
                        await self.page.click(selector, timeout=5000)
                        gift_clicked = True
                        await asyncio.sleep(3)
                        break
                    except Exception as e:
                        logger.debug(f"Gift button {selector} failed: {e}")
                        continue
                
                if not gift_clicked:
                    logger.error("Could not find gift button")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                    return False
                
                # Try to confirm if needed
                logger.info("Checking for confirmation dialog...")
                confirm_selectors = [
                    'button:has-text("Confirm")',
                    'button:has-text("Yes")',
                    'button:has-text("OK")'
                ]
                
                for selector in confirm_selectors:
                    try:
                        await self.page.click(selector, timeout=3000)
                        await asyncio.sleep(2)
                        logger.info("Confirmation clicked")
                        break
                    except Exception:
                        # No confirmation needed or button not found
                        pass
                
                # Check for success
                await asyncio.sleep(2)
                content = await self.page.content()
                page_text = await self.page.evaluate('() => document.body.innerText')
                
                success_indicators = ['success', 'sent', 'delivered', 'completed']
                error_indicators = ['error', 'failed', 'insufficient', 'invalid']
                
                if any(indicator in page_text.lower() for indicator in success_indicators):
                    logger.info(f"Successfully gifted {months} months Premium to user {user_id}")
                    return True
                elif any(indicator in page_text.lower() for indicator in error_indicators):
                    logger.error(f"Error gifting Premium: {page_text[:200]}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(5)
                        continue
                    return False
                else:
                    logger.warning("Could not confirm gift success, assuming success")
                    return True
                    
            except Exception as e:
                logger.error(f"Error gifting premium (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue
                return False
        
        return False
    
    async def close(self):
        """Close browser and cleanup"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

# Global fragment instance
fragment = FragmentAutomation()
