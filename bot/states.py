"""Состояния FSM."""
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State()
    grade = State()


class NewLecture(StatesGroup):
    title = State()
    description = State()
    speaker = State()
    place = State()
    starts_at = State()
    capacity = State()
    photo = State()
    confirm = State()


class EditLecture(StatesGroup):
    value = State()


class Broadcast(StatesGroup):
    text = State()
