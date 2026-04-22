
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DAYS = [
    ("Пн", "1"), ("Вт", "2"), ("Ср", "3"), ("Чт", "4"),
    ("Пт", "5"), ("Сб", "6"), ("Вс", "0"),
]

HOURS = list(range(24))
MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]


def days_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Кнопки выбора дней недели. Выбранные помечены ✅."""
    buttons = []
    row = []
    for name, val in DAYS:
        mark = "✅ " if val in selected else ""
        row.append(InlineKeyboardButton(
            text=f"{mark}{name}",
            callback_data=f"sched_day:{val}",
        ))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="Каждый день", callback_data="sched_day:all")])
    buttons.append([InlineKeyboardButton(text="Будни (Пн-Пт)", callback_data="sched_day:weekdays")])

    if selected:
        buttons.append([InlineKeyboardButton(text="Дальше →", callback_data="sched_days_done")])
    buttons.append([InlineKeyboardButton(text="« Отмена", callback_data="admin:schedules")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def hours_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора часа — сетка 6×4."""
    buttons = []
    row = []
    for h in HOURS:
        row.append(InlineKeyboardButton(
            text=f"{h:02d}",
            callback_data=f"sched_hour:{h}",
        ))
        if len(row) == 6:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="sched_back_days")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def minutes_keyboard(hour: int) -> InlineKeyboardMarkup:
    """Кнопки выбора минут."""
    buttons = []
    row = []
    for m in MINUTES:
        row.append(InlineKeyboardButton(
            text=f"{hour:02d}:{m:02d}",
            callback_data=f"sched_min:{m}",
        ))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="sched_back_hours")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Создать", callback_data="sched_confirm")],
        [InlineKeyboardButton(text="« Отмена", callback_data="admin:schedules")],
    ])


def days_to_cron(selected: set[str]) -> str:
    """Конвертирует выбранные дни в cron day_of_week."""
    if len(selected) == 7:
        return "*"
    return ",".join(sorted(selected))


def days_display(selected: set[str]) -> str:
    """Человекочитаемое отображение дней."""
    if len(selected) == 7:
        return "Каждый день"
    names = dict(DAYS)
    reverse = {v: k for k, v in names.items()}
    # DAYS list has (name, val)
    name_map = {val: name for name, val in DAYS}
    return ", ".join(name_map[d] for d in sorted(selected) if d in name_map)
