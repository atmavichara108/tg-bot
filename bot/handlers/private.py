import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart

logger = logging.getLogger(__name__)
router = Router(name="private")

@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start_private(message: types.Message, bot: types.Bot):
    """Приветствие в личных сообщениях."""
    # Получаем настройки из workflow_data через объект bot (или напрямую из dp, если доступно)
    # В aiogram 3.x доступ к workflow_data в хендлерах обычно осуществляется через передачу в middleware 
    # или через доступ к объекту бота, если он был настроен. 
    # Однако, согласно запросу, мы ожидаем settings в workflow_data.
    # В aiogram 3.x данные из workflow_data прокидываются в хендлеры автоматически.
    
    settings = message.bot.workflow_data.get("settings")
    contact = settings.contact_username if settings else "не указан"
    
    await message.answer(f"Привет! Если хочешь связаться — пиши @{contact}")

@router.message(F.chat.type == "private")
async def handle_all_private(message: types.Message):
    """Обработка всех остальных сообщений в личке."""
    settings = message.bot.workflow_data.get("settings")
    contact = settings.contact_username if settings else "не указан"
    
    await message.answer(f"Для связи пишите: @{contact}")
    
    logger.info(
        "Личное сообщение: user_id=%s, username=%s, text=%s",
        message.from_user.id,
        message.from_user.username,
        message.text
    )
