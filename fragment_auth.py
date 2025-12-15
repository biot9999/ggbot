"""
Fragment 认证模块
使用 Telethon 登录 Telegram 并获取 Fragment 认证数据
"""

from telethon import TelegramClient, functions
from telethon.tl.types import DataJSON
import re
import logging

logger = logging.getLogger(__name__)


class FragmentAuth:
    """Fragment 认证管理器"""
    
    def __init__(self, api_id, api_hash, phone, session_name='fragment_session'):
        """
        初始化 Fragment 认证管理器
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            phone: 手机号（国际格式，如 +8613800138000）
            session_name: Session 文件名
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.client = None
        self.hash = None
        self.cookies = {}
    
    async def login(self):
        """
        登录 Telegram
        
        Returns:
            bool: 登录是否成功
        """
        try:
            self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            logger.info(f"✅ Telegram 登录成功: {self.phone}")
            return True
        except Exception as e:
            logger.error(f"❌ Telegram 登录失败: {e}", exc_info=True)
            return False
    
    async def get_fragment_auth(self):
        """
        获取 Fragment 认证数据
        
        Returns:
            str: Fragment hash，失败返回 None
        """
        try:
            # 请求 Fragment Web App
            logger.info("正在请求 Fragment Web App...")
            result = await self.client(functions.messages.RequestWebViewRequest(
                peer='FragmentBot',  # Fragment 官方 Bot
                bot='FragmentBot',
                platform='android',
                url='https://fragment.com'
            ))
            
            # 解析返回的 URL，提取认证数据
            # result.url = "https://fragment.com#tgWebAppData=query_id%3D...%26hash%3D..."
            url = result.url
            logger.debug(f"Web App URL: {url[:100]}...")
            
            # 提取 hash
            hash_match = re.search(r'hash=([a-f0-9]+)', url)
            if hash_match:
                self.hash = hash_match.group(1)
                logger.info(f"✅ 获取 Fragment hash: {self.hash[:16]}...")
            else:
                logger.warning("⚠️ 未能从 URL 中提取 hash")
                # 尝试从 tgWebAppData 中提取
                if 'tgWebAppData' in url:
                    # URL decode and extract hash
                    import urllib.parse
                    decoded = urllib.parse.unquote(url)
                    hash_match = re.search(r'hash=([a-f0-9]+)', decoded)
                    if hash_match:
                        self.hash = hash_match.group(1)
                        logger.info(f"✅ 从 tgWebAppData 获取 hash: {self.hash[:16]}...")
            
            # 提取其他认证参数（如果有）
            # 某些 token 可能需要通过访问 Fragment 页面获取
            
            return self.hash
            
        except Exception as e:
            logger.error(f"❌ 获取 Fragment 认证失败: {e}", exc_info=True)
            return None
    
    async def get_full_auth_data(self):
        """
        获取完整的认证数据（包括所有参数）
        
        Returns:
            dict: 包含所有认证参数的字典
        """
        try:
            result = await self.client(functions.messages.RequestWebViewRequest(
                peer='FragmentBot',
                bot='FragmentBot',
                platform='android',
                url='https://fragment.com'
            ))
            
            url = result.url
            import urllib.parse
            
            # 解析 URL 中的所有参数
            auth_data = {
                'url': url,
                'hash': None,
                'query_id': None,
                'user': None,
                'auth_date': None,
            }
            
            # 提取 tgWebAppData
            if 'tgWebAppData' in url:
                # Split by # and get the fragment part
                parts = url.split('#')
                if len(parts) > 1:
                    fragment = parts[1]
                    params = urllib.parse.parse_qs(fragment)
                    
                    if 'tgWebAppData' in params:
                        web_app_data = params['tgWebAppData'][0]
                        web_app_params = urllib.parse.parse_qs(web_app_data)
                        
                        auth_data['hash'] = web_app_params.get('hash', [None])[0]
                        auth_data['query_id'] = web_app_params.get('query_id', [None])[0]
                        auth_data['user'] = web_app_params.get('user', [None])[0]
                        auth_data['auth_date'] = web_app_params.get('auth_date', [None])[0]
            
            # Fallback to regex
            if not auth_data['hash']:
                hash_match = re.search(r'hash=([a-f0-9]+)', url)
                if hash_match:
                    auth_data['hash'] = hash_match.group(1)
            
            self.hash = auth_data['hash']
            logger.info(f"✅ 获取完整认证数据: hash={self.hash[:16] if self.hash else 'None'}...")
            
            return auth_data
            
        except Exception as e:
            logger.error(f"❌ 获取完整认证数据失败: {e}", exc_info=True)
            return None
    
    async def close(self):
        """关闭 Telegram 连接"""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram 连接已关闭")
