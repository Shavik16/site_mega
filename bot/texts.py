"""Сборка текстов сообщений."""
from __future__ import annotations

import aiosqlite

from utils import esc, format_datetime, from_db

SKIP = "-"

MAIN_HELP = (
    "Я бот школьных лекций.\n\n"
    "📅 <b>Лекции</b> — афиша ближайших лекций и бронь места\n"
    "🎟 <b>Мои записи</b> — куда ты уже записан(а)\n"
    "👤 <b>Профиль</b> — твои ФИО и класс\n\n"
    "Команды: /lectures, /my, /profile, /help"
)

ADMIN_HELP = (
    "⚙️ <b>Админка преподавателя</b>\n\n"
    "• <b>Новая лекция</b> — мастер из 7 шагов, с афишей и фото\n"
    "• <b>Все лекции</b> — правка, отмена, удаление, список записавшихся\n"
    "• <b>Рассылка</b> — сообщение всем зарегистрированным\n\n"
    "Команды: /new, /manage, /broadcast"
)


def lecture_card(lecture: aiosqlite.Row | dict, *, for_admin: bool = False) -> str:
    """Красивая карточка лекции (HTML)."""
    booked = int(lecture["booked"] or 0)
    capacity = int(lecture["capacity"])
    free = max(capacity - booked, 0)
    starts_at = from_db(lecture["starts_at"])

    lines = [f"📚 <b>{esc(lecture['title'])}</b>", ""]
    lines.append(f"🗓 {format_datetime(starts_at)}")
    if lecture["place"]:
        lines.append(f"📍 {esc(lecture['place'])}")
    if lecture["speaker"]:
        lines.append(f"🎤 {esc(lecture['speaker'])}")
    lines.append(f"👥 Свободно {free} из {capacity}" if free else f"👥 Мест нет ({capacity} из {capacity})")

    if lecture["description"]:
        lines += ["", esc(lecture["description"])]

    if lecture["is_cancelled"]:
        lines += ["", "❌ <b>Лекция отменена</b>"]

    if for_admin:
        lines += ["", f"<i>ID лекции: {lecture['id']} · записалось: {booked}</i>"]

    return "\n".join(lines)


def announcement(lecture: aiosqlite.Row | dict) -> str:
    return "🔔 <b>Новая лекция!</b>\n\n" + lecture_card(lecture)


def lecture_button_label(lecture: aiosqlite.Row | dict, *, booked_by_me: bool = False) -> str:
    from utils import format_short

    free = max(int(lecture["capacity"]) - int(lecture["booked"] or 0), 0)
    mark = "✅" if booked_by_me else ("🔴" if not free else "🟢")
    if lecture["is_cancelled"]:
        mark = "❌"
    title = lecture["title"]
    if len(title) > 30:
        title = title[:29] + "…"
    return f"{mark} {format_short(from_db(lecture['starts_at']))} · {title}"


def bookings_list(lecture: aiosqlite.Row | dict, rows: list[aiosqlite.Row]) -> str:
    head = f"🎟 <b>Записались на «{esc(lecture['title'])}»</b> — {len(rows)} из {lecture['capacity']}"
    if not rows:
        return head + "\n\nПока никто не записался."
    lines = [head, ""]
    for i, row in enumerate(rows, 1):
        contact = f" (@{esc(row['username'])})" if row["username"] else ""
        lines.append(f"{i}. {esc(row['full_name'])} — {esc(row['grade'])}{contact}")
    return "\n".join(lines)


def profile(user: aiosqlite.Row) -> str:
    return (
        "👤 <b>Профиль</b>\n\n"
        f"ФИО: {esc(user['full_name'])}\n"
        f"Класс: {esc(user['grade'])}\n\n"
        "Ошибка в данных? Нажми «Изменить данные»."
    )
