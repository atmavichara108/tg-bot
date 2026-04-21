import logging
from aiogram import Router, types
from aiogram.filters import ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated

from bot.db.queries import add_group, deactivate_group

logger = logging.getLogger(__name__)

router = Router(name="group")

# Фильтры для переходов статуса бота
JOIN_FILTER = ChatMemberUpdatedFilter(
    member_status_changed=ChatMemberUpdatedFilter.IS_NOT_MEMBER
    >> ChatMemberUpdatedFilter.IS_MEMBER
)
LEAVE_FILTER = ChatMemberUpdatedFilter(
    member_status_changed=ChatMemberUpdatedFilter.IS_MEMBER
    >> ChatMemberUpdatedFilter.IS_NOT_MEMBER
)


@router.my_chat_member(JOIN_FILTER)
async def bot_added_to_group(
    event: ChatMemberUpdated, db: types.Connection  # db будет подставлен из dp["db"]
):
    """
    Обрабатывает событие добавления бота в чат (группу/супергруппу).
    """
    chat = event.chat
    title = chat.title or "без названия"
    await add_group(db, chat_id=chat.id, title=title)
    logger.info("Бот добавлен в группу: %s (%s)", title, chat.id)


@router.my_chat_member(LEAVE_FILTER)
async def bot_removed_from_group(
    event: ChatMemberUpdated, db: types.Connection
):
    """
    Обрабатывает событие удаления бота из чата.
    """
    chat = event.chat
    title = chat.title or "без названия"
    await deactivate_group(db, chat_id=chat.id)
    logger.info("Бот удалён из группы: %s (%s)", title, chat.id)
