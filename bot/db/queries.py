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

async def create_message(db: aiosqlite.Connection, text: str, photo_id: str = None) -> int:
    """Создаёт сообщение, возвращает его id."""
    cursor = await db.execute(
        "INSERT INTO messages (text, photo_id, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (text, photo_id),
    )
    await db.commit()
    return cursor.lastrowid


async def get_all_messages(db: aiosqlite.Connection) -> list[dict]:
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT id, text, photo_id, created_at FROM messages ORDER BY id DESC"
    ) as cursor:
        rows = await cursor.fetchall()
        return [{"id": r["id"], "text": r["text"], "photo_id": r["photo_id"], "created_at": r["created_at"]} for r in rows]


async def get_message_by_id(db: aiosqlite.Connection, msg_id: int) -> dict | None:
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT id, text, photo_id, created_at FROM messages WHERE id = ?", (msg_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        return {"id": row["id"], "text": row["text"], "photo_id": row["photo_id"], "created_at": row["created_at"]}


async def update_message_text(db: aiosqlite.Connection, msg_id: int, text: str) -> None:
    await db.execute(
        "UPDATE messages SET text = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (text, msg_id),
    )
    await db.commit()


async def update_message_photo(db: aiosqlite.Connection, msg_id: int, photo_id: str | None) -> None:
    await db.execute(
        "UPDATE messages SET photo_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (photo_id, msg_id),
    )
    await db.commit()


async def delete_message(db: aiosqlite.Connection, msg_id: int) -> None:
    await db.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
    await db.commit()

