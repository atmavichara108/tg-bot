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


async def create_schedule(db: aiosqlite.Connection, message_id: int, group_id: int | None, cron_expr: str) -> int:
    cursor = await db.execute(
        "INSERT INTO schedules (message_id, group_id, cron_expr) VALUES (?, ?, ?)",
        (message_id, group_id, cron_expr),
    )
    await db.commit()
    return cursor.lastrowid


async def get_all_schedules(db: aiosqlite.Connection) -> list[dict]:
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """
        SELECT s.id, s.cron_expr, s.is_active, s.message_id, s.group_id,
               m.text as msg_text,
               g.title as group_title
        FROM schedules s
        LEFT JOIN messages m ON s.message_id = m.id
        LEFT JOIN groups g ON s.group_id = g.id
        ORDER BY s.id DESC
        """
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_schedule_by_id(db: aiosqlite.Connection, schedule_id: int) -> dict | None:
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """
        SELECT s.id, s.cron_expr, s.is_active, s.message_id, s.group_id,
               m.text as msg_text, m.photo_id as msg_photo_id,
               g.title as group_title
        FROM schedules s
        LEFT JOIN messages m ON s.message_id = m.id
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE s.id = ?
        """,
        (schedule_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return dict(row) if row else None


async def toggle_schedule(db: aiosqlite.Connection, schedule_id: int) -> bool:
    """Переключает is_active, возвращает новое значение."""
    async with db.execute("SELECT is_active FROM schedules WHERE id = ?", (schedule_id,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return False
    new_val = 0 if row[0] else 1
    await db.execute("UPDATE schedules SET is_active = ? WHERE id = ?", (new_val, schedule_id))
    await db.commit()
    return bool(new_val)


async def delete_schedule(db: aiosqlite.Connection, schedule_id: int) -> None:
    await db.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    await db.commit()


async def get_active_schedules(db: aiosqlite.Connection) -> list[dict]:
    """Все активные расписания — для scheduler'а."""
    db.row_factory = aiosqlite.Row
    async with db.execute(
        """
        SELECT s.id, s.cron_expr, s.message_id, s.group_id,
               m.text as msg_text, m.photo_id as msg_photo_id,
               g.chat_id as group_chat_id
        FROM schedules s
        JOIN messages m ON s.message_id = m.id
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE s.is_active = 1
        """
    ) as cursor:
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_all_active_group_chat_ids(db: aiosqlite.Connection) -> list[int]:
    """Возвращает список chat_id всех активных групп."""
    async with db.execute("SELECT chat_id FROM groups WHERE is_active = 1") as cursor:
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def increment_group_errors(db: aiosqlite.Connection, chat_id: int) -> int:
    """Увеличивает счётчик ошибок, возвращает новое значение."""
    await db.execute(
        """
        UPDATE groups
        SET settings = json_set(
            COALESCE(settings, '{}'),
            '$.error_count',
            COALESCE(json_extract(settings, '$.error_count'), 0) + 1
        )
        WHERE chat_id = ?
        """,
        (chat_id,),
    )
    await db.commit()
    async with db.execute(
        "SELECT json_extract(settings, '$.error_count') FROM groups WHERE chat_id = ?",
        (chat_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return row[0] if row and row[0] else 0


async def reset_group_errors(db: aiosqlite.Connection, chat_id: int) -> None:
    await db.execute(
        """
        UPDATE groups
        SET settings = json_set(COALESCE(settings, '{}'), '$.error_count', 0)
        WHERE chat_id = ?
        """,
        (chat_id,),
    )
    await db.commit()


async def set_group_flood_until(db: aiosqlite.Connection, chat_id: int, timestamp: float) -> None:
    """Запоминает до какого момента группа заблокирована FloodWait."""
    await db.execute(
        """
        UPDATE groups
        SET settings = json_set(COALESCE(settings, '{}'), '$.flood_until', ?)
        WHERE chat_id = ?
        """,
        (timestamp, chat_id),
    )
    await db.commit()


async def get_group_flood_until(db: aiosqlite.Connection, chat_id: int) -> float:
    async with db.execute(
        "SELECT json_extract(settings, '$.flood_until') FROM groups WHERE chat_id = ?",
        (chat_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return float(row[0]) if row and row[0] else 0.0
