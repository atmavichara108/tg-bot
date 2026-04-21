import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

# Путь к файлу SQLite по умолчанию
DEFAULT_DB_PATH = "bot.db"


async def init_db(db_path: str = DEFAULT_DB_PATH) -> aiosqlite.Connection:
    """
    Инициализирует базу данных SQLite.

    1. Подключается к SQLite через aiosqlite.
    2. Включает режим WAL и foreign_keys.
    3. Создаёт таблицы groups, messages и schedules (если их нет).
    4. Возвращает объект aiosqlite.Connection.
    """
    # Создаём директорию, если её нет
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL;")
    await conn.execute("PRAGMA foreign_keys=ON;")

    # Создаём таблицы
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER UNIQUE NOT NULL,
            title TEXT,
            is_active BOOLEAN DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            settings TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            photo_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
            cron_expr TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            next_run TIMESTAMP
        );
        """
    )
    await conn.commit()
    return conn


@asynccontextmanager
async def get_db(db_path: str = DEFAULT_DB_PATH):
    """
    Контекстный менеджер для получения соединения с базой данных.
    Используется в виде:
        async with get_db() as conn:
            ...
    """
    conn = await init_db(db_path)
    try:
        yield conn
    finally:
        await conn.close()
