"""Отправка карточек лекций и массовые рассылки."""
from __future__ import annotations

import asyncio
import logging

import aiosqlite
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import texts

logger = logging.getLogger(__name__)

CAPTION_LIMIT = 1024


async def send_lecture_card(
    bot: Bot,
    chat_id: int,
    lecture: aiosqlite.Row | dict,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    for_admin: bool = False,
    prefix: str = "",
) -> Message:
    """Карточка лекции: с фото — фотосообщением, иначе текстом."""
    text = prefix + texts.lecture_card(lecture, for_admin=for_admin)
    photo = lecture["photo_file_id"]
    if photo and len(text) <= CAPTION_LIMIT:
        return await bot.send_photo(chat_id, photo, caption=text, reply_markup=reply_markup)
    if photo:
        await bot.send_photo(chat_id, photo)
    return await bot.send_message(chat_id, text, reply_markup=reply_markup)


async def edit_card(
    callback: CallbackQuery,
    lecture: aiosqlite.Row | dict,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    for_admin: bool = False,
) -> None:
    """Обновляет уже отправленную карточку (текстом или подписью к фото)."""
    text = texts.lecture_card(lecture, for_admin=for_admin)
    message = callback.message
    if message is None:
        return
    try:
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=reply_markup)
        else:
            await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            logger.warning("Не удалось обновить карточку: %s", error)


async def safe_delete(message: Message | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def broadcast(
    bot: Bot,
    user_ids: list[int],
    *,
    text: str,
    photo: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> tuple[int, int]:
    """Шлёт сообщение списку пользователей. Возвращает (доставлено, не доставлено)."""
    delivered = failed = 0
    for user_id in user_ids:
        try:
            if photo and len(text) <= CAPTION_LIMIT:
                await bot.send_photo(user_id, photo, caption=text, reply_markup=reply_markup)
            else:
                if photo:
                    await bot.send_photo(user_id, photo)
                await bot.send_message(user_id, text, reply_markup=reply_markup)
            delivered += 1
        except TelegramRetryAfter as error:
            await asyncio.sleep(error.retry_after)
            failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1  # бот заблокирован или чат недоступен
        except Exception:  # noqa: BLE001 — рассылка не должна падать целиком
            logger.exception("Ошибка рассылки пользователю %s", user_id)
            failed += 1
        await asyncio.sleep(0.05)  # ~20 сообщений в секунду, лимит Telegram
    return delivered, failed
