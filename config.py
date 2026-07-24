"""
配置加载模块
从 .env 文件和系统环境变量中加载配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    """机器人配置类"""

    # ========== 基础配置 ==========
    BOT_ID: str = os.getenv("WECOM_BOT_ID", "")
    BOT_SECRET: str = os.getenv("WECOM_BOT_SECRET", "")

    # ========== 连接配置 ==========
    WS_URL: str = os.getenv("WECOM_WS_URL", "")  # 留空使用默认
    HEARTBEAT_INTERVAL: int = int(os.getenv("WECOM_HEARTBEAT_INTERVAL", "30000"))
    RECONNECT_INTERVAL: int = int(os.getenv("WECOM_RECONNECT_INTERVAL", "1000"))
    MAX_RECONNECT_ATTEMPTS: int = int(os.getenv("WECOM_MAX_RECONNECT_ATTEMPTS", "10"))

    # ========== 行为配置 ==========
    ENABLE_STREAM_REPLY: bool = os.getenv("ENABLE_STREAM_REPLY", "true").lower() == "true"
    STREAM_THINKING_TEXT: str = os.getenv("STREAM_THINKING_TEXT", "正在思考中...")
    WELCOME_TEXT: str = os.getenv(
        "WELCOME_TEXT",
        "您好！我是智能助手，有什么可以帮您的吗？\n\n您可以输入 `/help` 查看支持的命令。",
    )
    ENABLE_COMMANDS: bool = os.getenv("ENABLE_COMMANDS", "true").lower() == "true"
    ENABLE_AI_REPLY: bool = os.getenv("ENABLE_AI_REPLY", "false").lower() == "true"

    @classmethod
    def validate(cls) -> bool:
        """验证必填配置项"""
        if not cls.BOT_ID or not cls.BOT_SECRET:
            print("❌ 错误：请在 .env 文件中配置 WECOM_BOT_ID 和 WECOM_BOT_SECRET")
            return False
        return True

    @classmethod
    def display(cls):
        """打印当前配置（隐藏敏感信息）"""
        print("=" * 50)
        print("🤖 企业微信智能机器人配置")
        print("=" * 50)
        print(f"  Bot ID:       {cls.BOT_ID[:20]}...")
        print(f"  Secret:       {'*' * 16}")
        print(f"  WebSocket:    {cls.WS_URL or '默认官方地址'}")
        print(f"  心跳间隔:     {cls.HEARTBEAT_INTERVAL}ms")
        print(f"  重连间隔:     {cls.RECONNECT_INTERVAL}ms")
        print(f"  最大重连次数: {cls.MAX_RECONNECT_ATTEMPTS}")
        print(f"  流式回复:     {'开启' if cls.ENABLE_STREAM_REPLY else '关闭'}")
        print(f"  命令系统:     {'开启' if cls.ENABLE_COMMANDS else '关闭'}")
        print(f"  AI 回复:      {'开启' if cls.ENABLE_AI_REPLY else '关闭'}")
        print("=" * 50)
