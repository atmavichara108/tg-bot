# Модуль конфигурации

import os
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Settings:
    bot_token: str
    admin_id: int
    contact_username: str
    database_path: str = "bot.db"

def get_settings():
    """
    Загружает параметры из окружения и возвращает объект Settings.
    Если bot_token или admin_id не заданы — выбрасывает ValueError.
    """
    load_dotenv()
    if not os.path.exists(os.getenv("ENV_FILE")):
        raise ValueError("Путь к файлу .env не найден.")
    return Settings(
        bot_token=os.getenv("BOT_TOKEN"),
        admin_id=int(os.getenv("ADMIN_ID")),
        contact_username=os.getenv("CONTACT_USERNAME"),
        database_path=os.getenv("DATABASE_PATH")
    )
