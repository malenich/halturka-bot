
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    category = State()
    text = State()
    photo = State()

@dp.message_handler(commands="start")
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Вакансия", "Услуги")
    keyboard.add("Аренда", "Продажа / Отдаю")
    keyboard.add("Другое")
    await message.answer("Выбери категорию", reply_markup=keyboard)
    await Form.category.set()

@dp.message_handler(state=Form.category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Отправь текст объявления.")
    await Form.text.set()

@dp.message_handler(state=Form.text)
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Хочешь добавить фото? Пришли его или напиши /skip")
    await Form.photo.set()

@dp.message_handler(commands="skip", state=Form.photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await send_application(message, data, state)

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.photo)
async def get_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data["photo"] = message.photo[-1].file_id
    await send_application(message, data, state)

async def send_application(message, data, state):
    user = message.from_user
    caption = f"Новая анкета от пользователя @{user.username or user.id}:

Категория: {data['category']}

{data['text']}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{user.id}"))
    kb.add(InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user.id}"))
    if "photo" in data:
        await bot.send_photo(chat_id=ADMIN_ID, photo=data["photo"], caption=caption, reply_markup=kb)
    else:
        await bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=kb)

    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
async def handle_moderation(callback_query: types.CallbackQuery):
    action, user_id = callback_query.data.split("_")
    user_id = int(user_id)

    if action == "approve":
        await bot.send_message(user_id, "Каркуша подтвердил твою анкету, она отправлена на публикацию.")
        await bot.copy_message(chat_id=CHANNEL_USERNAME, from_chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    else:
        await bot.send_message(callback_query.from_user.id, "Напиши причину отказа:")
        await bot.send_message(user_id, "Каркуша отклонил твою анкету, она не будет опубликована. Причина отказа придёт отдельно.")

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
