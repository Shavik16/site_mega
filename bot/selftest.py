"""Самопроверка бота: прогон основных сценариев через диспетчер с фейковой сессией Telegram.

Токен не нужен, к Telegram не ходит, база создаётся во временном файле.
Запуск:  python selftest.py
"""
import asyncio, os, sys, tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Даты лекций считаем от «сегодня», чтобы тест не протух.
LECTURE_DT = datetime.now() + timedelta(days=30)
MOVED_DT = LECTURE_DT + timedelta(days=1, hours=2)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (CallbackQuery, Chat, Message, PhotoSize, Update, User)

from db import Database
from handlers import build_router

ADMIN = 1
STUDENT = 2
STUDENT2 = 3


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def close(self):
        pass

    async def stream_content(self, *args, **kwargs):
        yield b""

    async def make_request(self, bot, method, timeout=None):
        name = type(method).__name__
        payload = method.model_dump(exclude_none=True)
        self.calls.append((name, payload))
        if name == "GetMe":
            return User(id=99, is_bot=True, first_name="LectureBot", username="lecture_bot")
        if name in {"SendMessage", "SendPhoto", "EditMessageText", "EditMessageCaption"}:
            msg = Message(
                message_id=len(self.calls),
                date=datetime.now(),
                chat=Chat(id=payload.get("chat_id", 0), type="private"),
                text=payload.get("text"),
                caption=payload.get("caption"),
            )
            return msg.as_(bot)
        return True

    def texts(self):
        return [p.get("text") or p.get("caption") or "" for n, p in self.calls
                if n in {"SendMessage", "SendPhoto", "EditMessageText", "EditMessageCaption", "AnswerCallbackQuery"}]

    def last(self, n=1):
        return self.texts()[-n:]

    def reset(self):
        self.calls.clear()


session = FakeSession()
bot = Bot("111:TEST", session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
_uid = [100]


def msg(user_id, text=None, photo=False):
    _uid[0] += 1
    return Update(update_id=_uid[0], message=Message(
        message_id=_uid[0],
        date=datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="U", username=f"user{user_id}"),
        text=text,
        photo=[PhotoSize(file_id="PHOTO123", file_unique_id="u", width=100, height=100)] if photo else None,
    ))


def cb(user_id, data):
    _uid[0] += 1
    return Update(update_id=_uid[0], callback_query=CallbackQuery(
        id=str(_uid[0]),
        from_user=User(id=user_id, is_bot=False, first_name="U", username=f"user{user_id}"),
        chat_instance="ci",
        data=data,
        message=Message(
            message_id=_uid[0],
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=User(id=99, is_bot=True, first_name="B"),
            text="карточка",
        ),
    ))


def check(cond, label):
    print(("  OK   " if cond else "  FAIL ") + label)
    if not cond:
        print("     последние сообщения:", session.texts()[-3:])
        raise SystemExit(1)


async def main():
    tmp = tempfile.mktemp(suffix=".db")
    db = Database(tmp)
    await db.connect()
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["admin_ids"] = {ADMIN}
    dp.include_router(build_router())

    async def feed(update):
        session.reset()
        await dp.feed_update(bot, update)
        return session.texts()

    print("1. Регистрация ученика")
    out = await feed(msg(STUDENT, "/start"))
    check(any("фамилию" in t for t in out), "просит ФИО")
    out = await feed(msg(STUDENT, "Петров"))
    check(any("Не похоже на ФИО" in t for t in out), "отбивает неполное ФИО")
    out = await feed(msg(STUDENT, "Петров Пётр Петрович"))
    check(any("класс" in t for t in out), "просит класс")
    out = await feed(msg(STUDENT, "10-Б"))
    check(any("Готово" in t for t in out), "регистрация завершена")
    user = await db.get_user(STUDENT)
    check(user["full_name"] == "Петров Пётр Петрович" and user["grade"] == "10-Б", "данные в базе")

    print("2. Повторный /start не переспрашивает")
    out = await feed(msg(STUDENT, "/start"))
    check(any("С возвращением" in t for t in out), "узнаёт ученика")

    print("3. Ученик без лекций")
    out = await feed(msg(STUDENT, "📅 Лекции"))
    check(any("Пока ни одной лекции" in t for t in out), "пустая афиша")

    print("4. Преподаватель создаёт лекцию с фото")
    await feed(msg(ADMIN, "/start"))
    await feed(msg(ADMIN, "Сидоров Иван Иванович"))
    await feed(msg(ADMIN, "учитель"))
    out = await feed(msg(ADMIN, "⚙️ Админка"))
    check(any("Админка" in t for t in out), "меню админки")
    out = await feed(msg(ADMIN, "➕ Новая лекция"))
    check(any("шаг 1" in t.lower() for t in out), "шаг 1")
    await feed(msg(ADMIN, "Чёрные дыры и как в них не упасть"))
    await feed(msg(ADMIN, "Разберём горизонт событий и парадокс близнецов."))
    await feed(msg(ADMIN, "Сидоров И.И."))
    await feed(msg(ADMIN, "Каб. 214"))
    out = await feed(msg(ADMIN, "завтра"))
    check(any("Не понял дату" in t for t in out), "валидация даты")
    await feed(msg(ADMIN, LECTURE_DT.strftime("%d.%m.%Y %H:%M")))
    out = await feed(msg(ADMIN, "0"))
    check(any("число от 1" in t for t in out), "валидация мест")
    await feed(msg(ADMIN, "2"))
    out = await feed(msg(ADMIN, None, photo=True))
    check(any("Чёрные дыры" in t for t in out), "предпросмотр афиши")
    check(any(n == "SendPhoto" for n, _ in session.calls), "предпросмотр ушёл фотографией")
    out = await feed(cb(ADMIN, "new:publish"))
    check(any("сохранена" in t for t in out), "лекция сохранена")
    check(any("Новая лекция!" in t for t in out), "афиша разослана")
    lectures = await db.list_lectures()
    check(len(lectures) == 1 and lectures[0]["photo_file_id"] == "PHOTO123", "лекция в базе с фото")
    lec_id = lectures[0]["id"]

    print("5. Ученик бронирует место")
    out = await feed(msg(STUDENT, "📅 Лекции"))
    check(any("Ближайшие лекции" in t for t in out), "список лекций")
    out = await feed(cb(STUDENT, f"lec:view:{lec_id}"))
    check(any("Свободно 2 из 2" in t for t in out), "карточка со свободными местами")
    out = await feed(cb(STUDENT, f"lec:book:{lec_id}"))
    check(any("забронировано" in t for t in out), "бронь принята")
    check(await db.is_booked(lec_id, STUDENT), "бронь в базе")
    out = await feed(cb(STUDENT, f"lec:book:{lec_id}"))
    check(any("уже записан" in t for t in out), "повторная бронь отбита")
    out = await feed(msg(STUDENT, "🎟 Мои записи"))
    check(any("Твои записи" in t for t in out), "мои записи")

    print("6. Мест не хватает")
    await feed(msg(STUDENT2, "/start"))
    await feed(msg(STUDENT2, "Иванова Мария"))
    await feed(msg(STUDENT2, "9-А"))
    await feed(cb(STUDENT2, f"lec:book:{lec_id}"))
    await db.update_lecture(lec_id, "capacity", 2)
    out = await feed(cb(STUDENT2, f"lec:book:{lec_id}"))
    check(any("уже записан" in t for t in out), "второй ученик записан")
    await db.update_lecture(lec_id, "capacity", 2)
    check((await db.get_lecture(lec_id))["booked"] == 2, "мест занято 2")
    _uid[0] += 1
    await db.save_user(4, "Третий Ученик", "8-В", None)
    out = await feed(cb(4, f"lec:book:{lec_id}"))
    check(any("Все места заняты" in t for t in out), "третьему мест нет")

    print("7. Преподаватель смотрит список и правит лекцию")
    out = await feed(cb(ADMIN, f"adm:who:{lec_id}:"))
    check(any("Петров Пётр Петрович" in t and "10-Б" in t for t in out), "список записавшихся")
    out = await feed(cb(ADMIN, f"adm:field:{lec_id}:starts_at"))
    check(any("Новая дата" in t for t in out), "запрос новой даты")
    out = await feed(msg(ADMIN, MOVED_DT.strftime("%d.%m.%Y %H:%M")))
    check(any("обновлено" in t for t in out), "поле обновлено")
    check(any("перенесена" in t for t in out), "записавшихся оповестили")
    out = await feed(cb(ADMIN, f"adm:cancel:{lec_id}:"))
    check(any("Лекция отменена" in t for t in out), "лекция отменена")
    check((await db.get_lecture(lec_id))["is_cancelled"] == 1, "флаг отмены в базе")
    out = await feed(cb(ADMIN, f"adm:delete_yes:{lec_id}:"))
    check(any("удалена" in t for t in out), "лекция удалена")
    check(await db.get_lecture(lec_id) is None, "лекции нет в базе")

    print("8. Ученик не может в админку")
    out = await feed(msg(STUDENT, "⚙️ Админка"))
    check(any("Не понял" in t for t in out), "админка недоступна ученику")

    await db.close()
    os.remove(tmp)
    print("\nВСЕ СЦЕНАРИИ ПРОЙДЕНЫ")


asyncio.run(main())
