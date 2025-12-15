# 🤖 Telegram Premium 自动赠送机器人

一个功能完整的 Telegram 机器人，支持用户通过 USDT (TRC20) 支付购买 Telegram Premium 和 Stars，支付成功后自动通过 Fragment.com 账号赠送给用户或好友。

## ✨ 核心功能

### 用户端功能
- 🛍️ 选择 Premium 套餐（3/6/12个月）或 Stars 套餐
- 💎 为自己购买或赠送给好友
- 💳 生成 USDT (TRC20) 支付二维码和收款地址
- ✅ 支付后点击"我已支付"按钮
- 🔍 自动验证支付到账
- 🎁 支付成功后自动开通 Premium 或充值 Stars
- 📬 发送开通成功通知
- 👤 用户中心查看订单历史和统计信息
- 📋 订单分页浏览和详情查看
- ❌ /cancel 命令随时取消当前操作

### 管理员端功能
- 🔐 手动认证方式（避免账号冻结）
- 🌐 纯 API 调用 Fragment.com（无需浏览器）
- 📊 完整的统计面板（订单、收入、用户统计）
- 🎁 自动调用 Fragment API 赠送 Premium
- 💵 会员和 Stars 价格可由管理员自定义设置
- 🔄 自动重试机制提高成功率
- ✅ 无系统依赖，只需 Python 包
- ⚡ 速度快，资源占用少

### 支付系统
- 💎 支持 USDT (TRC20) 支付
- 🔗 集成 TronGrid API 监控区块链交易
- 🎯 自动匹配订单和支付
- ⚡ 支付确认后触发自动开通
- 🛡️ 识别真假 USDT 功能，防止假付款
- 🔄 支持手动验证支付状态
- ⏰ 30分钟支付超时自动取消

### 数据管理
- 📋 订单状态管理（pending/paid/completed/failed/expired/cancelled）
- 👥 用户会员信息管理
- 📝 交易日志记录
- 🎁 礼物赠送记录
- 📊 用户统计数据

### UI/UX 优化
- 🎨 美化的2列网格主菜单
- 💎 优化的Premium和Stars购买页面
- 📦 详细的订单信息展示
- 💳 清晰的支付信息和防诈骗提示
- 👤 完整的用户中心界面
- ↩️ 所有页面均有返回主菜单按钮

## 🔧 技术栈

### 后端框架
- **Python 3.8+**
- **python-telegram-bot** - Telegram Bot API
- **MongoDB** - 数据库
- **requests** - Fragment API 调用

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

> **注意**: 新版本使用纯 API 方式，无需安装浏览器或系统依赖库。

### 3. 安装 MongoDB
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

### 快速启动（推荐）
使用提供的启动脚本：
```bash
./start.sh
```

脚本会自动：
- 检查 .env 配置
- 创建虚拟环境
- 安装依赖
- 启动机器人

### 手动启动
```bash
python bot.py
```

### 生产环境部署（使用 systemd）
1. 编辑 `telegram-premium-bot.service` 文件，修改路径和用户
2. 复制到 systemd 目录：
```bash
sudo cp telegram-premium-bot.service /etc/systemd/system/
```
3. 启用并启动服务：
```bash
sudo systemctl enable telegram-premium-bot
sudo systemctl start telegram-premium-bot
```
4. 查看状态：
```bash
sudo systemctl status telegram-premium-bot
```

### 用户命令
- `/start` - 开始使用机器人，显示主菜单
- `/buy` - 购买 Premium 会员
- `/status` - 查看用户中心和订单统计
- `/help` - 获取帮助信息
- `/cancel` - 取消当前操作，返回主菜单
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

### 5. 配置 Fragment 认证

本项目采用**手动认证模式**来避免账号冻结风险。

#### 为什么使用手动认证？

- ✅ **避免账号冻结**：不使用 Telethon 完整登录，不会触发 Telegram 反滥用机制
- ✅ **无需验证码**：只需在浏览器点击确认，符合 Fragment 正常登录流程
- ✅ **长期稳定**：认证数据可长期使用，无需频繁重新登录
- ✅ **安全可控**：完全手动控制，认证数据本地保存

#### 📖 获取 Fragment 认证数据

**步骤 1：在浏览器登录 Fragment**

1. 访问 https://fragment.com
2. 点击右上角 **"Login"** 按钮
3. Telegram 会收到登录确认请求
4. 在 Telegram 中点击 **"Confirm"** 确认登录
5. ✅ 登录成功

**步骤 2：打开浏览器开发者工具**

- **Chrome/Edge**: 按 `F12` 或 `Ctrl+Shift+I`（Windows）/ `Cmd+Option+I`（Mac）
- **Firefox**: 按 `F12`
- **Safari**: 按 `Cmd+Option+I`（需先在偏好设置中启用开发者菜单）

**步骤 3：获取 Cookies**

1. 在开发者工具中点击 **"Application"**（应用程序）或 **"Storage"**（存储）标签
2. 左侧菜单选择 **"Cookies"** → `https://fragment.com`
3. 找到并复制以下 cookie 的值：
   - `stel_ssid` - Session ID
   - `stel_token` 或 `stel_ton_token` - Token
   - `stel_dt` - 时区偏移（通常是 `-480`）

**步骤 4：获取 Hash**

**方法一：从 Network 请求中获取**

1. 点击 **"Network"**（网络）标签
2. 刷新页面（`F5`）
3. 在请求列表中查找 `api?hash=...` 的请求
4. 点击该请求，查看 URL 中的 `hash` 参数
5. 复制 `hash` 的值

**方法二：从 Console 获取（如果可用）**

1. 点击 **"Console"**（控制台）标签
2. 输入 `document.cookie` 并回车
3. 查找并复制相关 cookie 值

**步骤 5：创建配置文件**

```bash
# 复制示例文件
cp fragment_auth.json.example fragment_auth.json

# 编辑配置
nano fragment_auth.json
```

填入刚才获取的值：

```json
{
  "hash": "你复制的完整hash值",
  "cookies": {
    "stel_ssid": "你复制的stel_ssid值",
    "stel_token": "你复制的token值",
    "stel_dt": "-480"
  },
  "headers": {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://fragment.com",
    "Referer": "https://fragment.com/"
  }
}
```

**步骤 6：测试配置**

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 运行测试脚本
python test_fragment_auth.py
```

如果配置正确，应该显示：

```
✅ 认证数据加载成功
✅ 连接成功！
🎉 Fragment 认证配置正确，可以正常使用
```

#### ⚠️ 注意事项

1. **保护敏感数据**
   - 🔒 **切勿提交** `fragment_auth.json` 到 Git
   - 🔒 不要分享你的 hash 和 cookies
   - 🔒 定期更换认证数据以提高安全性

2. **认证过期处理**
   - 如果认证过期（通常几周到几个月），重新从浏览器获取即可
   - 机器人会提示认证失败，按上述步骤重新配置

3. **多账号配置**
   - 如需使用不同账号，创建不同的配置文件（如 `fragment_auth_account2.json`）
   - 在代码中指定不同的配置文件路径

#### 🔧 故障排除

**问题：认证数据加载失败**

```
❌ 认证文件不存在: fragment_auth.json
```

**解决：** 确保 `fragment_auth.json` 文件存在且格式正确

---

**问题：连接测试失败**

```
❌ Fragment 连接测试失败
```

**可能原因：**
- 认证数据已过期 → 重新从浏览器获取
- 网络问题 → 检查服务器是否能访问 fragment.com
- Fragment 服务暂时不可用 → 稍后重试

---

**问题：API 调用返回 Bad Request**

```
API Response: {'error': 'Bad request'}
```

**可能原因：**
- Hash 或 cookies 不正确 → 重新复制，确保完整无误
- 认证已过期 → 重新登录并获取新数据

## 🎁 Fragment 会员开通功能

### 特点
- ✅ 使用手动认证，避免账号冻结
- ✅ 纯 API 调用，无需浏览器
- ✅ 无需验证码，符合正常登录流程
- ✅ 支持自动开通和赠送会员
- ✅ 速度快，资源占用少
- ✅ 认证数据长期有效

### 技术架构
使用**手动认证 + Fragment API** 方式：

```
浏览器登录 → 获取认证数据 → 保存到配置文件 → 机器人使用认证调用 API
```

### 优势对比

| 特性 | Telethon 登录 | 手动认证（新方案） |
|------|--------------|-------------------|
| 需要验证码 | ❌ 是 | ✅ 否 |
| 账号冻结风险 | 🔴 高 | 🟢 极低 |
| 配置复杂度 | 🟡 中等 | 🟢 简单 |
| 认证稳定性 | 🟡 需定期重新登录 | 🟢 长期有效 |
| 用户体验 | 🟡 需要输入验证码 | 🟢 仅需浏览器点击确认 |

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
├── bot.py                          # 主机器人文件（重构后）
├── config.py                       # 配置管理
├── database.py                     # 数据库操作（扩展统计功能）
├── payment.py                      # 支付系统
├── fragment.py                     # Fragment 自动化（改进登录）
├── keyboards.py                    # 按钮布局管理（新增）
├── messages.py                     # 消息模板管理（新增）
├── utils.py                        # 工具函数（新增）
├── constants.py                    # 常量定义（新增）
├── requirements.txt                # 依赖列表
├── start.sh                        # 启动脚本
├── telegram-premium-bot.service    # Systemd 服务文件
├── .env.example                    # 环境变量示例
├── .gitignore                      # Git 忽略文件
└── README.md                       # 项目文档
```

### 代码架构改进
本次更新重构了代码结构，提高了可维护性：

- **keyboards.py**: 统一管理所有按钮布局，包括主菜单、购买页面、管理员面板等
- **messages.py**: 统一管理所有消息模板，便于统一修改文案
- **utils.py**: 通用工具函数，如时间格式化、用户名验证、日志记录等
- **constants.py**: 常量定义，避免硬编码
- **database.py**: 扩展了统计方法，支持订单、收入、用户统计
- **fragment.py**: 改进了登录流程，增加了重试机制和更详细的错误处理
- **bot.py**: 完全重构，使用模块化设计，支持所有新功能
├── fragment.py                     # Fragment 自动化
├── requirements.txt                # 依赖列表
├── start.sh                        # 启动脚本
├── telegram-premium-bot.service    # Systemd 服务文件
├── .env.example                    # 环境变量示例
├── .gitignore                      # Git 忽略文件
└── README.md                       # 项目文档
```

### 扩展功能
本项目已实现的高级功能：
- 🎁 **为他人购买**: 支持购买 Premium 后赠送给好友
- ⭐ **Stars 购买**: 支持购买 Telegram Stars（基础实现）
- 📊 **统计面板**: 管理员可查看完整的订单、收入、用户统计
- 👤 **用户中心**: 用户可查看个人订单历史和消费统计
- 🎨 **UI 美化**: 2列网格布局、优化的消息格式、清晰的信息展示
- ↩️ **便捷导航**: 所有页面都有返回主菜单的按钮
- ❌ **取消功能**: /cancel 命令可随时取消当前操作
- 🔄 **重试机制**: Fragment 操作失败自动重试
- 📝 **详细日志**: 完整的操作日志记录

可以考虑继续添加：
- 🌍 多语言支持
- 💳 更多支付方式（如 TON、ETH）
- 🔔 订单状态推送通知
- 💬 客服系统
- 🎫 优惠券系统
- 💰 用户余额充值功能

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
  ```bash
  grep TELEGRAM_BOT_TOKEN .env
  ```
- 确认 MongoDB 已启动
  ```bash
  sudo systemctl status mongodb
  ```
- 查看详细错误日志
  ```bash
  python bot.py
  ```

### 支付检测不到
- 确认 TronGrid API 配置正确
- 检查钱包地址是否正确
  ```bash
  grep PAYMENT_WALLET_ADDRESS .env
  ```
- 确保用户使用了 TRC20 网络
- 检查 TronGrid API 额度是否用完
- 手动测试 TronGrid API：
  ```bash
  curl "https://api.trongrid.io/v1/accounts/YOUR_ADDRESS/transactions/trc20?limit=10"
  ```

### Fragment 登录失败
- 确保安装了 Playwright 浏览器
  ```bash
  playwright install chromium
  ```
- 检查网络连接
- 尝试重新登录
  ```bash
  rm fragment_session.json
  # 然后在机器人中使用 /login 命令
  ```
- 在服务器上运行需要图形界面或 Xvfb

### MongoDB 连接失败
- 确认 MongoDB 服务已启动
  ```bash
  sudo systemctl start mongodb
  ```
- 检查 MongoDB URI 配置
  ```bash
  grep MONGODB_URI .env
  ```
- 测试 MongoDB 连接
  ```bash
  mongo --eval "db.version()"
  ```

### 依赖安装失败
- 更新 pip
  ```bash
  pip install --upgrade pip
  ```
- 安装系统依赖（Ubuntu/Debian）
  ```bash
  sudo apt-get install python3-dev libpq-dev
  ```
- 使用虚拟环境
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

### 日志查看
- 查看 systemd 服务日志
  ```bash
  sudo journalctl -u telegram-premium-bot -f
  ```
- 查看实时日志
  ```bash
  python bot.py  # 直接运行查看输出
  ```

## 📝 License

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请通过 GitHub Issues 联系。
