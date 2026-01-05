import discord
from discord.ext import commands
import traceback
import asyncio
import aiohttp
from datetime import datetime

# =========================
# UniversalBot 基本設定
# =========================

BOT_NAME = "UniversalBot"

DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE"

# 管理用Webhook（ログ送信先）
LOG_WEBHOOK_URL = "https://discord.com/api/webhooks/XXXXXXXX/XXXXXXXX"

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

# =========================
# ログ送信ユーティリティ
# =========================

async def send_log(title: str, description: str, level: str = "INFO"):
    """
    管理Webhookにログを送信する
    level: INFO / WARNING / ERROR / CRITICAL
    """
    embed = {
        "title": f"[{level}] {title}",
        "description": description,
        "color": {
            "INFO": 0x3498db,
            "WARNING": 0xf1c40f,
            "ERROR": 0xe74c3c,
            "CRITICAL": 0x8e44ad
        }.get(level, 0x95a5a6),
        "timestamp": datetime.utcnow().isoformat()
    }

    payload = {
        "username": BOT_NAME,
        "embeds": [embed]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(LOG_WEBHOOK_URL, json=payload):
                pass
    except Exception as e:
        # Webhookが死んでもBot本体は止めない
        print("Webhook log failed:", e)


# =========================
# Botクラス定義
# =========================

class UniversalBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=INTENTS,
            help_command=None
        )

    async def setup_hook(self):
        """
        起動時にCogをロード
        """
        try:
            # 将来ここにCogを追加していく
            await self.load_extension("cogs.core")
            await send_log(
                "Startup",
                "Core cogs loaded successfully.",
                "INFO"
            )
        except Exception as e:
            await send_log(
                "Startup Error",
                f"Failed to load cogs:\n```{traceback.format_exc()}```",
                "CRITICAL"
            )

    async def on_ready(self):
        await send_log(
            "Bot Ready",
            f"{self.user} has connected to Discord.",
            "INFO"
        )
        print(f"{BOT_NAME} logged in as {self.user}")

    async def on_command_error(self, ctx, error):
        """
        コマンドエラーの一元管理
        """
        if isinstance(error, commands.CommandNotFound):
            return  # 無視（ログも不要）

        error_trace = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

        await send_log(
            "Command Error",
            f"User: {ctx.author}\n"
            f"Channel: {ctx.channel}\n"
            f"Command: {ctx.message.content}\n"
            f"```{error_trace}```",
            "ERROR"
        )

        try:
            await ctx.send("⚠️ 内部エラーが発生しました。管理者に通知されています。")
        except discord.Forbidden:
            pass

    async def on_error(self, event_method, *args, **kwargs):
        """
        Discordイベント全体の例外キャッチ
        """
        error_trace = traceback.format_exc()

        await send_log(
            "Event Error",
            f"Event: {event_method}\n```{error_trace}```",
            "CRITICAL"
        )


# =========================
# Bot起動
# =========================

def main():
    bot = UniversalBot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
