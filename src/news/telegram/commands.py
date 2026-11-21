"""Личные сообщения боту: /start и /help — приветствие на русском и узбекском.

Других команд у бота нет: новости он берёт только из постов канала.
"""

import logging

from src.news.telegram.client import TelegramClient

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "🇺🇿 Yoshlar Fondi botiga xush kelibsiz!\n"
    "Bot Jamgʻarma kanalidagi yangiliklarni yoshlarfondi.uz saytida avtomatik eʼlon qiladi. "
    "Botdan foydalanish uchun uni Jamgʻarmaning yangiliklar kanaliga administrator "
    "sifatida qoʻshing.\n"
    "\n"
    "🇷🇺 Добро пожаловать в бот Yoshlar Fondi!\n"
    "Бот автоматически публикует новости из канала Фонда на сайте yoshlarfondi.uz. "
    "Чтобы воспользоваться ботом, добавьте его администратором в канал новостей Фонда."
)

COMMANDS = {"/start", "/help"}


def command_of(text: str) -> str | None:
    """`/start`, `/start@bot_name`, `/start payload` → `/start`."""
    if not text.startswith("/"):
        return None
    return text.split(maxsplit=1)[0].split("@", 1)[0].lower()


async def handle_message(client: TelegramClient, update: dict) -> bool:
    """Отвечает на /start и /help в личном чате. True — если ответ отправлен."""
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return False
    if command_of((message.get("text") or "").strip()) not in COMMANDS:
        return False
    await client.send_message(int(chat["id"]), WELCOME_TEXT)
    logger.info("Telegram bot: welcome sent to private chat %s", chat.get("id"))
    return True
