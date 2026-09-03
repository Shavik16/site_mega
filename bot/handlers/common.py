"""Старт, регистрация (один раз: ФИО + класс), профиль, помощь."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

import texts
from db import Database
from keyboards import BTN_PROFILE, main_menu
from states import Registration
from utils import esc

router = Router(name="common")

NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-zЇїІіЄєҐґ'\-\s]{5,80}$")

WELCOME = (
    "👋 Привет! Это бот школьных лекций.\n\n"
    "Здесь преподаватели выкладывают афиши лекций, а ты бронируешь место в один клик.\n"
    "Регистрация нужна один раз — чтобы лектор видел, кто придёт."
)
ASK_NAME = "✍️ Напиши свои <b>фамилию, имя и отчество</b> (например: Иванов Иван Иванович)."
ASK_GRADE = "🎓 Отлично! Теперь напиши свой <b>класс</b> (например: 10-Б)."


def _profile_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить данные", callback_data="profile:edit")
    return kb.as_markup()


async def start_registration(message: Message, state: FSMContext, greeting: str = WELCOME) -> None:
    await state.set_state(Registration.full_name)
    await message.answer(greeting, reply_markup=ReplyKeyboardRemove())
    await message.answer(ASK_NAME)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database, admin_ids: set[int]) -> None:
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user is None:
        await start_registration(message, state)
        return
    is_admin = message.from_user.id in admin_ids
    await message.answer(
        f"С возвращением, {esc(user['full_name'].split()[0])}! 👋\n\n{texts.MAIN_HELP}",
        reply_markup=main_menu(is_admin),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, db: Database, admin_ids: set[int]) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    if current in {Registration.full_name.state, Registration.grade.state} and not await db.get_user(
        message.from_user.id
    ):
        await message.answer("Без регистрации бот не работает. Напиши ФИО ещё раз.")
        return
    await state.clear()
    await message.answer("Отменил.", reply_markup=main_menu(message.from_user.id in admin_ids))


@router.message(Registration.full_name, F.text)
async def reg_full_name(message: Message, state: FSMContext) -> None:
    name = " ".join(message.text.split())
    if not NAME_RE.match(name) or len(name.split()) < 2:
        await message.answer(
            "Не похоже на ФИО 🤔 Напиши хотя бы фамилию и имя буквами, например: Иванов Иван."
        )
        return
    await state.update_data(full_name=name)
    await state.set_state(Registration.grade)
    await message.answer(ASK_GRADE)


@router.message(Registration.grade, F.text)
async def reg_grade(message: Message, state: FSMContext, db: Database, admin_ids: set[int]) -> None:
    grade = " ".join(message.text.split())
    if not 1 <= len(grade) <= 15:
        await message.answer("Класс — это что-то короткое, например 10-Б. Попробуй ещё раз.")
        return

    data = await state.get_data()
    await db.save_user(
        user_id=message.from_user.id,
        full_name=data["full_name"],
        grade=grade,
        username=message.from_user.username,
    )
    await state.clear()
    await message.answer(
        f"✅ Готово! {esc(data['full_name'])}, {esc(grade)}.\n\n{texts.MAIN_HELP}",
        reply_markup=main_menu(message.from_user.id in admin_ids),
    )


@router.message(Registration.full_name)
@router.message(Registration.grade)
async def reg_wrong_type(message: Message) -> None:
    await message.answer("Нужен текст 🙂")


@router.message(Command("help"))
async def cmd_help(message: Message, admin_ids: set[int]) -> None:
    text = texts.MAIN_HELP
    if message.from_user.id in admin_ids:
        text += "\n\n" + texts.ADMIN_HELP
    await message.answer(text, reply_markup=main_menu(message.from_user.id in admin_ids))


@router.message(Command("profile"))
@router.message(F.text == BTN_PROFILE)
async def show_profile(message: Message, state: FSMContext, db: Database) -> None:
    user = await db.get_user(message.from_user.id)
    if user is None:
        await start_registration(message, state, "Сначала короткая регистрация 👇")
        return
    await message.answer(texts.profile(user), reply_markup=_profile_kb())


@router.callback_query(F.data == "profile:edit")
async def edit_profile(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(Registration.full_name)
    await callback.message.answer(ASK_NAME)
