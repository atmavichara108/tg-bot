import logging
from aiogram import Router, types
from aiogram.types import ChatMemberUpdated
from bot.db.queries import add_group, deactivate_group

logger = logging.getLogger(__name__)
router = Router(name="group")


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, db: types.Connection):
    old = event.old_chat_member.status
    new = event.new_chat_member.status
    chat = event.chat

    # Бот добавлен в группу
    if old in ("left", "kicked") and new in ("member", "administrator"):
        await add_group(db, chat.id, chat.title or "")
        logger.info(f"Бот добавлен в группу: {chat.title} ({chat.id})")

    # Бот удалён из группы
    elif old in ("member", "administrator") and new in ("left", "kicked"):
        await deactivate_group(db, chat.id)
        logger.info(f"Бот удалён из группы: {chat.title} ({chat.id})")
