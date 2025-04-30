from aiogram.fsm.state import StatesGroup, State

class BroadcastState(StatesGroup):
    waiting_for_broadcast_message = State()


class BroadcastUserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_broadcast_message = State()
