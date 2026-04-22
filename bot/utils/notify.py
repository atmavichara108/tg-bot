
import logging
from aiogram import Bot

logger = logging.getLogger(__name__)


async def notify_admin(bot: Bot, admin_id: int, text: str):
    """Отправляет уведомление админу в личку."""
    try:
        await bot.send_message(chat_id=admin_id, text=text)
    except Exception as e:
        logger.error(f"Не удалось уведомить админа: {e}")
