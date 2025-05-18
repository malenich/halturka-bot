
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from aiogram.utils import executor
from aiogram.dispatcher.filters import CommandStart
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()

@dp.message_handler(CommandStart())
async def start(message: types.Message):
    await message.answer("Привет! Отправь описание своей анкеты.")
    await Form.waiting_for_text.set()

@dp.message_handler(state=Form.waiting_for_text)
async def get_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Хочешь добавить фото? Пришли его или напиши /skip")
    await Form.waiting_for_photo.set()

@dp.message_handler(commands="skip", state=Form.waiting_for_photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    caption = f"Новая анкета от пользователя @{message.from_user.username or message.from_user.id}: {text}"
    await bot.send_message(chat_id=ADMIN_ID, text=caption)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.waiting_for_photo)
async def get_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    photo = message.photo[-1].file_id
    caption = f"Новая анкета от пользователя @{message.from_user.username or message.from_user.id}:
{text}"
    await bot.send_photo(chat_id=ADMIN_ID, photo=photo, caption=caption)
    await message.answer("Анкета с фото отправлена Каркуше на проверку. Спасибо!")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
