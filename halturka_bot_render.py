
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_category = State()
    waiting_for_photo = State()
    waiting_for_admin_action = State()
    waiting_for_rejection_reason = State()

user_data = {}

category_keyboard = InlineKeyboardMarkup(row_width=2).add(
    InlineKeyboardButton("Вакансия", callback_data="category_Вакансия"),
    InlineKeyboardButton("Услуги", callback_data="category_Услуги"),
    InlineKeyboardButton("Аренда", callback_data="category_Аренда"),
    InlineKeyboardButton("Продажа / Отдаю", callback_data="category_Продажа"),
    InlineKeyboardButton("Другое", callback_data="category_Другое"),
)

@dp.message_handler(commands="start")
async def start(message: types.Message):
    await message.answer("Привет! Отправь описание своей анкеты.")
    await Form.waiting_for_text.set()

@dp.message_handler(state=Form.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Выбери категорию:", reply_markup=category_keyboard)
    await Form.waiting_for_category.set()

@dp.callback_query_handler(lambda c: c.data.startswith("category_"), state=Form.waiting_for_category)
async def get_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    await state.update_data(category=category)
    await callback.message.answer("Хочешь добавить фото? Пришли его или напиши /skip")
    await Form.waiting_for_photo.set()

@dp.message_handler(commands="skip", state=Form.waiting_for_photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_data[message.from_user.id] = data
    text = data["text"]
    category = data["category"]
    caption = f"Новая анкета от пользователя @{message.from_user.username or message.from_user.id}: Категория: {category} {text}"
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{message.from_user.id}")
    )
    await bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=keyboard)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.waiting_for_photo)
async def get_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_data[message.from_user.id] = {**data, "photo": message.photo[-1].file_id}
    caption = f"Новая анкета от пользователя @{message.from_user.username or message.from_user.id}: Категория: {data['category']} {data['text']}"
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{message.from_user.id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{message.from_user.id}")
    )
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=keyboard)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    data = user_data.get(user_id)
    if not data:
        await callback.answer("Данные не найдены.")
        return
    text = f"Категория: {data['category']} {data['text']}"
    if "photo" in data:
        await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=data["photo"], caption=text)
    else:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=text)
    await bot.send_message(chat_id=user_id, text="Каркуша подтвердил твою анкету, она отправлена на публикацию.")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Анкета опубликована.")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    await state.update_data(target_user=user_id)
    await callback.message.answer("Напиши причину отказа.")
    await Form.waiting_for_rejection_reason.set()

@dp.message_handler(state=Form.waiting_for_rejection_reason)
async def rejection_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["target_user"]
    await bot.send_message(chat_id=user_id, text="Каркуша отклонил твою анкету, она не будет опубликована.")
    await bot.send_message(chat_id=user_id, text=f"Причина отказа: {message.text} Попробуй снова, устранив причину отказа.")
    await message.answer("Отказ отправлен.")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
