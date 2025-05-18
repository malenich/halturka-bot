import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    waiting_for_admin_action = State()
    waiting_for_rejection_reason = State()

user_data = {}

@dp.message_handler(commands="start")
async def start(message: types.Message):
    await message.answer("Привет! Отправь описание своей анкеты.")
    await Form.waiting_for_text.set()

@dp.message_handler(state=Form.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text, user_id=message.from_user.id, username=message.from_user.username)
    await message.answer("Хочешь добавить фото? Пришли его или напиши /skip")
    await Form.waiting_for_photo.set()

@dp.message_handler(commands="skip", state=Form.waiting_for_photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    user_id = data["user_id"]
    username = data["username"]
    caption = f"📝 Новая анкета от пользователя @{username or user_id}:
{text}"
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
    )
    user_data[user_id] = caption
    await bot.send_message(chat_id=ADMIN_ID, text=caption, reply_markup=keyboard)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.waiting_for_photo)
async def get_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    user_id = message.from_user.id
    username = message.from_user.username
    caption = f"📝 Новая анкета от пользователя @{username or user_id}:
{text}"
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
    )
    user_data[user_id] = (message.photo[-1].file_id, caption)
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=keyboard)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("approve_") or c.data.startswith("reject_"))
async def process_callback(callback_query: types.CallbackQuery):
    action, user_id = callback_query.data.split("_")
    user_id = int(user_id)
    if action == "approve":
        content = user_data.get(user_id)
        if isinstance(content, tuple):
            file_id, caption = content
            await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=file_id, caption=caption)
        else:
            await bot.send_message(chat_id=CHANNEL_USERNAME, text=content)
        await bot.send_message(chat_id=user_id, text="Каркуша подтвердил твою анкету, она отправлена на публикацию.")
    else:
        await bot.send_message(chat_id=callback_query.from_user.id, text="Напиши причину отказа:")
        await Form.waiting_for_rejection_reason.set()
        await dp.current_state(user=callback_query.from_user.id).update_data(target_user_id=user_id)
    await callback_query.answer()

@dp.message_handler(state=Form.waiting_for_rejection_reason)
async def handle_rejection_reason(message: types.Message, state: FSMContext):
    reason = message.text
    data = await state.get_data()
    user_id = data["target_user_id"]
    await bot.send_message(chat_id=user_id, text=f"Каркуша отклонил твою анкету, она не будет опубликована.
Причина: {reason}
Попробуйте снова, устранив причину отказа.")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)