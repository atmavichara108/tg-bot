import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

from bot.config import get_settings
from bot.db.models import init_db, get_db
from bot.handlers import private, group

# ------------------------------------------------------------
# Настройка логирования
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Точка входа
# ------------------------------------------------------------
async def main() -> None:
    # 1. Загрузка конфигурации
    settings = get_settings()
    # Логируем только нужные поля, маскируя токен
    masked_token = f"{settings.bot_token[:4]}...{settings.bot_token[-4:]}"
    logger.info(
        "Конфигурация загружена: admin_id=%s, contact_username=%s, database_path=%s, bot_token=%s",
        settings.admin_id,
        settings.contact_username,
        settings.database_path,
        masked_token,
    )

    # 2. Инициализация БД
    db_conn = await init_db(settings.database_path)
    logger.info("База данных инициализирована: %s", settings.database_path)

    # 3. Создание Bot и Dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    
    # Подключаем роутеры
    dp.include_router(private.router)
    dp.include_router(group.router)

    # 4. Сохранение объектов в workflow_data для доступа из хендлеров
    dp.workflow_data["bot"] = bot
    dp.workflow_data["db"] = db_conn
    dp.workflow_data["settings"] = settings
    dp["settings"] = settings
    dp["db"] = db_conn  # гарантируем доступ через dp["db"]

    # 5. Запуск polling
    try:
        logger.info("Запуск polling...")
        await dp.start_polling(bot)
    finally:
        # Корректное закрытие соединения с БД при завершении
        await db_conn.close()
        await bot.session.close()
        logger.info("Остановлен polling, соединения закрыты.")


if __name__ == "__main__":
    asyncio.run(main())
