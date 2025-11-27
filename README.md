# Telegram Advertising Bot

一个功能丰富的 Telegram 广告群发机器人，支持多账户管理、目标用户列表、消息模板和代理池。

A feature-rich Telegram advertising bot with multi-account management, target user lists, message templates, and proxy pool support.

## Features | 功能特点

### 1. Account Management | 账户管理
- Import accounts via `.session` files
- Auto-validate account login status
- Monitor account status (restricted, can send messages, etc.)
- Support proxy configuration per account

### 2. Target User Management | 目标用户管理
- Upload `.txt` files with target users
- Support usernames, user IDs, and phone numbers
- Automatic deduplication
- Blacklist functionality

### 3. Message Sending | 消息发送
- Custom message templates
- Support for text, photos, documents, and videos
- Channel message forwarding
- Interactive buttons with links
- Template variables ({username}, {user_id}, etc.)
- Multi-account rotation
- Smart error handling

### 4. Proxy Support | 代理支持
- HTTP and SOCKS5 proxy support
- Add, modify, delete, and test proxies
- Proxy pool rotation
- Per-account proxy assignment

### 5. User Interface | 用户界面
- Interactive Telegram button menus
- Session/account management
- Target list management
- Template editing
- Proxy configuration
- Task start/pause/cancel
- Real-time progress display

### 6. Security & Rate Limiting | 安全控制
- Configurable message delay
- Account switch intervals
- Concurrent task limits
- Comprehensive logging

### 7. Task Management | 任务管理
- Task scheduling
- Pause/resume/cancel tasks
- Export reports

## Installation | 安装

### Prerequisites | 前提条件
- Python 3.9+
- Telegram API credentials (get from https://my.telegram.org)
- Bot token (get from @BotFather)

### Setup | 设置

1. Clone the repository:
```bash
git clone https://github.com/biot9999/ggbot.git
cd ggbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. Run the bot:
```bash
python bot.py
```

## Configuration | 配置

Edit `.env` file with your settings:

```env
# Telegram Bot Token (from @BotFather)
BOT_TOKEN=your_bot_token_here

# Telegram API Credentials (from https://my.telegram.org)
API_ID=your_api_id
API_HASH=your_api_hash

# Admin User IDs (comma-separated numeric IDs, not usernames)
# Get your user ID by messaging @userinfobot on Telegram
# Example with single admin: ADMIN_IDS=123456789
# Example with multiple admins: ADMIN_IDS=123456789,987654321
ADMIN_IDS=123456789

# Rate Limiting
MESSAGE_DELAY_MIN=5
MESSAGE_DELAY_MAX=15
ACCOUNT_SWITCH_DELAY=30
MAX_CONCURRENT_TASKS=3
```

### Finding Your Telegram User ID | 获取用户 ID

To get your Telegram user ID:
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. The bot will reply with your user ID (a numeric value like `123456789`)
3. Use this **numeric ID** in `ADMIN_IDS`, **not** your username

**Important:** Do not use `@username` format. Only numeric user IDs are supported.

## Usage | 使用方法

### Bot Commands | 机器人命令

- `/start` - Show main menu | 显示主菜单
- `/help` - Show help guide | 显示帮助
- `/status` - Show bot status | 显示状态
- `/stats` - Show statistics | 显示统计
- `/ping` - Health check | 健康检查

### Workflow | 工作流程

1. **Upload Sessions** | 上传会话文件
   - Go to Accounts → Upload Session
   - Send your `.session` file

2. **Upload Targets** | 上传目标
   - Go to Targets → Upload Target List
   - Send a `.txt` file with one target per line

3. **Create Template** | 创建模板
   - Go to Templates → Create Text/Media/Forward Template
   - Follow the prompts

4. **Configure Proxies** (optional) | 配置代理
   - Go to Proxies → Add Proxy
   - Enter proxy details

5. **Create Task** | 创建任务
   - Go to Tasks → Create Task
   - Select accounts, targets, and template
   - Start the task

### Template Variables | 模板变量

Use these variables in your message templates:

| Variable | Description |
|----------|-------------|
| `{username}` | Target's username |
| `{user_id}` | Target's user ID |
| `{first_name}` | Target's first name |
| `{last_name}` | Target's last name |
| `{date}` | Current date |
| `{time}` | Current time |

### Adding Buttons | 添加按钮

Add buttons to templates using this format:
```
Your message text here.

[Button Text](https://your-url.com)
[Another Button](https://another-url.com)
```

## Directory Structure | 目录结构

```
ggbot/
├── bot.py              # Main application
├── requirements.txt    # Dependencies
├── .env.example        # Example configuration
├── src/
│   ├── config.py       # Configuration
│   ├── models/         # Data models
│   ├── services/       # Business logic
│   ├── handlers/       # Bot handlers
│   └── utils/          # Utilities
├── data/
│   ├── sessions/       # Session files
│   ├── targets/        # Target lists
│   └── proxies/        # Proxy config
└── logs/               # Log files
```

## Security Notes | 安全注意事项

⚠️ **Important:**
- Never share your `.session` files
- Keep your `.env` file private
- Use proxies to reduce ban risk
- Set appropriate rate limits
- Monitor account status regularly

## License | 许可证

MIT License

## Contributing | 贡献

Pull requests are welcome. For major changes, please open an issue first.

## Support | 支持

If you have questions or issues, please open a GitHub issue.
