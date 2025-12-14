# 🤖 Telegram Premium 自动赠送机器人

一个功能完整的 Telegram 机器人，支持用户通过 USDT (TRC20) 支付购买 Telegram Premium，支付成功后自动通过 Fragment.com 账号赠送 Premium 给用户。

## ✨ 核心功能

### 用户端功能
- 🛍️ 选择 Premium 套餐（3/6/12个月）
- 💳 生成 USDT (TRC20) 支付二维码和收款地址
- ✅ 支付后点击"我已支付"按钮
- 🔍 自动验证支付到账
- 🎁 支付成功后自动开通 Premium
- 📬 发送开通成功通知

### 管理员端功能
- 🔐 Fragment.com 账号配置工具
- 🌐 浏览器自动化登录 Fragment 并保存 session
- 💰 自动检查 Fragment 账户余额
- 📊 后台监控 USDT 支付
- 🎁 自动调用 Fragment 赠送 Premium
- 💵 会员价格可由管理员自定义设置

### 支付系统
- 💎 支持 USDT (TRC20) 支付
- 🔗 集成 TronGrid API 监控区块链交易
- 🎯 自动匹配订单和支付
- ⚡ 支付确认后触发自动开通
- 🛡️ 识别真假 USDT 功能，防止假付款
- 🔄 支持手动验证支付状态

### 数据管理
- 📋 订单状态管理（pending/paid/completed/failed/expired/cancelled）
- 👥 用户会员信息管理
- 📝 交易日志记录

## 🔧 技术栈

### 后端框架
- **Python 3.8+**
- **python-telegram-bot** - Telegram Bot API
- **Playwright** - 浏览器自动化（操作 Fragment.com）
- **aiohttp** - 异步 HTTP 请求
- **MongoDB** - 数据库

### 支付集成
- **TronGrid API** - 监控 TRC20 USDT 交易
- 真假 USDT 验证机制

### 其他工具
- **qrcode** - 生成支付二维码
- **asyncio** - 异步任务处理
- **python-dotenv** - 环境变量管理

## 📦 安装步骤

### 1. 克隆项目
```bash
git clone https://github.com/biot9999/ggbot.git
cd ggbot
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 安装 Playwright 浏览器
```bash
playwright install chromium
```

### 4. 安装 MongoDB
根据你的操作系统安装 MongoDB：
- **Ubuntu/Debian**: `sudo apt install mongodb`
- **macOS**: `brew install mongodb-community`
- **Windows**: 从官网下载安装

### 5. 配置环境变量
复制 `.env.example` 为 `.env` 并填写配置：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
# Telegram Bot Token（从 @BotFather 获取）
TELEGRAM_BOT_TOKEN=your_bot_token_here

# 管理员用户 ID（多个用逗号分隔）
ADMIN_USER_IDS=123456789,987654321

# MongoDB 配置
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=telegram_premium_bot

# TronGrid API Key（可选，从 https://www.trongrid.io 获取）
TRONGRID_API_KEY=your_trongrid_api_key

# USDT TRC20 合约地址（官方地址，不要修改）
USDT_TRC20_CONTRACT=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t

# 收款钱包地址（你的 TRC20 钱包地址）
PAYMENT_WALLET_ADDRESS=your_trc20_wallet_address

# 套餐价格（USDT）
PRICE_3_MONTHS=5.00
PRICE_6_MONTHS=9.00
PRICE_12_MONTHS=15.00

# 支付设置
PAYMENT_TIMEOUT=1800  # 30分钟
PAYMENT_CHECK_INTERVAL=30  # 30秒检查一次
```

## 🚀 使用方法

### 启动机器人
```bash
python bot.py
```

### 用户命令
- `/start` - 开始使用机器人
- `/buy` - 购买 Premium 会员
- `/status` - 查看订单状态
- `/help` - 获取帮助

### 管理员命令
- `/admin` - 管理员面板
- `/setprice <月数> <价格>` - 设置价格（例如：`/setprice 3 5.99`）
- `/balance` - 查看 Fragment 余额
- `/login` - 登录 Fragment 账号

## 📋 配置指南

### 1. 创建 Telegram Bot
1. 在 Telegram 中找到 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称和用户名
4. 复制获得的 Bot Token 到 `.env` 文件

### 2. 获取用户 ID
1. 在 Telegram 中找到 [@userinfobot](https://t.me/userinfobot)
2. 发送任意消息获取你的用户 ID
3. 将用户 ID 添加到 `.env` 的 `ADMIN_USER_IDS`

### 3. 配置 TRC20 钱包
1. 使用支持 TRC20 的钱包（如 TronLink、imToken）
2. 获取你的 TRC20 钱包地址
3. 将地址填入 `.env` 的 `PAYMENT_WALLET_ADDRESS`

### 4. 获取 TronGrid API Key（可选）
1. 访问 [TronGrid.io](https://www.trongrid.io)
2. 注册账号并创建 API Key
3. 将 API Key 填入 `.env`（免费版限制较多，建议使用）

### 5. 配置 Fragment.com
1. 启动机器人后，使用管理员账号发送 `/login`
2. 按提示完成 Fragment.com 登录
3. 登录信息会自动保存，无需重复登录

## 🔒 安全特性

### 假 USDT 检测
机器人会验证每笔交易的代币合约地址，确保：
- ✅ 只接受官方 USDT TRC20 合约的转账
- ✅ 拒绝假 USDT 代币
- ✅ 防止欺诈和假付款

### 支付验证流程
1. 检查交易是否存在于区块链
2. 验证代币合约地址是否为官方 USDT
3. 确认转账金额是否匹配订单
4. 验证收款地址是否正确

## 📊 系统架构

```
┌─────────────┐
│   用户      │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Telegram Bot       │
│  - 命令处理         │
│  - 订单管理         │
│  - 回调处理         │
└──────┬──────────────┘
       │
       ├────────────────────┐
       │                    │
       ▼                    ▼
┌─────────────┐    ┌──────────────┐
│  MongoDB    │    │  Payment     │
│  - 用户数据  │    │  - TronGrid  │
│  - 订单数据  │    │  - USDT验证  │
│  - 交易记录  │    │  - 支付监控  │
└─────────────┘    └──────────────┘
                           │
                           ▼
                   ┌──────────────┐
                   │  Fragment    │
                   │  - 登录管理   │
                   │  - Premium   │
                   │    赠送       │
                   └──────────────┘
```

## 🛠️ 开发说明

### 项目结构
```
ggbot/
├── bot.py              # 主机器人文件
├── config.py           # 配置管理
├── database.py         # 数据库操作
├── payment.py          # 支付系统
├── fragment.py         # Fragment 自动化
├── requirements.txt    # 依赖列表
├── .env.example        # 环境变量示例
├── .gitignore          # Git 忽略文件
└── README.md           # 项目文档
```

### 扩展功能
可以考虑添加：
- 🌍 多语言支持
- 💳 更多支付方式（如 TON、ETH）
- 📊 更详细的统计面板
- 🔔 订单状态推送通知
- 💬 客服系统
- 🎫 优惠券系统

## ⚠️ 注意事项

1. **安全性**
   - 不要泄露 Bot Token 和 API Keys
   - 妥善保管 MongoDB 数据库
   - 定期备份订单和交易数据

2. **合规性**
   - 确保在你的地区运营此类服务是合法的
   - 遵守 Telegram 服务条款
   - 遵守当地金融法规

3. **可靠性**
   - 建议使用稳定的服务器
   - 配置日志监控
   - 设置错误告警

4. **Fragment 自动化**
   - Fragment.com 的页面结构可能会变化
   - 需要定期测试和更新选择器
   - 建议添加错误重试机制

## 🐛 故障排除

### 机器人无法启动
- 检查 Bot Token 是否正确
- 确认 MongoDB 已启动
- 查看日志文件排查错误

### 支付检测不到
- 确认 TronGrid API 配置正确
- 检查钱包地址是否正确
- 确保用户使用了 TRC20 网络

### Fragment 登录失败
- 确保安装了 Playwright 浏览器
- 检查网络连接
- 尝试重新登录

## 📝 License

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请通过 GitHub Issues 联系。
