"""
Telethon-based Username Resolver with Multi-Session Support
Resolves Telegram usernames to user IDs and fetches profile information
Supports multiple pre-authorized session files with automatic rotation
"""

import logging
import os
import glob
from pathlib import Path
from typing import Optional, Dict, List
from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError, AuthKeyError, FloodWaitError
from telethon.tl.types import User

logger = logging.getLogger(__name__)


class TelethonResolver:
    """Username resolver using Telethon with multi-session support and rotation"""
    
    def __init__(self, api_id: int, api_hash: str, sessions_dir: str = 'sessions',
                 session_priority: Optional[List[str]] = None, password: str = None):
        """
        Initialize Telethon resolver with multi-session support
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            sessions_dir: Directory containing *.session files
            session_priority: Optional list of session names (without .session) to prioritize
            password: 2FA password if enabled (optional)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.sessions_dir = sessions_dir
        self.password = password
        self.session_priority = session_priority or []
        
        # Current session state
        self.current_client = None
        self.current_session_name = None
        self._connected = False
        
        # Available sessions (discovered on startup)
        self.available_sessions = []
        self.session_index = 0
        
    def _discover_sessions(self) -> List[str]:
        """
        Discover available session files
        
        Returns:
            List of session names (without .session extension)
        """
        sessions = []
        
        # Ensure sessions directory exists
        os.makedirs(self.sessions_dir, exist_ok=True)
        
        # If priority list is provided, use it first
        if self.session_priority:
            for session_name in self.session_priority:
                session_path = os.path.join(self.sessions_dir, f"{session_name}.session")
                if os.path.exists(session_path):
                    sessions.append(session_name)
                    logger.info(f"Found priority session: {session_name}")
                else:
                    logger.warning(f"Priority session not found: {session_name}")
        
        # Auto-discover other sessions in directory
        pattern = os.path.join(self.sessions_dir, "*.session")
        for session_file in glob.glob(pattern):
            session_name = Path(session_file).stem
            if session_name not in sessions:
                sessions.append(session_name)
                logger.info(f"Auto-discovered session: {session_name}")
        
        if not sessions:
            logger.warning(f"No session files found in {self.sessions_dir}")
        
        return sessions
    
    async def ensure_started(self) -> bool:
        """
        Ensure resolver is started and connected
        
        Returns:
            bool: True if connected successfully
        """
        if self._connected and self.current_client:
            return True
        
        # Discover available sessions
        if not self.available_sessions:
            self.available_sessions = self._discover_sessions()
            if not self.available_sessions:
                logger.error("No session files available for Telethon resolver")
                return False
            
            logger.info(f"Discovered {len(self.available_sessions)} session file(s)")
        
        # Try to connect with first available session
        return await self._connect_next_session()
    
    async def _connect_next_session(self) -> bool:
        """
        Connect to the next available session
        
        Returns:
            bool: True if connection successful
        """
        while self.session_index < len(self.available_sessions):
            session_name = self.available_sessions[self.session_index]
            session_path = os.path.join(self.sessions_dir, session_name)
            
            try:
                logger.info(f"Attempting to connect with session: {session_name}")
                
                # Create client
                client = TelegramClient(session_path, self.api_id, self.api_hash)
                await client.connect()
                
                # Check if authorized
                if not await client.is_user_authorized():
                    logger.warning(f"Session {session_name} not authorized, skipping")
                    await client.disconnect()
                    self.session_index += 1
                    continue
                
                # Successfully connected
                self.current_client = client
                self.current_session_name = session_name
                self._connected = True
                logger.info(f"✅ Telethon resolver connected with session: {session_name}")
                return True
                
            except AuthKeyError as e:
                logger.warning(f"Session {session_name} auth key error: {e}, trying next")
                self.session_index += 1
                continue
            except Exception as e:
                logger.error(f"Error connecting session {session_name}: {e}", exc_info=True)
                self.session_index += 1
                continue
        
        logger.error("All available sessions failed to connect")
        return False
    
    async def _rotate_session(self) -> bool:
        """
        Rotate to next session on failure
        
        Returns:
            bool: True if successfully rotated to new session
        """
        logger.info(f"Rotating from session {self.current_session_name}")
        
        # Disconnect current session
        if self.current_client and self._connected:
            try:
                await self.current_client.disconnect()
            except (ConnectionError, OSError) as e:
                # Ignore disconnect errors during rotation - session may already be dead
                logger.debug(f"Error disconnecting session during rotation: {e}")
            except Exception as e:
                # Log unexpected errors but continue rotation
                logger.warning(f"Unexpected error disconnecting session: {e}")
        
        self.current_client = None
        self.current_session_name = None
        self._connected = False
        
        # Move to next session
        self.session_index += 1
        
        return await self._connect_next_session()
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.current_client and self._connected:
            await self.current_client.disconnect()
            self._connected = False
            logger.info(f"Telethon resolver disconnected from session: {self.current_session_name}")
    
    async def resolve_username(self, username: str) -> Optional[Dict]:
        """
        Resolve username to user information
        
        Args:
            username: Username without @ prefix
            
        Returns:
            dict: User information (user_id, username, first_name, last_name)
                  or None if resolution fails
        """
        # Ensure connected
        if not await self.ensure_started():
            logger.error("Failed to start Telethon resolver")
            return None
        
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        retry_count = 0
        max_retries = len(self.available_sessions)
        
        while retry_count < max_retries:
            try:
                logger.info(f"Telethon: Resolving username @{username} with session {self.current_session_name}")
                
                # Get entity
                entity = await self.current_client.get_entity(username)
                
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
            except FloodWaitError as e:
                logger.warning(f"Telethon: FloodWait error for @{username}, rotating session")
                if not await self._rotate_session():
                    logger.error("Failed to rotate to another session")
                    return None
                retry_count += 1
            except Exception as e:
                logger.error(f"❌ Telethon: Error resolving @{username}: {e}", exc_info=True)
                # Try rotating session on error
                if retry_count < max_retries - 1:
                    if await self._rotate_session():
                        retry_count += 1
                        continue
                return None
        
        logger.error(f"Failed to resolve @{username} after trying all sessions")
        return None
    
    async def resolve_user_id(self, user_id: int) -> Optional[Dict]:
        """
        Resolve user ID to user information
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            dict: User information or None if resolution fails
        """
        # Ensure connected
        if not await self.ensure_started():
            logger.error("Failed to start Telethon resolver")
            return None
        
        retry_count = 0
        max_retries = len(self.available_sessions)
        
        while retry_count < max_retries:
            try:
                logger.info(f"Telethon: Resolving user_id {user_id} with session {self.current_session_name}")
                
                # Get entity
                entity = await self.current_client.get_entity(user_id)
                
                if not isinstance(entity, User):
                    logger.warning(f"Telethon: {user_id} is not a user")
                    return None
                
                user_info = {
                    'user_id': entity.id,
                    'username': getattr(entity, 'username', None),
                    'first_name': getattr(entity, 'first_name', ''),
                    'last_name': getattr(entity, 'last_name', ''),
                    'photo_url': None
                }
                
                logger.info(f"✅ Telethon: Resolved user_id {user_id}")
                return user_info
                
            except FloodWaitError as e:
                logger.warning(f"Telethon: FloodWait error for user_id {user_id}, rotating session")
                if not await self._rotate_session():
                    logger.error("Failed to rotate to another session")
                    return None
                retry_count += 1
            except Exception as e:
                logger.error(f"❌ Telethon: Error resolving user_id {user_id}: {e}", exc_info=True)
                # Try rotating session on error
                if retry_count < max_retries - 1:
                    if await self._rotate_session():
                        retry_count += 1
                        continue
                return None
        
        logger.error(f"Failed to resolve user_id {user_id} after trying all sessions")
        return None
    
    async def fetch_photo_file(self, user_id: int) -> Optional[bytes]:
        """
        Get user's profile photo as bytes
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bytes: Photo data or None if not available
        """
        # Ensure connected
        if not await self.ensure_started():
            return None
        
        retry_count = 0
        max_retries = len(self.available_sessions)
        
        while retry_count < max_retries:
            try:
                logger.info(f"Telethon: Fetching profile photo for user {user_id}")
                
                # Get entity
                entity = await self.current_client.get_entity(user_id)
                
                # Download profile photo to bytes
                photo_bytes = await self.current_client.download_profile_photo(entity, bytes)
                
                if photo_bytes:
                    logger.info(f"✅ Telethon: Retrieved profile photo for user {user_id}")
                else:
                    logger.info(f"Telethon: No profile photo for user {user_id}")
                
                return photo_bytes
                
            except FloodWaitError as e:
                logger.warning(f"Telethon: FloodWait error fetching photo, rotating session")
                if not await self._rotate_session():
                    return None
                retry_count += 1
            except Exception as e:
                logger.error(f"❌ Telethon: Error getting profile photo for user {user_id}: {e}")
                # Try rotating session on error
                if retry_count < max_retries - 1:
                    if await self._rotate_session():
                        retry_count += 1
                        continue
                return None
        
        return None
    
    async def get_profile_photo(self, user_id: int) -> Optional[bytes]:
        """Alias for fetch_photo_file for backward compatibility"""
        return await self.fetch_photo_file(user_id)
    
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
            photo_bytes = await self.fetch_photo_file(user_info['user_id'])
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
            # Parse session priority list if provided
            session_priority = None
            if config.TELETHON_SESSIONS:
                session_priority = [s.strip() for s in config.TELETHON_SESSIONS.split(',') if s.strip()]
            
            _resolver_instance = TelethonResolver(
                api_id=config.TELEGRAM_API_ID,
                api_hash=config.TELEGRAM_API_HASH,
                sessions_dir=config.TELETHON_SESSIONS_DIR,
                session_priority=session_priority,
                password=config.TELEGRAM_2FA_PASSWORD
            )
            
            # Try to connect
            if not await _resolver_instance.ensure_started():
                logger.warning("Failed to start Telethon resolver")
                return None
            
            logger.info("✅ Telethon resolver initialized and ready")
                
        except Exception as e:
            logger.error(f"Error initializing Telethon resolver: {e}", exc_info=True)
            return None
    
    return _resolver_instance

