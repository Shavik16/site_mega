"""Клавиатуры и callback-data."""
from __future__ import annotations

import aiosqlite
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from texts import lecture_button_label

BTN_LECTURES = "📅 Лекции"
BTN_MY = "🎟 Мои записи"
BTN_PROFILE = "👤 Профиль"
BTN_ADMIN = "⚙️ Админка"

BTN_NEW_LECTURE = "➕ Новая лекция"
BTN_MANAGE = "🗂 Все лекции"
BTN_BROADCAST = "📢 Рассылка"
BTN_BACK = "⬅️ Назад"


class LectureCB(CallbackData, prefix="lec"):
    action: str  # view | book | unbook | list
    lecture_id: int = 0


class AdminCB(CallbackData, prefix="adm"):
    action: str  # view | edit | field | cancel | restore | delete | delete_yes | who | list | publish
    lecture_id: int = 0
    field: str = ""


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_LECTURES), KeyboardButton(text=BTN_MY)],
        [KeyboardButton(text=BTN_PROFILE)],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_LECTURE), KeyboardButton(text=BTN_MANAGE)],
            [KeyboardButton(text=BTN_BROADCAST)],
            [KeyboardButton(text=BTN_BACK)],
        ],
        resize_keyboard=True,
    )


def lectures_list(lectures: list[aiosqlite.Row], booked_ids: set[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for lecture in lectures:
        kb.button(
            text=lecture_button_label(lecture, booked_by_me=lecture["id"] in booked_ids),
            callback_data=LectureCB(action="view", lecture_id=lecture["id"]),
        )
    kb.adjust(1)
    return kb.as_markup()


def lecture_card_kb(lecture_id: int, *, booked: bool, can_book: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if booked:
        kb.button(
            text="❌ Отменить бронь",
            callback_data=LectureCB(action="unbook", lecture_id=lecture_id),
        )
    elif can_book:
        kb.button(
            text="✅ Забронировать место",
            callback_data=LectureCB(action="book", lecture_id=lecture_id),
        )
    kb.button(text="⬅️ К списку", callback_data=LectureCB(action="list"))
    kb.adjust(1)
    return kb.as_markup()


def announce_kb(lecture_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Забронировать место",
        callback_data=LectureCB(action="view", lecture_id=lecture_id),
    )
    return kb.as_markup()


def admin_lectures_list(lectures: list[aiosqlite.Row]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for lecture in lectures:
        kb.button(
            text=lecture_button_label(lecture),
            callback_data=AdminCB(action="view", lecture_id=lecture["id"]),
        )
    kb.adjust(1)
    return kb.as_markup()


def admin_card_kb(lecture: aiosqlite.Row) -> InlineKeyboardMarkup:
    lecture_id = lecture["id"]
    kb = InlineKeyboardBuilder()
    kb.button(text="🎟 Кто записался", callback_data=AdminCB(action="who", lecture_id=lecture_id))
    kb.button(text="✏️ Редактировать", callback_data=AdminCB(action="edit", lecture_id=lecture_id))
    kb.button(text="📢 Разослать афишу", callback_data=AdminCB(action="publish", lecture_id=lecture_id))
    if lecture["is_cancelled"]:
        kb.button(text="♻️ Вернуть лекцию", callback_data=AdminCB(action="restore", lecture_id=lecture_id))
    else:
        kb.button(text="🚫 Отменить лекцию", callback_data=AdminCB(action="cancel", lecture_id=lecture_id))
    kb.button(text="🗑 Удалить", callback_data=AdminCB(action="delete", lecture_id=lecture_id))
    kb.button(text="⬅️ К списку", callback_data=AdminCB(action="list"))
    kb.adjust(1)
    return kb.as_markup()


EDIT_FIELDS = (
    ("title", "Название"),
    ("description", "Описание"),
    ("speaker", "Лектор"),
    ("place", "Место"),
    ("starts_at", "Дата и время"),
    ("capacity", "Количество мест"),
    ("photo_file_id", "Фото"),
)


def edit_fields_kb(lecture_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for field, label in EDIT_FIELDS:
        kb.button(
            text=label,
            callback_data=AdminCB(action="field", lecture_id=lecture_id, field=field),
        )
    kb.button(text="⬅️ Назад", callback_data=AdminCB(action="view", lecture_id=lecture_id))
    kb.adjust(2)
    return kb.as_markup()


def confirm_delete_kb(lecture_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Да, удалить", callback_data=AdminCB(action="delete_yes", lecture_id=lecture_id))
    kb.button(text="⬅️ Отмена", callback_data=AdminCB(action="view", lecture_id=lecture_id))
    kb.adjust(1)
    return kb.as_markup()


def new_lecture_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Опубликовать и разослать", callback_data="new:publish")
    kb.button(text="💾 Сохранить без рассылки", callback_data="new:save")
    kb.button(text="❌ Отменить", callback_data="new:abort")
    kb.adjust(1)
    return kb.as_markup()
