#!/usr/bin/env python3
"""
Fragment API 测试工具

用于调试 Fragment API 调用问题
测试不同的 API 方法和参数组合
"""

import logging
import sys
from fragment_premium import FragmentPremium

# 设置日志级别为 DEBUG 以查看详细信息
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fragment_api_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_connection():
    """测试 Fragment 连接"""
    logger.info("=" * 60)
    logger.info("测试 1: Fragment 连接测试")
    logger.info("=" * 60)
    
    premium = FragmentPremium('fragment_auth.json')
    
    if premium.initialize():
        logger.info("✅ 初始化成功")
        return premium
    else:
        logger.error("❌ 初始化失败")
        return None


def test_premium_info(premium):
    """测试获取 Premium 信息"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试 2: 获取 Premium 信息")
    logger.info("=" * 60)
    
    try:
        result = premium.get_premium_info()
        
        if result.get('ok'):
            logger.info("✅ Premium 信息获取成功")
            logger.info(f"   响应数据: {result}")
        else:
            logger.error(f"❌ Premium 信息获取失败")
            logger.error(f"   错误: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}", exc_info=True)
        return None


def test_gift_premium(premium, user_id: int, months: int = 3):
    """测试赠送 Premium (仅测试模式，不实际赠送)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"测试 3: 赠送 Premium (User ID: {user_id}, Months: {months})")
    logger.info("=" * 60)
    logger.warning("⚠️ 注意: 这将实际调用 API！确保 user_id 正确！")
    
    try:
        result = premium.gift_premium(user_id, months)
        
        if result.get('ok'):
            logger.info("✅ Premium 赠送成功")
            logger.info(f"   响应数据: {result}")
        else:
            logger.error(f"❌ Premium 赠送失败")
            logger.error(f"   错误: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}", exc_info=True)
        return None


def test_history(premium):
    """测试获取交易历史"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试 4: 获取交易历史")
    logger.info("=" * 60)
    
    try:
        result = premium.api.get_history()
        
        if result.get('ok'):
            logger.info("✅ 交易历史获取成功")
            logger.info(f"   响应数据: {result}")
        else:
            logger.error(f"❌ 交易历史获取失败")
            logger.error(f"   错误: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}", exc_info=True)
        return None


def main():
    """主测试函数"""
    logger.info("🧪 Fragment API 测试工具")
    logger.info("")
    logger.info("此工具用于调试 Fragment API 调用问题")
    logger.info("日志将同时输出到控制台和 fragment_api_test.log 文件")
    logger.info("")
    
    # 测试 1: 连接测试
    premium = test_connection()
    if not premium:
        logger.error("❌ 初始化失败，停止测试")
        sys.exit(1)
    
    # 测试 2: 获取 Premium 信息
    test_premium_info(premium)
    
    # 测试 3: 获取交易历史
    test_history(premium)
    
    # 测试 4: 赠送 Premium（需要用户确认）
    logger.info("")
    logger.info("=" * 60)
    logger.info("测试 5: 赠送 Premium (可选)")
    logger.info("=" * 60)
    
    user_input = input("\n是否要测试赠送 Premium？这将实际调用 API！(yes/no): ")
    
    if user_input.lower() in ['yes', 'y']:
        user_id = input("请输入目标 User ID: ")
        months = input("请输入月数 (3/6/12, 默认3): ") or "3"
        
        try:
            user_id = int(user_id)
            months = int(months)
            
            if months not in [3, 6, 12]:
                logger.error("❌ 月数必须是 3, 6 或 12")
            else:
                confirm = input(f"\n确认为 User ID {user_id} 赠送 {months} 个月 Premium? (yes/no): ")
                if confirm.lower() in ['yes', 'y']:
                    test_gift_premium(premium, user_id, months)
                else:
                    logger.info("已取消测试")
        except ValueError:
            logger.error("❌ 输入格式错误")
    else:
        logger.info("已跳过赠送 Premium 测试")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 测试完成")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📊 测试总结:")
    logger.info("   - 检查上面的日志输出")
    logger.info("   - 如果出现 'Invalid method' 或 'Access denied' 错误:")
    logger.info("     1. 检查 fragment_auth.json 中的认证数据是否过期")
    logger.info("     2. 在浏览器中重新登录 fragment.com 并更新认证数据")
    logger.info("     3. 确认 cookies (stel_ssid, stel_token, stel_dt) 和 hash 都是最新的")
    logger.info("   - 详细日志已保存到 fragment_api_test.log")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⚠️ 用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\n❌ 发生错误: {e}", exc_info=True)
        sys.exit(1)
