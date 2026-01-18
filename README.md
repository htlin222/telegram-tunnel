# Telegram Tunnel

A Telegram bot that acts as a remote shell session. Execute shell commands from your phone via Telegram.

## Setup

1. **Install dependencies**
   ```bash
   uv sync
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and user ID
   ```

3. **Get your Telegram bot token**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the token to `.env`

4. **Get your Telegram user ID**
   - Message [@userinfobot](https://t.me/userinfobot)
   - Copy your ID to `.env`

## Usage

### Running the bot

```bash
make dev      # Foreground mode (for development)
make run      # Background mode
make stop     # Stop background bot
make restart  # Restart background bot
make status   # Check if running
make log      # View log file
make log-tail # Follow log in real-time
```

### Auto-start on macOS login

```bash
make install   # Register LaunchAgent
make uninstall # Remove LaunchAgent
```

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start session |
| `/help` | Show help |
| `/pwd` | Show current directory (with bookmark button) |
| `/cd <path>` | Change directory |
| `/home` | Go to home directory |
| `/bookmark` | Show saved bookmarks |

Any other text is executed as a shell command.

## Security

### User whitelist
Only users listed in `ALLOWED_USERS` can use the bot. Configure in `.env`:
```
ALLOWED_USERS=123456789,987654321
```

### Command blacklist
Block dangerous commands in `blacklist_cmd.txt` (one per line):
```
rm
sudo
```

### Directory blacklist
Block access to sensitive directories in `blacklist_dir.txt`:
```
~/.ssh
~/API
```

## Files

| File | Description |
|------|-------------|
| `bot.py` | Main bot code |
| `.env` | Environment variables (gitignored) |
| `blacklist_cmd.txt` | Blocked commands (gitignored) |
| `blacklist_dir.txt` | Blocked directories (gitignored) |
| `*.template.txt` | Templates for blacklists |
| `launchd.plist.template` | macOS LaunchAgent template |

## License

MIT
