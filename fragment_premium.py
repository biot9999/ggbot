"""
Fragment 会员开通集成模块
整合认证和 API 调用
"""

import asyncio
import logging
import aiohttp
from fragment_auth import FragmentAuth
from fragment_api import FragmentAPI

logger = logging.getLogger(__name__)


class FragmentPremium:
    """Fragment 会员管理器"""
    
    def __init__(self, api_id, api_hash, phone):
        """
        初始化 Fragment 会员管理器
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            phone: 手机号（国际格式）
        """
        self.auth = FragmentAuth(api_id, api_hash, phone)
        self.api = None
        self._initialized = False
    
    async def initialize(self):
        """
        初始化：登录并获取认证
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 1. 登录 Telegram
            logger.info("开始初始化 Fragment Premium...")
            if not await self.auth.login():
                logger.error("Telegram 登录失败")
                return False
            
            # 2. 获取 Fragment 认证
            hash_value = await self.auth.get_fragment_auth()
            
            if not hash_value:
                logger.error("无法获取 Fragment 认证")
                return False
            
            # 3. 尝试获取 cookies（可选）
            cookies = await self._get_fragment_cookies(hash_value)
            
            # 4. 初始化 API 客户端
            self.api = FragmentAPI(hash_value, cookies)
            
            self._initialized = True
            logger.info("✅ Fragment Premium 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}", exc_info=True)
            return False
    
    async def _get_fragment_cookies(self, hash_value: str):
        """
        获取 Fragment cookies（通过访问页面）
        
        Args:
            hash_value: Fragment hash
            
        Returns:
            dict: Cookies 字典
        """
        try:
            logger.info("尝试获取 Fragment cookies...")
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.get(
                    f'https://fragment.com?hash={hash_value}',
                    headers=headers,
                    allow_redirects=True
                ) as resp:
                    cookies = {k: v.value for k, v in resp.cookies.items()}
                    
                    if cookies:
                        logger.info(f"✅ 获取到 {len(cookies)} 个 cookies")
                        logger.debug(f"Cookies: {list(cookies.keys())}")
                    else:
                        logger.info("未获取到 cookies，将仅使用 hash")
                    
                    return cookies
                    
        except Exception as e:
            logger.warning(f"获取 cookies 失败，将仅使用 hash: {e}")
            return {}
    
    async def gift_premium(self, user_id: int, months: int = 12):
        """
        给指定用户赠送会员
        
        Args:
            user_id: Telegram 用户 ID
            months: 月数 (3, 6, 12)
            
        Returns:
            dict: API 响应结果
        """
        if not self._initialized:
            raise Exception("未初始化，请先调用 initialize()")
        
        logger.info(f"🎁 开始为 User ID {user_id} 开通 {months} 个月会员...")
        
        # 尝试方法1: 使用 user_id 直接赠送
        result = self.api.gift_premium_by_user_id(user_id, months)
        
        if result.get('ok'):
            logger.info(f"✅ 会员开通成功！User ID: {user_id}, 月数: {months}")
            return result
        
        # 如果方法1失败，尝试方法2: 使用 updatePremiumState
        logger.info("尝试备用方法...")
        result = self.api.update_premium_state(mode='new', months=months, recipient=str(user_id))
        
        if result.get('ok'):
            logger.info(f"✅ 会员开通成功（备用方法）！User ID: {user_id}, 月数: {months}")
        else:
            logger.error(f"❌ 会员开通失败: {result.get('error', 'Unknown error')}")
        
        return result
    
    async def get_balance(self):
        """
        获取 Fragment 账户余额
        
        Returns:
            float: 余额（TON），失败返回 None
        """
        if not self._initialized:
            raise Exception("未初始化，请先调用 initialize()")
        
        try:
            result = self.api.get_balance()
            
            if result.get('ok'):
                # 尝试从响应中提取余额
                balance = result.get('balance', result.get('ton_balance', None))
                if balance is not None:
                    logger.info(f"💰 Fragment 余额: {balance} TON")
                    return float(balance)
            
            logger.warning("无法获取余额信息")
            return None
            
        except Exception as e:
            logger.error(f"获取余额失败: {e}", exc_info=True)
            return None
    
    async def get_premium_info(self):
        """
        获取 Premium 信息
        
        Returns:
            dict: Premium 信息
        """
        if not self._initialized:
            raise Exception("未初始化，请先调用 initialize()")
        
        return self.api.get_premium_info()
    
    async def close(self):
        """关闭连接"""
        await self.auth.close()
        logger.info("Fragment Premium 已关闭")


# 使用示例
async def main():
    """测试示例"""
    # 配置（从环境变量或配置文件读取）
    API_ID = 2040
    API_HASH = "b18441a1ff607e10a989891a5462e627"
    PHONE = "+8613800138000"  # 需要配置
    
    premium = FragmentPremium(API_ID, API_HASH, PHONE)
    
    try:
        # 初始化
        if await premium.initialize():
            print("✅ 初始化成功")
            
            # 获取余额
            balance = await premium.get_balance()
            if balance:
                print(f"💰 余额: {balance} TON")
            
            # 赠送会员（测试时注释掉）
            # result = await premium.gift_premium(123456789, months=12)
            # if result.get('ok'):
            #     print("✅ 会员开通成功！")
            # else:
            #     print(f"❌ 失败: {result.get('error')}")
        else:
            print("❌ 初始化失败")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    finally:
        await premium.close()


if __name__ == '__main__':
    asyncio.run(main())
