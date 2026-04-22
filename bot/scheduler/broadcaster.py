
import time
import logging
from aiogram import Bot
from aiogram.exceptions import (
    TelegramRetryAfter,
    TelegramForbiddenError,
    TelegramBadRequest,
)
from bot.db.queries import (
    get_all_active_group_chat_ids,
    deactivate_group,
    increment_group_errors,
    reset_group_errors,
    set_group_flood_until,
    get_group_flood_until,
)

logger = logging.getLogger(__name__)

MAX_ERRORS = 5


async def send_to_chat(bot: Bot, db, chat_id: int, text: str, photo_id: str | None) -> bool:
    """Отправляет сообщение в один чат. Возвращает True при успехе."""

    # Проверяем flood cooldown
    flood_until = await get_group_flood_until(db, chat_id)
    if flood_until > time.time():
        wait = int(flood_until - time.time())
        logger.info(f"Chat {chat_id}: flood cooldown, пропуск ({wait}с осталось)")
        return False

    try:
        if photo_id:
            await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=text)
        else:
            await bot.send_message(chat_id=chat_id, text=text)

        await reset_group_errors(db, chat_id)
        return True

    except TelegramRetryAfter as e:
        until = time.time() + e.retry_after
        await set_group_flood_until(db, chat_id, until)
        logger.warning(f"Chat {chat_id}: FloodWait {e.retry_after}с")
        return False

    except TelegramForbiddenError:
        await deactivate_group(db, chat_id)
        logger.warning(f"Chat {chat_id}: бот заблокирован/кикнут, группа деактивирована")
        return False

    except TelegramBadRequest as e:
        err_msg = str(e)
        if "CHAT_RESTRICTED" in err_msg or "not enough rights" in err_msg:
            logger.warning(f"Chat {chat_id}: нет прав на отправку: {err_msg}")
        else:
            logger.error(f"Chat {chat_id}: bad request: {err_msg}")

        errors = await increment_group_errors(db, chat_id)
        if errors >= MAX_ERRORS:
            await deactivate_group(db, chat_id)
            logger.warning(f"Chat {chat_id}: {errors} ошибок подряд, группа деактивирована")
        return False

    except Exception as e:
        logger.error(f"Chat {chat_id}: неизвестная ошибка: {e}")
        errors = await increment_group_errors(db, chat_id)
        if errors >= MAX_ERRORS:
            await deactivate_group(db, chat_id)
            logger.warning(f"Chat {chat_id}: {errors} ошибок подряд, группа деактивирована")
        return False


async def send_scheduled(bot: Bot, db, schedule_id: int, message_id: int,
                         msg_text: str, msg_photo_id: str | None,
                         group_chat_id: int | None):
    """Отправляет запланированное сообщение."""
    if group_chat_id:
        chat_ids = [group_chat_id]
    else:
        chat_ids = await get_all_active_group_chat_ids(db)

    sent = 0
    failed = 0
    for chat_id in chat_ids:
        success = await send_to_chat(bot, db, chat_id, msg_text, msg_photo_id)
        if success:
            sent += 1
        else:
            failed += 1

    logger.info(f"Sched #{schedule_id}: отправлено {sent}, ошибки {failed}")
    return sent, failed
