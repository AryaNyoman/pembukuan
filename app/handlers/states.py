from aiogram.fsm.state import State, StatesGroup


class PendingTransaction(StatesGroup):
    waiting_confirmation = State()


class EditingTransaction(StatesGroup):
    waiting_for_text = State()


class AddingBudget(StatesGroup):
    waiting_for_text = State()
