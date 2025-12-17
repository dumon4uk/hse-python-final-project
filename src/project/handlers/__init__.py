from aiogram import Router

from .start import router as start_router
from .download import router as download_router

router = Router()
router.include_router(start_router)
router.include_router(download_router)
