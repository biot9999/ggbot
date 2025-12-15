"""
Telethon-based Username Resolver
Resolves Telegram usernames to user IDs and fetches profile information
"""

import logging
import os
from typing import Optional, Dict
from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError
from telethon.tl.types import User

logger = logging.getLogger(__name__)


class TelethonResolver:
    """Username resolver using Telethon"""
    
    def __init__(self, api_id: int, api_hash: str, session_name: str = 'resolver_session', 
                 phone: str = None, password: str = None):
        """
        Initialize Telethon resolver
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            session_name: Session file name
            phone: Phone number for login (optional, only needed for first-time login)
            password: 2FA password if enabled (optional)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.phone = phone
        self.password = password
        self.client = None
        self._connected = False
    
    async def connect(self) -> bool:
        """
        Connect to Telegram
        
        Returns:
            bool: True if connection successful
        """
        try:
            if self.client is None:
                self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            
            if not self._connected:
                await self.client.connect()
                
                # Check if authorized
                if not await self.client.is_user_authorized():
                    if self.phone:
                        logger.info("Telethon: Not authorized, attempting login...")
                        await self.client.send_code_request(self.phone)
                        # Note: In production, you'd need to handle code input
                        # For now, we expect the session to already be authorized
                        logger.warning("Telethon: Code required for login. Please authorize session manually.")
                        return False
                    else:
                        logger.error("Telethon: Not authorized and no phone number provided")
                        return False
                
                self._connected = True
                logger.info("✅ Telethon resolver connected")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error connecting Telethon: {e}", exc_info=True)
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client and self._connected:
            await self.client.disconnect()
            self._connected = False
            logger.info("Telethon resolver disconnected")
    
    async def resolve_username(self, username: str) -> Optional[Dict]:
        """
        Resolve username to user information
        
        Args:
            username: Username without @ prefix
            
        Returns:
            dict: User information (user_id, username, first_name, last_name, photo_url)
                  or None if resolution fails
        """
        try:
            # Ensure connected
            if not self._connected:
                if not await self.connect():
                    logger.error("Failed to connect Telethon")
                    return None
            
            # Remove @ if present
            if username.startswith('@'):
                username = username[1:]
            
            logger.info(f"Telethon: Resolving username @{username}")
            
            # Get entity
            entity = await self.client.get_entity(username)
            
            if not isinstance(entity, User):
                logger.warning(f"Telethon: @{username} is not a user")
                return None
            
            # Extract user information
            user_info = {
                'user_id': entity.id,
                'username': entity.username,
                'first_name': entity.first_name or '',
                'last_name': entity.last_name or '',
                'photo_url': None  # We'll get photo separately if needed
            }
            
            logger.info(f"✅ Telethon: Resolved @{username} to user_id {entity.id}")
            return user_info
            
        except (UsernameInvalidError, UsernameNotOccupiedError) as e:
            logger.warning(f"Telethon: Username @{username} not found: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Telethon: Error resolving @{username}: {e}", exc_info=True)
            return None
    
    async def get_profile_photo(self, user_id: int) -> Optional[bytes]:
        """
        Get user's profile photo
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bytes: Photo data or None if not available
        """
        try:
            # Ensure connected
            if not self._connected:
                if not await self.connect():
                    return None
            
            logger.info(f"Telethon: Fetching profile photo for user {user_id}")
            
            # Get entity
            entity = await self.client.get_entity(user_id)
            
            # Download profile photo to bytes
            photo_bytes = await self.client.download_profile_photo(entity, bytes)
            
            if photo_bytes:
                logger.info(f"✅ Telethon: Retrieved profile photo for user {user_id}")
            else:
                logger.info(f"Telethon: No profile photo for user {user_id}")
            
            return photo_bytes
            
        except Exception as e:
            logger.error(f"❌ Telethon: Error getting profile photo for user {user_id}: {e}")
            return None
    
    async def resolve_with_photo(self, username: str) -> Optional[Dict]:
        """
        Resolve username and fetch profile photo
        
        Args:
            username: Username without @ prefix
            
        Returns:
            dict: User information including photo_bytes, or None if resolution fails
        """
        user_info = await self.resolve_username(username)
        
        if user_info:
            # Try to get photo
            photo_bytes = await self.get_profile_photo(user_info['user_id'])
            user_info['photo_bytes'] = photo_bytes
        
        return user_info


# Global resolver instance (initialized lazily)
_resolver_instance = None


async def get_resolver() -> Optional[TelethonResolver]:
    """
    Get or create global Telethon resolver instance
    
    Returns:
        TelethonResolver: Resolver instance or None if configuration missing
    """
    global _resolver_instance
    
    if _resolver_instance is None:
        # Import config here to avoid circular imports
        import config
        
        # Check if Telethon is configured
        if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
            logger.warning("Telethon resolver not configured (missing API_ID or API_HASH)")
            return None
        
        try:
            _resolver_instance = TelethonResolver(
                api_id=config.TELEGRAM_API_ID,
                api_hash=config.TELEGRAM_API_HASH,
                session_name=config.TELEGRAM_SESSION,
                phone=config.TELEGRAM_PHONE,
                password=config.TELEGRAM_2FA_PASSWORD  # Optional 2FA password
            )
            
            # Try to connect
            if not await _resolver_instance.connect():
                logger.warning("Failed to connect Telethon resolver")
                return None
                
        except Exception as e:
            logger.error(f"Error initializing Telethon resolver: {e}", exc_info=True)
            return None
    
    return _resolver_instance
