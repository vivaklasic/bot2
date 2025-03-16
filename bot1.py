import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import requests

# Токен от твоего бота
TOKEN = 'YOUR_BOT_TOKEN'

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Получение картинок из Google Таблицы (API)
def get_images_from_google_sheets():
    url = "https://script.google.com/macros/s/YOUR_SCRIPT_URL/exec"
    response = requests.get(url)
    data = response.json()
    return data

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Давай начнем игру.")

# Отправка картинок с кнопками
@dp.message_handler(commands=['send_images'])
async def send_images(message: types.Message):
    images = get_images_from_google_sheets()
    
    for image in images:
        image_url = image['image_url']
        is_correct = image['is_correct']

        # Кнопки для выбора
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Правильно", callback_data=f'correct_{is_correct}'),
            InlineKeyboardButton("Неправильно", callback_data=f'incorrect_{is_correct}')
        )

        # Отправка картинки
        await message.answer_photo(photo=image_url, reply_markup=keyboard)

# Обработка кнопок
@dp.callback_query_handler(lambda query: query.data.startswith('correct') or query.data.startswith('incorrect'))
async def handle_button(query: types.CallbackQuery):
    data = query.data.split('_')
    answer = data[0]
    is_correct = int(data[1])

    if answer == 'correct' and is_correct == 1:
        await query.answer("Правильно!")
    elif answer == 'incorrect' and is_correct == 0:
        await query.answer("Правильно!")
    else:
        await query.answer("Неправильно!")

# Запуск бота
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
