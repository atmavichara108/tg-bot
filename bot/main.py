import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

from bot.config import get_settings
from bot.db.models import init_db, get_db

# ------------------------------------------------------------
# Настройка логирования
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Хендлеры
# ------------------------------------------------------------
router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Базовый хендлер на /start."""
    await message.answer("Бот запущен")
    logger.info("Отправлен ответ на /start пользователю %s", message.from_user.id)


# ------------------------------------------------------------
# Точка входа
# ------------------------------------------------------------
async def main() -> None:
    # 1. Загрузка конфигурации
    settings = get_settings()
    logger.info("Конфигурация загружена: %s", settings)

    # 2. Инициализация БД
    # init_db возвращает соединение, которое будем хранить в workflow_data
    db_conn = await init_db(settings.database_path)
    logger.info("База данных инициализирована: %s", settings.database_path)

    # 3. Создание Bot и Dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    dp.include_router(router)

    # 4. Сохранение объектов в workflow_data для доступа из хендлеров
    dp.workflow_data["bot"] = bot
    dp.workflow_data["db"] = db_conn

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
