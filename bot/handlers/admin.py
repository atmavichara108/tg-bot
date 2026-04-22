
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.db.queries import (
    get_active_groups,
    get_all_messages,
    get_message_by_id,
    create_message,
    update_message_text,
    update_message_photo,
    delete_message,
)

logger = logging.getLogger(__name__)
router = Router(name="admin")


# ── FSM states ──────────────────────────────────────────────
class CreateMsg(StatesGroup):
    waiting_text = State()
    waiting_photo = State()


class EditMsg(StatesGroup):
    waiting_text = State()
    waiting_photo = State()


# ── Keyboards ───────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Группы", callback_data="admin:groups")],
        [InlineKeyboardButton(text="Сообщения", callback_data="admin:messages")],
        [InlineKeyboardButton(text="Расписание", callback_data="admin:schedules")],
    ])


def back_btn(cb: str = "admin:menu") -> list:
    return [InlineKeyboardButton(text="« Назад", callback_data=cb)]


# ── Main menu ───────────────────────────────────────────────
@router.message(Command("admin"), F.chat.type == "private")
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Панель управления:", reply_markup=main_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Панель управления:", reply_markup=main_menu_kb())
    await callback.answer()


# ── Groups ──────────────────────────────────────────────────
@router.callback_query(F.data == "admin:groups")
async def cb_groups_list(callback: CallbackQuery, db):
    groups = await get_active_groups(db)
    if not groups:
        kb = InlineKeyboardMarkup(inline_keyboard=[back_btn()])
        await callback.message.edit_text("Нет активных групп.", reply_markup=kb)
        await callback.answer()
        return

    buttons = []
    for g in groups:
        buttons.append([InlineKeyboardButton(
            text=f"{g['title']}",
            callback_data=f"admin:group:{g['id']}"
        )])
    buttons.append(back_btn())
    await callback.message.edit_text("Активные группы:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# ── Messages list ───────────────────────────────────────────
@router.callback_query(F.data == "admin:messages")
async def cb_messages_list(callback: CallbackQuery, db):
    msgs = await get_all_messages(db)
    buttons = []
    for m in msgs:
        preview = (m["text"] or "")[:30] + ("..." if m["text"] and len(m["text"]) > 30 else "")
        photo_mark = " 🖼" if m["photo_id"] else ""
        buttons.append([InlineKeyboardButton(
            text=f"#{m['id']} {preview}{photo_mark}",
            callback_data=f"admin:msg:{m['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Создать", callback_data="admin:msg:new")])
    buttons.append(back_btn())
    await callback.message.edit_text(
        "Сообщения для рассылки:" if msgs else "Нет сообщений.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


# ── View single message ─────────────────────────────────────
@router.callback_query(F.data.startswith("admin:msg:") & ~F.data.in_({"admin:msg:new"}))
async def cb_msg_view(callback: CallbackQuery, db):
    msg_id = int(callback.data.split(":")[2])
    msg = await get_message_by_id(db, msg_id)
    if not msg:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"admin:msg_edit_text:{msg_id}")],
        [InlineKeyboardButton(text="🖼 Изменить фото", callback_data=f"admin:msg_edit_photo:{msg_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:msg_del:{msg_id}")],
        back_btn("admin:messages"),
    ])

    text = f"<b>Сообщение #{msg['id']}</b>\n\n{msg['text'] or '(без текста)'}"
    if msg["photo_id"]:
        text += "\n\n🖼 Фото прикреплено"

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Create message ──────────────────────────────────────────
@router.callback_query(F.data == "admin:msg:new")
async def cb_msg_new(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateMsg.waiting_text)
    await callback.message.edit_text("Отправь текст нового сообщения.\n\nИли /cancel для отмены.")
    await callback.answer()


@router.message(CreateMsg.waiting_text, F.text)
async def on_create_text(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb())
        return

    await state.update_data(text=message.text)
    await state.set_state(CreateMsg.waiting_photo)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить фото", callback_data="admin:msg_skip_photo")]
    ])
    await message.answer("Теперь отправь фото, или нажми «Пропустить».", reply_markup=kb)


@router.callback_query(CreateMsg.waiting_photo, F.data == "admin:msg_skip_photo")
async def on_create_skip_photo(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    msg_id = await create_message(db, data["text"], None)
    await state.clear()
    await callback.message.edit_text(f"Сообщение #{msg_id} создано.", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(CreateMsg.waiting_photo, F.photo)
async def on_create_photo(message: types.Message, state: FSMContext, db):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    msg_id = await create_message(db, data["text"], photo_id)
    await state.clear()
    await message.answer(f"Сообщение #{msg_id} создано (с фото).", reply_markup=main_menu_kb())


# ── Edit text ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin:msg_edit_text:"))
async def cb_msg_edit_text(callback: CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.split(":")[2])
    await state.set_state(EditMsg.waiting_text)
    await state.update_data(edit_id=msg_id)
    await callback.message.edit_text("Отправь новый текст.\n\nИли /cancel для отмены.")
    await callback.answer()


@router.message(EditMsg.waiting_text, F.text)
async def on_edit_text(message: types.Message, state: FSMContext, db):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_menu_kb())
        return

    data = await state.get_data()
    await update_message_text(db, data["edit_id"], message.text)
    await state.clear()
    await message.answer(f"Текст сообщения #{data['edit_id']} обновлён.", reply_markup=main_menu_kb())


# ── Edit photo ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin:msg_edit_photo:"))
async def cb_msg_edit_photo(callback: CallbackQuery, state: FSMContext):
    msg_id = int(callback.data.split(":")[2])
    await state.set_state(EditMsg.waiting_photo)
    await state.update_data(edit_id=msg_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить фото", callback_data="admin:msg_remove_photo")]
    ])
    await callback.message.edit_text("Отправь новое фото, или удали текущее.", reply_markup=kb)
    await callback.answer()


@router.message(EditMsg.waiting_photo, F.photo)
async def on_edit_photo(message: types.Message, state: FSMContext, db):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    await update_message_photo(db, data["edit_id"], photo_id)
    await state.clear()
    await message.answer(f"Фото сообщения #{data['edit_id']} обновлено.", reply_markup=main_menu_kb())


@router.callback_query(EditMsg.waiting_photo, F.data == "admin:msg_remove_photo")
async def on_remove_photo(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    await update_message_photo(db, data["edit_id"], None)
    await state.clear()
    await callback.message.edit_text(f"Фото сообщения #{data['edit_id']} удалено.", reply_markup=main_menu_kb())
    await callback.answer()


# ── Delete message ──────────────────────────────────────────
@router.callback_query(F.data.startswith("admin:msg_del:"))
async def cb_msg_delete(callback: CallbackQuery, db):
    msg_id = int(callback.data.split(":")[2])
    await delete_message(db, msg_id)
    await callback.message.edit_text(f"Сообщение #{msg_id} удалено.", reply_markup=main_menu_kb())
    await callback.answer()
