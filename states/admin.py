from aiogram.fsm.state import State, StatesGroup


class SendMessageState(StatesGroup):
    waiting_for_message = State()
