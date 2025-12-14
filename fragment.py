import asyncio
import json
import logging
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import config

logger = logging.getLogger(__name__)

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
            
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            
            # Navigate to Fragment
            await self.page.goto('https://fragment.com')
            await asyncio.sleep(2)
            
            # Click login button
            try:
                await self.page.click('text="Log in"', timeout=5000)
                await asyncio.sleep(2)
            except PlaywrightTimeout:
                logger.info("Already logged in or login button not found")
            
            # Wait for user to scan QR code and complete login
            # This is a simplified version - in production, you'd need a way to notify
            # the admin and wait for confirmation
            logger.info("Please scan QR code in browser...")
            
            # Wait for login to complete (check if we can access account page)
            try:
                await self.page.wait_for_url('**/fragment.com/**', timeout=60000)
                await asyncio.sleep(3)
                
                # Save session
                cookies = await self.context.cookies()
                storage_state = await self.context.storage_state()
                await self.save_session(cookies, storage_state)
                
                logger.info("Login successful!")
                return True
                
            except PlaywrightTimeout:
                logger.error("Login timeout - QR code not scanned")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
        finally:
            await self.close()
    
    async def restore_session(self):
        """Restore a saved session"""
        try:
            session_data = await self.load_session()
            if not session_data:
                return False
            
            await self.init_browser()
            
            # Create context with saved state
            self.context = await self.browser.new_context(
                storage_state=session_data.get('storage_state')
            )
            self.page = await self.context.new_page()
            
            # Navigate to Fragment to verify session
            await self.page.goto('https://fragment.com')
            await asyncio.sleep(2)
            
            # Check if we're logged in
            content = await self.page.content()
            if 'Log out' in content or 'Balance' in content:
                logger.info("Session restored successfully")
                return True
            else:
                logger.warning("Session expired")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring session: {e}")
            return False
    
    async def get_balance(self):
        """Get Fragment account balance"""
        try:
            if not self.page:
                if not await self.restore_session():
                    return None
            
            await self.page.goto('https://fragment.com')
            await asyncio.sleep(2)
            
            # Try to find balance element
            # This is a placeholder - actual selector needs to be determined from Fragment's HTML
            try:
                balance_text = await self.page.text_content('.balance, .ton-balance, [class*="balance"]', timeout=5000)
                # Parse balance from text
                match = re.search(r'([\d.]+)', balance_text)
                if match:
                    return float(match.group(1))
            except Exception as e:
                logger.warning(f"Could not find balance element: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
    
    async def gift_premium(self, user_id: int, months: int):
        """
        Gift Telegram Premium to a user
        Returns True if successful
        """
        try:
            if not self.page:
                if not await self.restore_session():
                    return False
            
            # Navigate to gift premium page
            # This is a placeholder URL - actual URL needs to be determined
            await self.page.goto('https://fragment.com/gifts/telegram-premium')
            await asyncio.sleep(2)
            
            # Select duration
            duration_selector = f'[data-months="{months}"], button:has-text("{months} month")'
            try:
                await self.page.click(duration_selector, timeout=5000)
                await asyncio.sleep(1)
            except PlaywrightTimeout:
                logger.error(f"Could not find {months} months option")
                return False
            
            # Enter recipient user ID
            user_id_input = 'input[name="user_id"], input[placeholder*="User ID"]'
            try:
                await self.page.fill(user_id_input, str(user_id), timeout=5000)
                await asyncio.sleep(1)
            except PlaywrightTimeout:
                logger.error("Could not find user ID input")
                return False
            
            # Click gift button
            gift_button = 'button:has-text("Gift"), button:has-text("Send Gift")'
            try:
                await self.page.click(gift_button, timeout=5000)
                await asyncio.sleep(2)
            except PlaywrightTimeout:
                logger.error("Could not find gift button")
                return False
            
            # Confirm if needed
            confirm_button = 'button:has-text("Confirm"), button:has-text("Yes")'
            try:
                await self.page.click(confirm_button, timeout=3000)
                await asyncio.sleep(2)
            except PlaywrightTimeout:
                # Maybe no confirmation needed
                pass
            
            # Check for success message
            content = await self.page.content()
            if 'success' in content.lower() or 'sent' in content.lower():
                logger.info(f"Successfully gifted {months} months Premium to user {user_id}")
                return True
            else:
                logger.warning("Could not confirm gift success")
                return False
                
        except Exception as e:
            logger.error(f"Error gifting premium: {e}")
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
