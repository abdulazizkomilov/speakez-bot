from aiogram.fsm.state import StatesGroup, State

class PromoState(StatesGroup):
    waiting_for_code = State()
