
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from bot.db.queries import get_active_schedules
from bot.scheduler.broadcaster import send_scheduled

logger = logging.getLogger(__name__)


async def load_schedules(scheduler: AsyncIOScheduler, bot: Bot, db, admin_id: int):
    for job in scheduler.get_jobs():
        if job.id != "reload_schedules":
            job.remove()

    schedules = await get_active_schedules(db)

    for s in schedules:
        job_id = f"sched_{s['id']}"
        parts = s["cron_expr"].split()
        if len(parts) != 5:
            logger.warning(f"Sched #{s['id']}: невалидный cron '{s['cron_expr']}', пропускаю")
            continue

        try:
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
            scheduler.add_job(
                send_scheduled,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                kwargs={
                    "bot": bot,
                    "db": db,
                    "admin_id": admin_id,
                    "schedule_id": s["id"],
                    "message_id": s["message_id"],
                    "msg_text": s["msg_text"],
                    "msg_photo_id": s["msg_photo_id"],
                    "group_chat_id": s["group_chat_id"],
                },
            )
            logger.info(f"Sched #{s['id']}: загружено [{s['cron_expr']}]")
        except Exception as e:
            logger.error(f"Sched #{s['id']}: ошибка создания джобы: {e}")

    logger.info(f"Загружено расписаний: {len(scheduler.get_jobs())}")


def create_scheduler(bot: Bot, db, admin_id: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        load_schedules,
        "interval",
        seconds=60,
        id="reload_schedules",
        kwargs={"scheduler": scheduler, "bot": bot, "db": db, "admin_id": admin_id},
    )

    return scheduler
