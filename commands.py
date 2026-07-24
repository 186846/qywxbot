"""
命令处理模块
支持 /help、/ping、/time、/info 等命令，可自由扩展
"""
import time as _time
from datetime import datetime
from typing import Callable, Awaitable

# 命令处理函数的类型别名
CommandHandler = Callable[[], Awaitable[str]]

# 命令注册表
_commands: dict[str, tuple[str, CommandHandler]] = {}

START_TIME = datetime.now()


def register(command: str, description: str):
    """装饰器：注册命令处理器"""

    def decorator(func: CommandHandler):
        _commands[command] = (description, func)
        return func

    return decorator


def get_all_commands() -> dict[str, tuple[str, CommandHandler]]:
    """获取所有已注册的命令"""
    return _commands


async def handle_command(text: str) -> str | None:
    """解析并执行命令，返回结果字符串；如果不是命令则返回 None"""
    text = text.strip()
    if not text.startswith("/"):
        return None

    # 分离命令和参数
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd in _commands:
        handler = _commands[cmd][1]
        return await handler()
    return None


# ==============================
# 内置命令注册
# ==============================


@register("/help", "显示所有可用命令")
async def cmd_help() -> str:
    lines = ["### 📋 可用命令列表\n"]
    for cmd, (desc, _) in sorted(_commands.items()):
        lines.append(f"- **{cmd}** — {desc}")
    lines.append(f"\n---\n💡 直接发送消息即可获得智能回复")
    return "\n".join(lines)


@register("/ping", "测试机器人是否在线")
async def cmd_ping() -> str:
    return "🏓 **pong!** 机器人在线运行中"


@register("/time", "显示当前时间")
async def cmd_time() -> str:
    now = datetime.now()
    return f"🕐 当前时间：**{now.strftime('%Y年%m月%d日 %H:%M:%S')}**"


@register("/info", "显示机器人运行信息")
async def cmd_info() -> str:
    from config import BotConfig

    uptime = datetime.now() - START_TIME
    days = uptime.days
    hours, rem = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    uptime_str = f"{days}天 {hours}小时 {minutes}分 {seconds}秒" if days else f"{hours}小时 {minutes}分 {seconds}秒"

    return "\n".join(
        [
            "### 🤖 机器人运行信息\n",
            f"- **Bot ID**: `{BotConfig.BOT_ID[:16]}...`",
            f"- **运行时长**: {uptime_str}",
            f"- **流式回复**: {'🟢 开启' if BotConfig.ENABLE_STREAM_REPLY else '🔴 关闭'}",
            f"- **命令系统**: {'🟢 开启' if BotConfig.ENABLE_COMMANDS else '🔴 关闭'}",
            f"- **启动时间**: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )


@register("/echo", "复读你发送的内容（测试用）")
async def cmd_echo() -> str:
    return "请使用格式：`/echo 你想说的话`"


@register("/us", "生成隔夜美股早报（全板块，约15秒）")
async def cmd_us() -> str:
    from stock_report import generate_report

    return await generate_report()


@register("/usq", "美股早报快速版（仅指数+科技巨头，约5秒）")
async def cmd_usq() -> str:
    from stock_report import generate_quick_report

    return await generate_quick_report()
