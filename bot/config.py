"""Загрузка настроек бота из окружения / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    token: str
    admin_ids: frozenset[int]
    db_path: Path


def _parse_admins(raw: str) -> frozenset[int]:
    ids = set()
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.lstrip("-").isdigit():
            raise ValueError(f"ADMIN_IDS: '{chunk}' не похоже на Telegram ID")
        ids.add(int(chunk))
    return frozenset(ids)


def load_config() -> Config:
    load_dotenv(BASE_DIR / ".env")

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Скопируй bot/.env.example в bot/.env и вставь токен от @BotFather."
        )

    admin_ids = _parse_admins(os.getenv("ADMIN_IDS", ""))
    if not admin_ids:
        raise RuntimeError(
            "Не задан ADMIN_IDS — без него никто не сможет создавать лекции. "
            "Свой ID можно узнать у @userinfobot."
        )

    db_path = Path(os.getenv("DB_PATH", "lectures.db"))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    return Config(token=token, admin_ids=admin_ids, db_path=db_path)
