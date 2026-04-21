import aiosqlite
from typing import List, Optional, Dict

# Helper to convert rows to dicts
def _row_to_dict(row: aiosqlite.Row) -> Dict:
    return {
        "id": row["id"],
        "chat_id": row["chat_id"],
        "title": row["title"],
        "added_at": row["added_at"],
    }


async def add_group(db: aiosqlite.Connection, chat_id: int, title: str) -> None:
    """
    Добавляет группу в таблицу ``groups``.
    Если запись уже существует (по chat_id), обновляет title и ставит is_active=1.
    """
    await db.execute(
        """
        INSERT OR IGNORE INTO groups (chat_id, title, is_active)
        VALUES (?, ?, 1)
        """,
        (chat_id, title),
    )
    # Если запись уже была, обновим её
    await db.execute(
        """
        UPDATE groups
        SET title = ?, is_active = 1
        WHERE chat_id = ?
        """,
        (title, chat_id),
    )
    await db.commit()


async def deactivate_group(db: aiosqlite.Connection, chat_id: int) -> None:
    """
    Деактивирует группу (is_active = 0) по её chat_id.
    """
    await db.execute(
        """
        UPDATE groups
        SET is_active = 0
        WHERE chat_id = ?
        """,
        (chat_id,),
    )
    await db.commit()


async def get_active_groups(db: aiosqlite.Connection) -> List[Dict]:
    """
    Возвращает список всех активных групп.
    Каждый элемент – словарь с полями: id, chat_id, title, added_at.
    """
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """
        SELECT id, chat_id, title, added_at
        FROM groups
        WHERE is_active = 1
        """
    ) as cursor:
        rows = await cursor.fetchall()
        return [_row_to_dict(row) for row in rows]


async def get_group_by_chat_id(
    db: aiosqlite.Connection, chat_id: int
) -> Optional[Dict]:
    """
    Возвращает одну группу по chat_id или None, если её нет.
    """
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """
        SELECT id, chat_id, title, added_at, is_active
        FROM groups
        WHERE chat_id = ?
        """,
        (chat_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return _row_to_dict(row) if row else None
