from aiogram import Router

from . import admin, common, student


def build_router() -> Router:
    """Собирает роутеры в порядке приоритета: регистрация -> админка -> ученики."""
    router = Router(name="root")
    router.include_router(common.router)
    router.include_router(admin.router)
    router.include_router(student.router)
    return router
