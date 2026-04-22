import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from bot.config import Settings

logger = logging.getLogger(__name__)
router = Router(name="private")


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: types.Message, settings: Settings):
    """Приветствие в личных сообщениях."""
    contact = settings.contact_username or "не указан"
    await message.answer(f"Привет! Если хочешь связаться — пиши {contact}")


@router.message(F.chat.type == "private")
async def handle_all_private(message: types.Message, settings: Settings):
    """Обработка всех остальных сообщений в личке."""
    contact = settings.contact_username or "не указан"
    await message.answer(f"Для связи пишите: {contact}")

    logger.info(
        "Личное сообщение: user_id=%s, username=%s, text=%s",
        message.from_user.id,
        message.from_user.username,
        message.text,
    )
