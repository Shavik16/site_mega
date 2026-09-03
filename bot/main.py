"""Точка входа: бот школьных лекций (aiogram 3, long polling)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import load_config
from db import Database
from handlers import build_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("lecture-bot")

COMMANDS = [
    BotCommand(command="start", description="Начало и регистрация"),
    BotCommand(command="lectures", description="Афиша лекций"),
    BotCommand(command="my", description="Мои записи"),
    BotCommand(command="profile", description="Мой профиль"),
    BotCommand(command="help", description="Помощь"),
    BotCommand(command="cancel", description="Отменить текущее действие"),
]


async def main() -> None:
    config = load_config()

    db = Database(config.db_path)
    await db.connect()
    logger.info("База готова: %s", config.db_path)

    bot = Bot(config.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["db"] = db
    dispatcher["admin_ids"] = set(config.admin_ids)
    dispatcher.include_router(build_router())

    await bot.set_my_commands(COMMANDS)
    me = await bot.get_me()
    logger.info("Запускаю @%s, преподавателей: %d", me.username, len(config.admin_ids))

    try:
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
