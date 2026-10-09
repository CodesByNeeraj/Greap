"""Telegram adapter: the real Greap customer channel."""

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from greap.config import loadSettings
from greap.constants import TELEGRAM_MESSAGE_LIMIT, TICK_SECONDS
from greap.greap_app import GreapApp


class TelegramNotifier:
    """Sends proactive messages; the bot is attached after construction."""

    def __init__(self, opsTelegramId: str) -> None:
        self.opsTelegramId = opsTelegramId
        self.application: Application | None = None

    async def sendUser(self, telegramId: str, text: str) -> None:
        """Message a user by Telegram id."""
        await self.application.bot.send_message(chat_id=telegramId, text=text)

    async def sendOps(self, text: str) -> None:
        """Operator links go to a configured chat, else to the console."""
        if self.opsTelegramId:
            await self.sendUser(self.opsTelegramId, text)
        else:
            print(f"[OPS] {text}")


def splitForTelegram(text: str) -> list[str]:
    """Telegram rejects messages over 4096 chars, so long lists go in pieces.

    Cutting on line breaks keeps each product line whole.
    """
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > TELEGRAM_MESSAGE_LIMIT:
            chunks.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    return chunks + [current]


def buildApplication() -> Application:
    """Create the Telegram app, wiring messages and the deadline timer."""
    settings = loadSettings()
    if not settings.telegramToken:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Get one from @BotFather.")
    notifier = TelegramNotifier(settings.opsTelegramId)
    greap = GreapApp(settings, notifier)
    application = Application.builder().token(settings.telegramToken).build()
    notifier.application = application

    async def onMessage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Every text, including /pay, goes through the same router."""
        telegramId = str(update.effective_user.id)
        for reply in await greap.handleMessage(telegramId, update.message.text):
            for chunk in splitForTelegram(reply):
                await update.message.reply_text(chunk)

    async def onTick(context: ContextTypes.DEFAULT_TYPE) -> None:
        """Periodic deadline checks."""
        await greap.tick()

    application.add_handler(MessageHandler(filters.TEXT, onMessage))
    application.job_queue.run_repeating(onTick, interval=TICK_SECONDS)
    return application


if __name__ == "__main__":
    buildApplication().run_polling()
