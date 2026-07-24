from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    risk_ack = State()
    password = State()
    password_confirm = State()


class Unlock(StatesGroup):
    password = State()
    pin = State()


class AddWallet(StatesGroup):
    entry_type = State()
    name = State()
    note = State()
    seed = State()


class EditWallet(StatesGroup):
    new_name = State()
    new_note = State()


class SearchWallet(StatesGroup):
    query = State()


class ReAuth(StatesGroup):
    password = State()


class ViewWallet(StatesGroup):
    confirm = State()


class DeleteWallet(StatesGroup):
    confirm = State()


class DeleteAccount(StatesGroup):
    confirm = State()


class BackupRestore(StatesGroup):
    password = State()
    waiting_file = State()


class ExportWallet(StatesGroup):
    password = State()


class SetupPin(StatesGroup):
    pin = State()
    pin_confirm = State()


class SetupDuress(StatesGroup):
    password = State()
    password_confirm = State()


class AddDecoyWallet(StatesGroup):
    name = State()
    seed = State()
