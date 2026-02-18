from aiogram.fsm.state import State, StatesGroup


class FoodAddStates(StatesGroup):
    waiting_category = State()
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_rating = State()
    waiting_image = State()
    waiting_is_new = State()


class FoodEditStates(StatesGroup):
    waiting_field = State()
    waiting_value = State()


class PromoCreateStates(StatesGroup):
    waiting_code = State()
    waiting_discount = State()
    waiting_expires = State()
    waiting_limit = State()


class CourierAddStates(StatesGroup):
    waiting_chat_id = State()
    waiting_name = State()


class CategoryAddStates(StatesGroup):
    waiting_name = State()


class SettingsStates(StatesGroup):
    waiting_shop_channel = State()
    waiting_courier_channel = State()
