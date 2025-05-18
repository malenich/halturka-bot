# -*- coding: utf-8 -*-
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import logging

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    category = State()
    text = State()
    photo = State()

category_kb = ReplyKeyboardMarkup(resize_keyboard=True)
category_kb.add("Вакансия", "Услуги").add("Аренда", "Продажа / Отдаю").add("Другое")

@dp.message_handler(commands='start')
async def start_handler(message: types.Message):
    await message.answer("Привет! Давай создадим анкету. Выбери категорию:", reply_markup=category_kb)
    await Form.category.set()

@dp.message_handler(state=Form.category)
async def category_chosen(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Теперь напиши текст объявления:")
    await Form.text.set()

@dp.message_handler(state=Form.text)
async def text_entered(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Хочешь добавить фото? Пришли его или напиши /skip")
    await Form.photo.set()

@dp.message_handler(commands='skip', state=Form.photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = f"📌 Новая анкета от пользователя @{message.from_user.username or 'без ника'}\n\n"
    text += f"📂 Категория: {data['category']}\n\n"
    text += f"{data['text']}"
    await bot.send_message(ADMIN_ID, text)
    await message.answer("Анкета отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.message_handler(content_types=['photo'], state=Form.photo)
async def photo_added(message: types.Message, state: FSMContext):
    data = await state.get_data()
    caption = f"📌 Новая анкета от пользователя @{message.from_user.username or 'без ника'}\n\n"
    caption += f"📂 Категория: {data['category']}\n\n"
    caption += f"{data['text']}"
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
