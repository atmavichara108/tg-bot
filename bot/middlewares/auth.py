
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class AdminMiddleware(BaseMiddleware):
    """Пропускает только сообщения/колбэки от админа в хендлеры админ-роутера."""

    def __init__(self, admin_id: int):
        self.admin_id = admin_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user and user.id == self.admin_id:
            return await handler(event, data)
        # Не админ — молча игнорируем
