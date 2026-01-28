import os
import socket
import subprocess
from datetime import datetime

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

# Set your Telegram user ID(s) here for security
# Get your ID by messaging @userinfobot on Telegram
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS: set[int] = {
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_USERS", "").split(",")
    if uid.strip()
}

# Current working directory for the shell session
cwd = os.getcwd()

# Bookmarks storage
bookmarks: list[str] = []

# Bot start time
START_TIME = datetime.now()

# Device name (for identifying multiple instances)
device_name = os.environ.get("DEVICE_NAME", socket.gethostname())

# Blacklists
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_blacklist(filename: str) -> set[str]:
    """Load blacklist from file."""
    path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}


def is_cmd_blocked(command: str) -> str | None:
    """Check if command starts with a blocked command. Returns blocked cmd or None."""
    blocked_cmds = load_blacklist("blacklist_cmd.txt")
    cmd_parts = command.split()
    if not cmd_parts:
        return None
    first_cmd = cmd_parts[0]
    for blocked in blocked_cmds:
        if first_cmd == blocked or command.startswith(blocked + " "):
            return blocked
    return None


def is_dir_blocked(path: str) -> bool:
    """Check if path is in blocked directories."""
    blocked_dirs = load_blacklist("blacklist_dir.txt")
    normalized = os.path.normpath(os.path.expanduser(path))
    for blocked in blocked_dirs:
        blocked_norm = os.path.normpath(os.path.expanduser(blocked))
        if normalized == blocked_norm or normalized.startswith(blocked_norm + os.sep):
            return True
    return False


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use the bot."""
    if not ALLOWED_USERS:
        return True  # No restrictions if empty
    return user_id in ALLOWED_USERS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    await update.message.reply_text(
        f"Shell session started.\n"
        f"CWD: {cwd}\n"
        f"Send any command to execute.\n"
        f"Use /cd <path> to change directory."
    )


async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change directory."""
    global cwd

    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text(f"Current directory: {cwd}")
        return

    new_path = " ".join(context.args)

    # Expand ~ and environment variables like $HOME
    new_path = os.path.expandvars(os.path.expanduser(new_path))

    # Handle relative and absolute paths
    if os.path.isabs(new_path):
        target = new_path
    else:
        target = os.path.join(cwd, new_path)

    target = os.path.normpath(target)

    if is_dir_blocked(target):
        await update.message.reply_text(f"🚫 Access denied: {target}")
        return

    if os.path.isdir(target):
        cwd = target
        keyboard = [
            [
                InlineKeyboardButton(
                    "Add to bookmark", callback_data=f"bookmark_add:{cwd}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"📁 Changed to: {cwd}", reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(f"Directory not found: {target}")


async def home_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change to home directory."""
    global cwd

    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    cwd = os.path.expanduser("~")
    await update.message.reply_text(f"Changed to: {cwd}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help message."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    help_text = (
        "Shell Bot Commands:\n\n"
        "/start - Start session\n"
        "/help - Show this help\n"
        "/cd <path> - Change directory\n"
        "/home - Go to home directory\n"
        "/pwd - Show current directory\n"
        "/status - Show server status\n"
        "/device - View/set device name\n"
        "/bookmark - Show bookmarks\n\n"
        "Any other text runs as shell command."
    )
    await update.message.reply_text(help_text)


async def pwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current directory."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    keyboard = [
        [InlineKeyboardButton("Add to bookmark", callback_data=f"bookmark_add:{cwd}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"📁 {cwd}", reply_markup=reply_markup)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show server status."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    # Get hostname and IP
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip = "Unknown"

    # Calculate uptime
    uptime = datetime.now() - START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        uptime_str = f"{minutes}m {seconds}s"
    else:
        uptime_str = f"{seconds}s"

    status_text = (
        f"🖥️ {device_name} ({ip})\n\n"
        f"Hostname: {hostname}\n"
        f"CWD: {cwd}\n"
        f"Uptime: {uptime_str}\n"
        f"Started: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await update.message.reply_text(status_text)


async def device_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View or set device name."""
    global device_name

    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    # Get IP for display
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        ip = "Unknown"

    if not context.args:
        await update.message.reply_text(
            f"🖥️ {device_name} ({ip})\n\nUse /device <name> to change."
        )
        return

    device_name = " ".join(context.args)
    await update.message.reply_text(f"✅ Device name set to: {device_name} ({ip})")


async def bookmark_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bookmarks list."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    if not bookmarks:
        await update.message.reply_text("No bookmarks yet. Use /pwd to add one.")
        return

    keyboard = []
    for path in bookmarks:
        short_path = path if len(path) <= 30 else "..." + path[-27:]
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"📁 {short_path}", callback_data=f"bookmark_cd:{path}"
                ),
                InlineKeyboardButton("❌", callback_data=f"bookmark_rm:{path}"),
            ]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bookmarks:", reply_markup=reply_markup)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    global cwd

    query = update.callback_query
    if not is_authorized(query.from_user.id):
        await query.answer("Unauthorized.")
        return

    await query.answer()
    data = query.data

    if data.startswith("bookmark_add:"):
        path = data[13:]
        if path not in bookmarks:
            bookmarks.append(path)
            await query.edit_message_text(f"📁 {path}\n✅ Bookmarked!")
        else:
            await query.edit_message_text(f"📁 {path}\n(already bookmarked)")

    elif data.startswith("bookmark_cd:"):
        path = data[12:]
        if is_dir_blocked(path):
            await query.edit_message_text(f"🚫 Access denied: {path}")
        elif os.path.isdir(path):
            cwd = path
            await query.edit_message_text(f"📁 Changed to: {cwd}")
        else:
            await query.edit_message_text(f"Directory not found: {path}")

    elif data.startswith("bookmark_rm:"):
        path = data[12:]
        if path in bookmarks:
            bookmarks.remove(path)
        if not bookmarks:
            await query.edit_message_text("Bookmarks: (empty)")
        else:
            keyboard = []
            for p in bookmarks:
                short_path = p if len(p) <= 30 else "..." + p[-27:]
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"📁 {short_path}", callback_data=f"bookmark_cd:{p}"
                        ),
                        InlineKeyboardButton("❌", callback_data=f"bookmark_rm:{p}"),
                    ]
                )
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Bookmarks:", reply_markup=reply_markup)


async def execute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute shell command and return output."""
    global cwd

    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return

    command = update.message.text

    if not command:
        return

    blocked = is_cmd_blocked(command)
    if blocked:
        await update.message.reply_text(f"🚫 Command blocked: {blocked}")
        return

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr

        if not output:
            output = f"(exit code: {result.returncode})"

        # Telegram message limit is 4096 chars
        if len(output) > 4000:
            output = output[:4000] + "\n... (truncated)"

        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("Command timed out (60s limit).")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def post_init(application: Application) -> None:
    """Set up bot menu commands."""
    commands = [
        BotCommand("status", "Show server status"),
        BotCommand("device", "View/set device name"),
        BotCommand("home", "Go to home directory"),
        BotCommand("bookmark", "Show bookmarks"),
        BotCommand("start", "Start session"),
        BotCommand("help", "Show help"),
        BotCommand("cd", "Change directory"),
        BotCommand("pwd", "Show current directory"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Start the bot."""
    if not BOT_TOKEN:
        print("Error: Set TELEGRAM_BOT_TOKEN environment variable")
        print("Get a token from @BotFather on Telegram")
        return

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cd", cd_command))
    app.add_handler(CommandHandler("home", home_command))
    app.add_handler(CommandHandler("pwd", pwd_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("device", device_command))
    app.add_handler(CommandHandler("bookmark", bookmark_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, execute_command))

    print(f"Bot starting... CWD: {cwd}")
    print("Press Ctrl+C to stop")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
