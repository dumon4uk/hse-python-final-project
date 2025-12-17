from aiogram.fsm.state import StatesGroup, State


class DownloadStates(StatesGroup):
    waiting_link = State()
    waiting_type = State()
    waiting_format = State()
    downloading = State()
