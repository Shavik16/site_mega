"""Ученик: афиша лекций, бронь места, мои записи."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import views
from db import Database
from keyboards import BTN_LECTURES, BTN_MY, LectureCB, lecture_card_kb, lectures_list, main_menu
from utils import esc, format_datetime, from_db

from .common import start_registration

router = Router(name="student")

BOOK_RESULT = {
    "ok": "✅ Место забронировано! Ждём тебя на лекции.",
    "already": "Ты уже записан(а) на эту лекцию 🙂",
    "full": "😔 Все места заняты. Загляни позже — вдруг кто-то отменит бронь.",
    "cancelled": "Эта лекция отменена.",
    "past": "Лекция уже прошла.",
    "missing": "Лекция не найдена — возможно, её удалили.",
}


async def _require_user(message: Message, state: FSMContext, db: Database):
    user = await db.get_user(message.from_user.id)
    if user is None:
        await start_registration(message, state, "Сначала короткая регистрация 👇")
    return user


async def _send_lectures_list(message: Message, db: Database, user_id: int) -> None:
    lectures = await db.list_lectures(only_upcoming=True)
    if not lectures:
        await message.answer("📭 Пока ни одной лекции не запланировано. Загляни позже!")
        return
    booked = {lecture["id"] for lecture in await db.user_bookings(user_id)}
    await message.answer(
        "📅 <b>Ближайшие лекции</b>\n\nВыбери лекцию, чтобы увидеть афишу и забронировать место.\n"
        "🟢 есть места · 🔴 мест нет · ✅ ты записан(а)",
        reply_markup=lectures_list(lectures, booked),
    )


@router.message(Command("lectures"))
@router.message(F.text == BTN_LECTURES)
async def cmd_lectures(message: Message, state: FSMContext, db: Database) -> None:
    if await _require_user(message, state, db) is None:
        return
    await _send_lectures_list(message, db, message.from_user.id)


@router.callback_query(LectureCB.filter(F.action == "list"))
async def back_to_list(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    await views.safe_delete(callback.message)
    await _send_lectures_list(callback.message, db, callback.from_user.id)


@router.callback_query(LectureCB.filter(F.action == "view"))
async def view_lecture(
    callback: CallbackQuery, callback_data: LectureCB, db: Database, bot: Bot, state: FSMContext
) -> None:
    await callback.answer()
    if await db.get_user(callback.from_user.id) is None:
        await start_registration(callback.message, state, "Сначала короткая регистрация 👇")
        return

    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        await callback.message.answer(BOOK_RESULT["missing"])
        return

    booked = await db.is_booked(lecture["id"], callback.from_user.id)
    can_book = not lecture["is_cancelled"] and lecture["booked"] < lecture["capacity"]
    await views.safe_delete(callback.message)
    await views.send_lecture_card(
        bot,
        callback.message.chat.id,
        lecture,
        lecture_card_kb(lecture["id"], booked=booked, can_book=can_book),
    )


@router.callback_query(LectureCB.filter(F.action == "book"))
async def book_lecture(callback: CallbackQuery, callback_data: LectureCB, db: Database, state: FSMContext) -> None:
    if await db.get_user(callback.from_user.id) is None:
        await callback.answer()
        await start_registration(callback.message, state, "Сначала короткая регистрация 👇")
        return

    result = await db.book(callback_data.lecture_id, callback.from_user.id)
    await callback.answer(BOOK_RESULT[result], show_alert=result != "ok")

    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        return
    booked = await db.is_booked(lecture["id"], callback.from_user.id)
    can_book = not lecture["is_cancelled"] and lecture["booked"] < lecture["capacity"]
    await views.edit_card(
        callback, lecture, lecture_card_kb(lecture["id"], booked=booked, can_book=can_book)
    )


@router.callback_query(LectureCB.filter(F.action == "unbook"))
async def unbook_lecture(callback: CallbackQuery, callback_data: LectureCB, db: Database) -> None:
    removed = await db.unbook(callback_data.lecture_id, callback.from_user.id)
    await callback.answer("Бронь отменена." if removed else "Ты и не был(а) записан(а).")

    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        return
    can_book = not lecture["is_cancelled"] and lecture["booked"] < lecture["capacity"]
    await views.edit_card(callback, lecture, lecture_card_kb(lecture["id"], booked=False, can_book=can_book))


@router.message(Command("my"))
@router.message(F.text == BTN_MY)
async def my_bookings(message: Message, state: FSMContext, db: Database) -> None:
    if await _require_user(message, state, db) is None:
        return

    rows = await db.user_bookings(message.from_user.id)
    if not rows:
        await message.answer("🎟 Ты пока никуда не записан(а). Загляни в «📅 Лекции».")
        return

    lines = ["🎟 <b>Твои записи</b>", ""]
    for lecture in rows:
        mark = "❌ ОТМЕНЕНА — " if lecture["is_cancelled"] else ""
        place = f", {esc(lecture['place'])}" if lecture["place"] else ""
        lines.append(
            f"• {mark}<b>{esc(lecture['title'])}</b>\n"
            f"  {format_datetime(from_db(lecture['starts_at']))}{place}"
        )
    await message.answer(
        "\n".join(lines),
        reply_markup=lectures_list(rows, {lecture["id"] for lecture in rows}),
    )


@router.message(F.text)
async def fallback(message: Message, state: FSMContext, db: Database, admin_ids: set[int]) -> None:
    """Любой непонятный текст — подсказка с меню."""
    if await db.get_user(message.from_user.id) is None:
        await start_registration(message, state, "Сначала короткая регистрация 👇")
        return
    await message.answer(
        "Не понял 🤔 Пользуйся кнопками меню или командой /help.",
        reply_markup=main_menu(message.from_user.id in admin_ids),
    )
