
import logging
from aiogram import Bot
from bot.db.queries import get_active_schedules, get_all_active_group_chat_ids

logger = logging.getLogger(__name__)


async def send_scheduled(bot: Bot, db, schedule_id: int, message_id: int,
                         msg_text: str, msg_photo_id: str | None,
                         group_chat_id: int | None):
    """Отправляет одно запланированное сообщение."""
    if group_chat_id:
        chat_ids = [group_chat_id]
    else:
        chat_ids = await get_all_active_group_chat_ids(db)

    for chat_id in chat_ids:
        try:
            if msg_photo_id:
                await bot.send_photo(chat_id=chat_id, photo=msg_photo_id, caption=msg_text)
            else:
                await bot.send_message(chat_id=chat_id, text=msg_text)
            logger.info(f"Sched #{schedule_id}: отправлено в {chat_id}")
        except Exception as e:
            logger.error(f"Sched #{schedule_id}: ошибка отправки в {chat_id}: {e}")
