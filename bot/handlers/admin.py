
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.db.queries import get_active_groups

logger = logging.getLogger(__name__)
router = Router(name="admin")


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Группы", callback_data="admin:groups")],
        [InlineKeyboardButton(text="Сообщения", callback_data="admin:messages")],
        [InlineKeyboardButton(text="Расписание", callback_data="admin:schedules")],
    ])


@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin(message: types.Message):
    await message.answer("Панель управления:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Панель управления:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:groups")
async def cb_groups_list(callback: CallbackQuery, db):
    groups = await get_active_groups(db)

    if not groups:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад", callback_data="admin:menu")]
        ])
        await callback.message.edit_text("Нет активных групп. Добавьте бота в группу.", reply_markup=kb)
        await callback.answer()
        return

    buttons = []
    for g in groups:
        buttons.append([
            InlineKeyboardButton(
                text=f"{g['title']} ({g['chat_id']})",
                callback_data=f"admin:group:{g['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="admin:menu")])

    await callback.message.edit_text("Активные группы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()
