# Модуль конфигурации

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    admin_ids: list[int] = field(default_factory=list)
    contact_username: str = ""
    database_path: str = "bot.db"


def get_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN")
    admin_ids_raw = os.getenv("ADMIN_ID", "")
    contact_username = os.getenv("CONTACT_USERNAME", "")
    database_path = os.getenv("DATABASE_PATH", "bot.db")

    if not bot_token:
        raise ValueError("Переменная окружения BOT_TOKEN не задана")

    if not admin_ids_raw:
        raise ValueError("Переменная окружения ADMIN_ID не задана")

    try:
        admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]
    except ValueError:
        raise ValueError(f"ADMIN_ID должен содержать числа через запятую, получено: {admin_ids_raw}")

    if not admin_ids:
        raise ValueError("ADMIN_ID не содержит ни одного валидного ID")

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        contact_username=contact_username,
        database_path=database_path,
    )
