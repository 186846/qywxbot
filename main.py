"""
企业微信智能机器人 - 纯文本收发 + 美股早报
基于 wecom-aibot-python-sdk
"""
import asyncio

from aibot import WSClient, WSClientOptions
from config import BotConfig
from commands import handle_command

# 需要"先显示加载提示再执行"的耗时命令
SLOW_COMMANDS = {"/us", "/usq"}


async def main():
    # 构建客户端
    options_kwargs = {
        "bot_id": BotConfig.BOT_ID,
        "secret": BotConfig.BOT_SECRET,
        "heartbeat_interval": BotConfig.HEARTBEAT_INTERVAL,
        "reconnect_interval": BotConfig.RECONNECT_INTERVAL,
        "max_reconnect_attempts": BotConfig.MAX_RECONNECT_ATTEMPTS,
    }
    if BotConfig.WS_URL:
        options_kwargs["ws_url"] = BotConfig.WS_URL

    ws = WSClient(WSClientOptions(**options_kwargs))

    # ---------- 连接事件 ----------
    @ws.on("authenticated")
    def on_auth():
        print("✅ 认证成功，机器人已上线")

    @ws.on("disconnected")
    def on_disconnected(reason):
        print(f"🔌 断开: {reason}")

    @ws.on("reconnecting")
    def on_reconnecting(attempt):
        print(f"🔄 重连中 ({attempt})")

    @ws.on("error")
    def on_error(err):
        print(f"❌ 错误: {err}")

    # ---------- 进入会话 ----------
    @ws.on("event.enter_chat")
    async def on_enter(frame):
        try:
            await ws.reply_welcome(
                frame,
                {"msgtype": "markdown", "markdown": {"content": BotConfig.WELCOME_TEXT}},
            )
        except Exception:
            pass

    # ---------- 文本消息 ----------
    @ws.on("message.text")
    async def on_text(frame):
        raw = frame.get("body", {}).get("text", {}).get("content", "").strip()
        if not raw:
            return

        print(f"📨 {raw}")

        # 群聊消息去掉 @机器人名' 前缀（如 @test' /usq → /usq）
        content = _strip_mention(raw)

        if BotConfig.ENABLE_COMMANDS and content.startswith("/"):
            cmd = content.split(maxsplit=1)[0].lower()

            # 耗时命令：先显示加载中
            if cmd in SLOW_COMMANDS:
                await _slow_reply(ws, frame, content)
                return

            # 普通命令
            result = await handle_command(content)
            if result:
                await _reply(ws, frame, result)
            return

        # 默认回复
        await _reply(ws, frame, f"收到：**{content}**")

    # ---------- 启动 ----------
    print(f"🚀 启动中... Bot ID: {BotConfig.BOT_ID[:20]}...")
    await ws.connect()
    print("⏳ 等待消息...")
    await asyncio.Event().wait()


async def _reply(ws: WSClient, frame: dict, content: str):
    """直接回复，不经过步骤"""
    await ws.reply(frame, {"msgtype": "markdown", "markdown": {"content": content}})


async def _slow_reply(ws: WSClient, frame: dict, content: str):
    """耗时命令：先发加载提示，执行完后发最终结果"""
    # 先发加载提示
    await ws.reply(frame, {"msgtype": "markdown", "markdown": {"content": "⏳ 正在抓取美股数据，请稍候..."}})

    # 执行命令
    try:
        result = await handle_command(content)
    except Exception as e:
        result = f"❌ 查询失败：{e}"

    # 发送最终结果
    await ws.reply(frame, {"msgtype": "markdown", "markdown": {"content": result or "未获取到数据"}})


def _strip_mention(text: str) -> str:
    """去掉群聊消息中的 @机器人名' 前缀"""
    mm = text.strip()
    # @xxx' 或 @xxx' （带空格分隔）→ 只保留后面的内容
    if mm.startswith("@"):
        idx = mm.find("'")
        if idx != -1:
            mm = mm[idx + 1:].strip()
        else:
            # 没有 ' 的情况，尝试空格分割 @name /cmd
            parts = mm.split(None, 1)
            mm = parts[1] if len(parts) > 1 else mm
    return mm


if __name__ == "__main__":
    if not BotConfig.validate():
        exit(1)
    BotConfig.display()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 已下线")
