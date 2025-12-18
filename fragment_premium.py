"""
Fragment 会员开通集成模块
整合认证和 API 调用
"""

import logging
from fragment_auth import FragmentAuth
from fragment_api import FragmentAPI

logger = logging.getLogger(__name__)


class FragmentPremium:
    """Fragment 会员管理器"""
    
    def __init__(self, config_file: str = 'fragment_auth.json'):
        """
        初始化 Fragment 会员管理器
        
        Args:
            config_file: Fragment 认证配置文件路径
        """
        self.config_file = config_file
        self.auth = FragmentAuth(config_file)
        self.api = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        初始化：加载认证数据并创建 API 客户端
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("开始初始化 Fragment Premium...")
            
            # 1. 加载认证数据
            if not self.auth.load_auth():
                logger.error("❌ Fragment 认证数据加载失败")
                logger.error("")
                logger.error("📝 配置步骤：")
                logger.error("1. 在浏览器访问 https://fragment.com 并登录")
                logger.error("2. 打开浏览器开发者工具（F12）")
                logger.error("3. 从 Application/Storage > Cookies 获取 cookies")
                logger.error("4. 从 Network 请求中获取 hash 参数")
                logger.error("5. 填入 fragment_auth.json 配置文件")
                logger.error("")
                return False
            
            # 2. 获取认证数据
            auth_data = self.auth.get_auth_data()
            
            if not auth_data or not auth_data.get('hash'):
                logger.error("❌ 认证数据无效：缺少 hash")
                return False
            
            # 3. 初始化 API 客户端
            self.api = FragmentAPI(
                hash_value=auth_data['hash'],
                cookies=auth_data.get('cookies'),
                headers=auth_data.get('headers')
            )
            
            # 4. 测试连接
            logger.info("测试 Fragment 连接...")
            if not self.api.test_connection():
                logger.warning("⚠️ Fragment 连接测试失败，认证可能已过期")
                logger.warning("如果后续操作失败，请重新从浏览器获取认证数据")
            
            self._initialized = True
            logger.info("✅ Fragment Premium 初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}", exc_info=True)
            return False
    
    def gift_premium(self, username: str, months: int = 12):
        """
        给指定用户赠送会员（仅支持 username）
        
        Args:
            username: Telegram username (可以带或不带 @ 前缀)
            months: 月数 (3, 6, 12)
            
        Returns:
            dict: API 响应结果
        """
        if not self._initialized:
            logger.error("❌ FragmentPremium 未初始化，无法赠送会员")
            raise Exception("未初始化，请先调用 initialize()")
        
        # 清理 username（移除 @ 前缀）
        clean_username = username.lstrip('@')
        
        logger.info(f"🎁 [Fragment Gift] 开始为 @{clean_username} 开通 {months} 个月会员...")
        logger.info(f"[Fragment Gift] Parameters - Username: @{clean_username}, Months: {months}")
        logger.debug(f"[Fragment Gift] Gift details - Username: @{clean_username}, Months: {months}")
        
        # 验证参数
        if not clean_username:
            logger.error("❌ [Fragment Gift] Username 为空，无法继续")
            return {'ok': False, 'error': 'Username is empty'}
        
        if months not in [3, 6, 12]:
            logger.error(f"❌ [Fragment Gift] 无效的月数: {months}，必须是 3、6 或 12")
            return {'ok': False, 'error': f'Invalid months: {months}, must be 3, 6, or 12'}
        
        # 使用浏览器精确复刻的方法
        logger.info("[Fragment Gift] 使用浏览器精确复刻方法: gift_premium_by_username")
        result = self.api.gift_premium_by_username(clean_username, months)
        
        if result.get('ok'):
            logger.info(f"✅ [Fragment Gift] 会员开通成功！Username: @{clean_username}, 月数: {months}")
            logger.info(f"[Fragment Gift] API 响应: {result}")
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"❌ [Fragment Gift] 会员开通失败: {error_msg}")
            logger.error(f"[Fragment Gift] 完整响应: {result}")
            logger.error(f"[Fragment Gift] 建议: 检查 fragment_auth.json 中的认证数据是否过期")
            logger.error(f"[Fragment Gift] 建议: 确认 @{clean_username} 是有效的 Telegram 用户名")
        
        return result
    
    def get_premium_info(self):
        """
        获取 Premium 信息
        
        Returns:
            dict: Premium 信息
        """
        if not self._initialized:
            raise Exception("未初始化，请先调用 initialize()")
        
        return self.api.get_premium_info()


# 使用示例
def main():
    """测试示例"""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    premium = FragmentPremium('fragment_auth.json')
    
    try:
        # 初始化
        if premium.initialize():
            print("✅ 初始化成功")
            
            # 获取 Premium 信息
            info = premium.get_premium_info()
            if info.get('ok'):
                print(f"✅ Premium 信息获取成功: {info}")
            else:
                print(f"⚠️ Premium 信息获取失败: {info.get('error')}")
            
            # 赠送会员（测试时注释掉）
            # result = premium.gift_premium("johndoe", months=12)  # 使用 @username
            # if result.get('ok'):
            #     print("✅ 会员开通成功！")
            # else:
            #     print(f"❌ 失败: {result.get('error')}")
        else:
            print("❌ 初始化失败")
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
