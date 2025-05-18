
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
import os

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()

@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    await message.answer("Привет! Отправь текст анкеты.")
    await Form.waiting_for_text.set()

@dp.message_handler(state=Form.waiting_for_text, content_types=types.ContentTypes.TEXT)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Хочешь добавить фото? Пришли его или напиши /skip")
    await Form.waiting_for_photo.set()

@dp.message_handler(commands="skip", state=Form.waiting_for_photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await send_to_admin(message.from_user.id, data["text"], None)
    await state.finish()
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")

@dp.message_handler(state=Form.waiting_for_photo, content_types=types.ContentTypes.PHOTO)
async def get_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo = message.photo[-1].file_id
    await send_to_admin(message.from_user.id, data["text"], photo)
    await state.finish()
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")

async def send_to_admin(user_id, text, photo):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve:{user_id}"),
        types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")
    )
    caption = f"Новая анкета от пользователя @{user_id}:"

{text}"
    if photo:
        await bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=keyboard)

@dp.callback_query_handler(Text(startswith="approve:"))
async def approve_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    user_id = int(callback.data.split(":")[1])
    msg = callback.message
    if msg.photo:
        await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=msg.photo[-1].file_id, caption=msg.caption)
    else:
        await bot.send_message(chat_id=CHANNEL_USERNAME, text=msg.text)
    await bot.send_message(user_id, "Каркуша подтвердил твою анкету, она отправлена на публикацию")
    await callback.answer("Анкета опубликована.")

@dp.callback_query_handler(Text(startswith="reject:"))
async def reject_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    user_id = int(callback.data.split(":")[1])
    await state.update_data(reject_user=user_id)
    await bot.send_message(ADMIN_ID, "Укажи причину отказа.")
    await Form.waiting_for_text.set()

@dp.message_handler(state=Form.waiting_for_text)
async def get_reject_reason(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("reject_user")
    reason = message.text
    text = (
        "Каркуша отклонил твою анкету, она не будет опубликована.
"
        f"Причина: {reason}
"
        "Попробуйте снова, устранив причину отказа."
    )
    await bot.send_message(user_id, text)
    await message.answer("Ответ отправлен пользователю.")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
