"""Преподаватель: мастер создания лекции, правка расписания, списки записавшихся."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import texts
import views
from db import Database
from keyboards import (
    BTN_ADMIN,
    BTN_BACK,
    BTN_BROADCAST,
    BTN_MANAGE,
    BTN_NEW_LECTURE,
    EDIT_FIELDS,
    AdminCB,
    admin_card_kb,
    admin_lectures_list,
    admin_menu,
    announce_kb,
    confirm_delete_kb,
    edit_fields_kb,
    main_menu,
    new_lecture_confirm_kb,
)
from states import Broadcast, EditLecture, NewLecture
from texts import SKIP
from utils import DATE_INPUT_HINT, esc, format_datetime, from_db, parse_datetime, to_db

MAX_TITLE = 100
MAX_DESCRIPTION = 700
MAX_SHORT = 80
MAX_CAPACITY = 1000

FIELD_LABELS = dict(EDIT_FIELDS)


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, admin_ids: set[int]) -> bool:
        return event.from_user is not None and event.from_user.id in admin_ids


router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ---------------------------------------------------------------- меню админа

@router.message(F.text == BTN_ADMIN)
async def admin_home(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ADMIN_HELP, reply_markup=admin_menu())


@router.message(F.text == BTN_BACK)
async def admin_back(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню.", reply_markup=main_menu(is_admin=True))


# ------------------------------------------------- мастер создания лекции

@router.message(Command("new"))
@router.message(F.text == BTN_NEW_LECTURE)
async def new_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(NewLecture.title)
    await message.answer(
        "➕ <b>Новая лекция</b> (шаг 1 из 7)\n\n"
        "Как называется лекция?\n"
        "<i>Отменить в любой момент — /cancel</i>"
    )


@router.message(NewLecture.title, F.text)
async def new_title(message: Message, state: FSMContext) -> None:
    title = " ".join(message.text.split())
    if not 3 <= len(title) <= MAX_TITLE:
        await message.answer(f"Название должно быть от 3 до {MAX_TITLE} символов.")
        return
    await state.update_data(title=title)
    await state.set_state(NewLecture.description)
    await message.answer(
        "Шаг 2 из 7. О чём лекция? Короткое описание для афиши.\n"
        f"<i>Пропустить — отправь «{SKIP}»</i>"
    )


@router.message(NewLecture.description, F.text)
async def new_description(message: Message, state: FSMContext) -> None:
    description = message.text.strip()
    if description == SKIP:
        description = None
    elif len(description) > MAX_DESCRIPTION:
        await message.answer(f"Слишком длинно: максимум {MAX_DESCRIPTION} символов.")
        return
    await state.update_data(description=description)
    await state.set_state(NewLecture.speaker)
    await message.answer(f"Шаг 3 из 7. Кто читает лекцию?\n<i>Пропустить — «{SKIP}»</i>")


@router.message(NewLecture.speaker, F.text)
async def new_speaker(message: Message, state: FSMContext) -> None:
    speaker = message.text.strip()
    if speaker == SKIP:
        speaker = None
    elif len(speaker) > MAX_SHORT:
        await message.answer(f"Максимум {MAX_SHORT} символов.")
        return
    await state.update_data(speaker=speaker)
    await state.set_state(NewLecture.place)
    await message.answer(f"Шаг 4 из 7. Где пройдёт лекция? (кабинет, актовый зал…)\n<i>Пропустить — «{SKIP}»</i>")


@router.message(NewLecture.place, F.text)
async def new_place(message: Message, state: FSMContext) -> None:
    place = message.text.strip()
    if place == SKIP:
        place = None
    elif len(place) > MAX_SHORT:
        await message.answer(f"Максимум {MAX_SHORT} символов.")
        return
    await state.update_data(place=place)
    await state.set_state(NewLecture.starts_at)
    await message.answer(f"Шаг 5 из 7. Когда начало?\nФормат: {DATE_INPUT_HINT}")


@router.message(NewLecture.starts_at, F.text)
async def new_starts_at(message: Message, state: FSMContext) -> None:
    when = parse_datetime(message.text)
    if when is None:
        await message.answer(f"Не понял дату. Нужен формат {DATE_INPUT_HINT}")
        return
    await state.update_data(starts_at=to_db(when))
    await state.set_state(NewLecture.capacity)
    await message.answer("Шаг 6 из 7. Сколько мест? Числом, например 25.")


@router.message(NewLecture.capacity, F.text)
async def new_capacity(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_CAPACITY:
        await message.answer(f"Нужно число от 1 до {MAX_CAPACITY}.")
        return
    await state.update_data(capacity=int(raw))
    await state.set_state(NewLecture.photo)
    await message.answer(f"Шаг 7 из 7. Пришли фото/афишу для анонса.\n<i>Без фото — «{SKIP}»</i>")


@router.message(NewLecture.photo, F.photo)
async def new_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await _show_preview(message, state, bot)


@router.message(NewLecture.photo, F.text == SKIP)
async def new_photo_skip(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.update_data(photo_file_id=None)
    await _show_preview(message, state, bot)


@router.message(NewLecture.photo)
async def new_photo_wrong(message: Message) -> None:
    await message.answer(f"Жду фото или «{SKIP}».")


async def _show_preview(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    preview = {**data, "id": 0, "booked": 0, "is_cancelled": 0}
    await state.set_state(NewLecture.confirm)
    await message.answer("👀 Вот так увидят афишу ученики:")
    await views.send_lecture_card(bot, message.chat.id, preview, new_lecture_confirm_kb())


@router.callback_query(NewLecture.confirm, F.data == "new:abort")
async def new_abort(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Черновик удалён")
    await callback.message.answer("Лекция не создана.", reply_markup=admin_menu())


@router.callback_query(NewLecture.confirm, F.data.in_({"new:save", "new:publish"}))
async def new_save(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    lecture_id = await db.create_lecture(
        title=data["title"],
        description=data.get("description"),
        speaker=data.get("speaker"),
        place=data.get("place"),
        starts_at=data["starts_at"],
        capacity=data["capacity"],
        photo_file_id=data.get("photo_file_id"),
        created_by=callback.from_user.id,
    )
    lecture = await db.get_lecture(lecture_id)
    await callback.message.answer(
        f"✅ Лекция сохранена (ID {lecture_id}).", reply_markup=admin_menu()
    )

    if callback.data == "new:publish":
        await _announce(bot, db, lecture, callback.message)


async def _announce(bot: Bot, db: Database, lecture, message: Message) -> None:
    user_ids = await db.all_user_ids()
    status = await message.answer(f"📢 Рассылаю афишу ({len(user_ids)} чел.)…")
    delivered, failed = await views.broadcast(
        bot,
        user_ids,
        text=texts.announcement(lecture),
        photo=lecture["photo_file_id"],
        reply_markup=announce_kb(lecture["id"]),
    )
    await status.edit_text(f"📢 Афиша отправлена: {delivered} доставлено, {failed} не дошло.")


# ------------------------------------------------------- управление лекциями

@router.message(Command("manage"))
@router.message(F.text == BTN_MANAGE)
async def manage(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    lectures = await db.list_lectures(only_upcoming=False, include_cancelled=True, limit=30)
    if not lectures:
        await message.answer("Лекций пока нет. Создай первую: «➕ Новая лекция».", reply_markup=admin_menu())
        return
    await message.answer(
        "🗂 <b>Все лекции</b> (сначала ближайшие)\nВыбери лекцию для управления.",
        reply_markup=admin_lectures_list(lectures),
    )


@router.callback_query(AdminCB.filter(F.action == "list"))
async def admin_list(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await views.safe_delete(callback.message)
    await manage(callback.message, state, db)


@router.callback_query(AdminCB.filter(F.action == "view"))
async def admin_view(callback: CallbackQuery, callback_data: AdminCB, db: Database, bot: Bot) -> None:
    await callback.answer()
    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        await callback.message.answer("Лекция не найдена.")
        return
    await views.safe_delete(callback.message)
    await views.send_lecture_card(
        bot, callback.message.chat.id, lecture, admin_card_kb(lecture), for_admin=True
    )


@router.callback_query(AdminCB.filter(F.action == "who"))
async def admin_who(callback: CallbackQuery, callback_data: AdminCB, db: Database) -> None:
    await callback.answer()
    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        await callback.message.answer("Лекция не найдена.")
        return
    rows = await db.lecture_bookings(lecture["id"])
    await callback.message.answer(texts.bookings_list(lecture, rows))


@router.callback_query(AdminCB.filter(F.action == "publish"))
async def admin_publish(callback: CallbackQuery, callback_data: AdminCB, db: Database, bot: Bot) -> None:
    await callback.answer()
    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        await callback.message.answer("Лекция не найдена.")
        return
    await _announce(bot, db, lecture, callback.message)


@router.callback_query(AdminCB.filter(F.action.in_({"cancel", "restore"})))
async def admin_cancel(callback: CallbackQuery, callback_data: AdminCB, db: Database, bot: Bot) -> None:
    cancelling = callback_data.action == "cancel"
    lecture = await db.get_lecture(callback_data.lecture_id)
    if lecture is None:
        await callback.answer("Лекция не найдена.", show_alert=True)
        return

    await db.set_cancelled(lecture["id"], cancelling)
    lecture = await db.get_lecture(lecture["id"])
    await callback.answer("Лекция отменена." if cancelling else "Лекция снова в расписании.")
    await views.edit_card(callback, lecture, admin_card_kb(lecture), for_admin=True)

    listeners = await db.booked_user_ids(lecture["id"])
    if listeners:
        prefix = "❌ <b>Лекция отменена</b>\n\n" if cancelling else "♻️ <b>Лекция снова в расписании</b>\n\n"
        delivered, _ = await views.broadcast(
            bot, listeners, text=prefix + texts.lecture_card(lecture)
        )
        await callback.message.answer(f"Оповестил записавшихся: {delivered} из {len(listeners)}.")


@router.callback_query(AdminCB.filter(F.action == "delete"))
async def admin_delete_confirm(callback: CallbackQuery, callback_data: AdminCB) -> None:
    await callback.answer()
    await callback.message.answer(
        "🗑 Удалить лекцию вместе со всеми записями? Отменить это будет нельзя.",
        reply_markup=confirm_delete_kb(callback_data.lecture_id),
    )


@router.callback_query(AdminCB.filter(F.action == "delete_yes"))
async def admin_delete(callback: CallbackQuery, callback_data: AdminCB, db: Database) -> None:
    await db.delete_lecture(callback_data.lecture_id)
    await callback.answer("Удалено")
    await views.safe_delete(callback.message)
    await callback.message.answer("🗑 Лекция удалена.", reply_markup=admin_menu())


# ------------------------------------------------------- редактирование полей

@router.callback_query(AdminCB.filter(F.action == "edit"))
async def admin_edit_menu(callback: CallbackQuery, callback_data: AdminCB) -> None:
    await callback.answer()
    await callback.message.answer(
        "✏️ Что меняем?", reply_markup=edit_fields_kb(callback_data.lecture_id)
    )


@router.callback_query(AdminCB.filter(F.action == "field"))
async def admin_edit_field(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext) -> None:
    await callback.answer()
    field = callback_data.field
    await state.set_state(EditLecture.value)
    await state.update_data(lecture_id=callback_data.lecture_id, field=field)

    hints = {
        "starts_at": f"Новая дата и время: {DATE_INPUT_HINT}",
        "capacity": f"Новое количество мест (1–{MAX_CAPACITY}):",
        "photo_file_id": f"Пришли новое фото (или «{SKIP}», чтобы убрать фото):",
        "description": f"Новое описание (или «{SKIP}», чтобы убрать):",
        "speaker": f"Новый лектор (или «{SKIP}», чтобы убрать):",
        "place": f"Новое место (или «{SKIP}», чтобы убрать):",
    }
    await callback.message.answer(
        hints.get(field, f"Новое значение для поля «{FIELD_LABELS.get(field, field)}»:")
        + "\n<i>Отмена — /cancel</i>"
    )


@router.message(EditLecture.value, F.photo)
async def admin_apply_photo(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    if data.get("field") != "photo_file_id":
        await message.answer("Сейчас жду текст, а не фото.")
        return
    await _apply_edit(message, state, db, bot, message.photo[-1].file_id)


@router.message(EditLecture.value, F.text)
async def admin_apply_value(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    field = data["field"]
    raw = message.text.strip()

    if field == "starts_at":
        when = parse_datetime(raw)
        if when is None:
            await message.answer(f"Не понял дату. Нужен формат {DATE_INPUT_HINT}")
            return
        value = to_db(when)
    elif field == "capacity":
        if not raw.isdigit() or not 1 <= int(raw) <= MAX_CAPACITY:
            await message.answer(f"Нужно число от 1 до {MAX_CAPACITY}.")
            return
        value = int(raw)
    elif field == "title":
        if not 3 <= len(raw) <= MAX_TITLE:
            await message.answer(f"Название — от 3 до {MAX_TITLE} символов.")
            return
        value = raw
    elif field == "photo_file_id":
        if raw != SKIP:
            await message.answer(f"Пришли фото или «{SKIP}», чтобы убрать его.")
            return
        value = None
    else:
        limit = MAX_DESCRIPTION if field == "description" else MAX_SHORT
        if raw == SKIP:
            value = None
        elif len(raw) > limit:
            await message.answer(f"Максимум {limit} символов.")
            return
        else:
            value = raw

    await _apply_edit(message, state, db, bot, value)


async def _apply_edit(message: Message, state: FSMContext, db: Database, bot: Bot, value) -> None:
    data = await state.get_data()
    lecture_id, field = data["lecture_id"], data["field"]
    await state.clear()

    lecture_before = await db.get_lecture(lecture_id)
    if lecture_before is None:
        await message.answer("Лекция не найдена — возможно, её удалили.", reply_markup=admin_menu())
        return

    await db.update_lecture(lecture_id, field, value)
    lecture = await db.get_lecture(lecture_id)
    await message.answer(f"✅ Поле «{FIELD_LABELS.get(field, field)}» обновлено.", reply_markup=admin_menu())
    await views.send_lecture_card(bot, message.chat.id, lecture, admin_card_kb(lecture), for_admin=True)

    if field == "starts_at" and lecture_before["starts_at"] != lecture["starts_at"]:
        listeners = await db.booked_user_ids(lecture_id)
        if listeners:
            await views.broadcast(
                bot,
                listeners,
                text=(
                    f"🕐 <b>Лекция «{esc(lecture['title'])}» перенесена</b>\n\n"
                    f"Было: {format_datetime(from_db(lecture_before['starts_at']))}\n"
                    f"Стало: {format_datetime(from_db(lecture['starts_at']))}"
                ),
            )
            await message.answer(f"Оповестил записавшихся: {len(listeners)} чел.")


# ------------------------------------------------------------------ рассылка

@router.message(Command("broadcast"))
@router.message(F.text == BTN_BROADCAST)
async def broadcast_start(message: Message, state: FSMContext, db: Database) -> None:
    await state.set_state(Broadcast.text)
    await message.answer(
        f"📢 Что разослать? Сообщение получат все зарегистрированные ({await db.users_count()} чел.).\n"
        "<i>Отмена — /cancel</i>"
    )


@router.message(Broadcast.text, F.text)
async def broadcast_send(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    await state.clear()
    user_ids = await db.all_user_ids()
    status = await message.answer(f"Отправляю ({len(user_ids)} чел.)…")
    delivered, failed = await views.broadcast(
        bot, user_ids, text=f"📢 <b>Объявление</b>\n\n{esc(message.text)}"
    )
    await status.edit_text(f"Готово: {delivered} доставлено, {failed} не дошло.")
