
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
    get_all_schedules,
    get_schedule_by_id,
    create_schedule,
    toggle_schedule,
    delete_schedule,
    get_all_active_group_chat_ids,
)
    from bot.handlers.schedule_ui import (
    days_keyboard, hours_keyboard, minutes_keyboard, confirm_keyboard,
    days_to_cron, days_display,
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


class CreateSchedule(StatesGroup):
    choosing_message = State()
    choosing_group = State()
    choosing_days = State()
    choosing_hour = State()
    choosing_minute = State()
    confirming = State()


class PostNow(StatesGroup):
    choosing_message = State()
    choosing_groups = State()


# ── Keyboards ───────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Группы", callback_data="admin:groups")],
        [InlineKeyboardButton(text="Сообщения", callback_data="admin:messages")],
        [InlineKeyboardButton(text="Расписание", callback_data="admin:schedules")],
        [InlineKeyboardButton(text="📨 Запостить", callback_data="admin:post")],
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


# ── Schedules list ──────────────────────────────────────────
@router.callback_query(F.data == "admin:schedules")
async def cb_schedules_list(callback: CallbackQuery, db):
    scheds = await get_all_schedules(db)
    buttons = []
    for s in scheds:
        preview = (s["msg_text"] or "")[:20]
        group_name = s["group_title"] or "Все группы"
        status = "✅" if s["is_active"] else "⏸"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {preview} → {group_name} [{s['cron_expr']}]",
            callback_data=f"admin:sched:{s['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Создать", callback_data="admin:sched:new")])
    buttons.append(back_btn())
    await callback.message.edit_text(
        "Расписания:" if scheds else "Нет расписаний.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


# ── View schedule ───────────────────────────────────────────
@router.callback_query(F.data.regexp(r"^admin:sched:\d+$"))
async def cb_sched_view(callback: CallbackQuery, db):
    sched_id = int(callback.data.split(":")[2])
    s = await get_schedule_by_id(db, sched_id)
    if not s:
        await callback.answer("Не найдено", show_alert=True)
        return

    status = "✅ Активно" if s["is_active"] else "⏸ На паузе"
    group_name = s["group_title"] or "Все группы"
    text = (
        f"<b>Расписание #{s['id']}</b>\n\n"
        f"Сообщение: #{s['message_id']} — {(s['msg_text'] or '')[:40]}\n"
        f"Группа: {group_name}\n"
        f"Cron: <code>{s['cron_expr']}</code>\n"
        f"Статус: {status}"
    )

    toggle_text = "⏸ Пауза" if s["is_active"] else "▶️ Включить"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:sched_toggle:{sched_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:sched_del:{sched_id}")],
        back_btn("admin:schedules"),
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Toggle schedule ─────────────────────────────────────────
@router.callback_query(F.data.startswith("admin:sched_toggle:"))
async def cb_sched_toggle(callback: CallbackQuery, db):
    sched_id = int(callback.data.split(":")[2])
    new_state = await toggle_schedule(db, sched_id)
    status = "включено" if new_state else "на паузе"
    await callback.answer(f"Расписание #{sched_id} — {status}")
    # Перерисовать карточку
    await cb_sched_view(callback, db)


# ── Delete schedule ─────────────────────────────────────────
@router.callback_query(F.data.startswith("admin:sched_del:"))
async def cb_sched_delete(callback: CallbackQuery, db):
    sched_id = int(callback.data.split(":")[2])
    await delete_schedule(db, sched_id)
    await callback.message.edit_text(f"Расписание #{sched_id} удалено.", reply_markup=main_menu_kb())
    await callback.answer()


# ── Create schedule: step 1 — choose message ───────────────
@router.callback_query(F.data == "admin:sched:new")
async def cb_sched_new(callback: CallbackQuery, state: FSMContext, db):
    msgs = await get_all_messages(db)
    if not msgs:
        await callback.answer("Сначала создайте хотя бы одно сообщение.", show_alert=True)
        return

    buttons = []
    for m in msgs:
        preview = (m["text"] or "")[:30]
        buttons.append([InlineKeyboardButton(
            text=f"#{m['id']} {preview}",
            callback_data=f"admin:sched_pick_msg:{m['id']}"
        )])
    buttons.append(back_btn("admin:schedules"))

    await state.set_state(CreateSchedule.choosing_message)
    await callback.message.edit_text("Выберите сообщение:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# ── Create schedule: step 2 — choose group ─────────────────
@router.callback_query(CreateSchedule.choosing_message, F.data.startswith("admin:sched_pick_msg:"))
async def cb_sched_pick_msg(callback: CallbackQuery, state: FSMContext, db):
    msg_id = int(callback.data.split(":")[2])
    await state.update_data(message_id=msg_id)

    groups = await get_active_groups(db)
    buttons = [[InlineKeyboardButton(text="📢 Все группы", callback_data="admin:sched_pick_grp:all")]]
    for g in groups:
        buttons.append([InlineKeyboardButton(
            text=g["title"],
            callback_data=f"admin:sched_pick_grp:{g['id']}"
        )])
    buttons.append(back_btn("admin:schedules"))

    await state.set_state(CreateSchedule.choosing_group)
    await callback.message.edit_text("Куда отправлять:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


# ── Create schedule: step 3 — choose days ──────────────────
@router.callback_query(CreateSchedule.choosing_group, F.data.startswith("admin:sched_pick_grp:"))
async def cb_sched_pick_grp(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[2]
    group_id = None if val == "all" else int(val)
    await state.update_data(group_id=group_id, selected_days=set())
    await state.set_state(CreateSchedule.choosing_days)
    await callback.message.edit_text("Выберите дни недели:", reply_markup=days_keyboard(set()))
    await callback.answer()


@router.callback_query(CreateSchedule.choosing_days, F.data.startswith("sched_day:"))
async def cb_sched_toggle_day(callback: CallbackQuery, state: FSMContext):
    val = callback.data.split(":")[1]
    data = await state.get_data()
    selected = set(data.get("selected_days", []))

    if val == "all":
        selected = {"0", "1", "2", "3", "4", "5", "6"}
    elif val == "weekdays":
        selected = {"1", "2", "3", "4", "5"}
    elif val in selected:
        selected.discard(val)
    else:
        selected.add(val)

    await state.update_data(selected_days=selected)
    await callback.message.edit_reply_markup(reply_markup=days_keyboard(selected))
    await callback.answer()


@router.callback_query(CreateSchedule.choosing_days, F.data == "sched_days_done")
async def cb_sched_days_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateSchedule.choosing_hour)
    await callback.message.edit_text("Выберите час:", reply_markup=hours_keyboard())
    await callback.answer()


@router.callback_query(CreateSchedule.choosing_days, F.data == "sched_back_days")
async def cb_sched_back_to_days_from_days(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = set(data.get("selected_days", []))
    await callback.message.edit_text("Выберите дни недели:", reply_markup=days_keyboard(selected))
    await callback.answer()


# ── Create schedule: step 4 — choose hour ──────────────────
@router.callback_query(CreateSchedule.choosing_hour, F.data.startswith("sched_hour:"))
async def cb_sched_pick_hour(callback: CallbackQuery, state: FSMContext):
    hour = int(callback.data.split(":")[1])
    await state.update_data(hour=hour)
    await state.set_state(CreateSchedule.choosing_minute)
    await callback.message.edit_text(f"Час: {hour:02d}\nВыберите минуты:", reply_markup=minutes_keyboard(hour))
    await callback.answer()


@router.callback_query(CreateSchedule.choosing_hour, F.data == "sched_back_days")
async def cb_sched_back_to_days(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = set(data.get("selected_days", []))
    await state.set_state(CreateSchedule.choosing_days)
    await callback.message.edit_text("Выберите дни недели:", reply_markup=days_keyboard(selected))
    await callback.answer()


# ── Create schedule: step 5 — choose minute ────────────────
@router.callback_query(CreateSchedule.choosing_minute, F.data.startswith("sched_min:"))
async def cb_sched_pick_min(callback: CallbackQuery, state: FSMContext):
    minute = int(callback.data.split(":")[1])
    data = await state.get_data()
    hour = data["hour"]
    selected_days = set(data.get("selected_days", []))

    days_text = days_display(selected_days)
    cron = f"{minute} {hour} * * {days_to_cron(selected_days)}"

    await state.update_data(minute=minute, cron_expr=cron)
    await state.set_state(CreateSchedule.confirming)

    await callback.message.edit_text(
        f"<b>Подтвердите расписание:</b>\n\n"
        f"Дни: {days_text}\n"
        f"Время: {hour:02d}:{minute:02d}\n\n"
        f"<code>{cron}</code>",
        reply_markup=confirm_keyboard(),
    )
    await callback.answer()


@router.callback_query(CreateSchedule.choosing_minute, F.data == "sched_back_hours")
async def cb_sched_back_to_hours(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CreateSchedule.choosing_hour)
    await callback.message.edit_text("Выберите час:", reply_markup=hours_keyboard())
    await callback.answer()


# ── Create schedule: confirm ────────────────────────────────
@router.callback_query(CreateSchedule.confirming, F.data == "sched_confirm")
async def cb_sched_confirm(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    sched_id = await create_schedule(db, data["message_id"], data["group_id"], data["cron_expr"])
    await state.clear()
    await callback.message.edit_text(f"Расписание #{sched_id} создано.", reply_markup=main_menu_kb())
    await callback.answer()
