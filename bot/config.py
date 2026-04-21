# Модуль конфигурации

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    """Настройки бота, загружаемые из переменных окружения."""
    bot_token: str
    admin_id: int
    contact_username: str
    database_path: str = "bot.db"


def get_settings() -> Settings:
    """
    Загружает параметры из переменных окружения и возвращает объект Settings.
    
    Raises:
        ValueError: Если bot_token или admin_id не заданы в переменных окружения.
    """
    load_dotenv()
    
    bot_token = os.getenv("BOT_TOKEN")
    admin_id = os.getenv("ADMIN_ID")
    contact_username = os.getenv("CONTACT_USERNAME", "")
    database_path = os.getenv("DATABASE_PATH", "bot.db")
    
    if not bot_token:
        raise ValueError("Переменная окружения BOT_TOKEN не задана")
    
    if not admin_id:
        raise ValueError("Переменная окружения ADMIN_ID не задана")
    
    try:
        admin_id = int(admin_id)
    except ValueError:
        raise ValueError(f"Переменная ADMIN_ID должна быть числом, получено: {admin_id}")
    
    return Settings(
        bot_token=bot_token,
        admin_id=admin_id,
        contact_username=contact_username,
        database_path=database_path,
    )
