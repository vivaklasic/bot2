import logging
import requests
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
import firebase_admin
from firebase_admin import credentials, db

TOKEN = '7743943724:AAH93OLyNfOoY_jT6hlf9plQ9MfX54E-zZI'

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка Firebase
cred = credentials.Certificate(r"C:\Users\Admin\Downloads\botchoiseimage-firebase-adminsdk-fbsvc-fff457209b.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://botchoiseimage-default-rtdb.europe-west1.firebasedatabase.app/'
})

def get_images_from_google_sheets():
    url = "https://script.google.com/macros/s/AKfycbxft9_xr1BDEwynxrT1Cp1Scvds4tc5mWf6PIZdh_naYIfDKfsLdtVVuw9lA09Iz2k/exec"
    response = requests.get(url)
    data = response.json()
    return data

def save_to_firebase(user_id, choice, is_correct):
    ref = db.reference(f"user_choices/{user_id}")
    user_data = ref.get() or {}

    correct = user_data.get("correct", 0)
    wrong = user_data.get("wrong", 0)

    if is_correct:
        correct += 1
    else:
        wrong += 1

    ref.set({"correct": correct, "wrong": wrong})

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Привет! Давай начнем игру. Напиши /send_images, чтобы выбрать картинку.')

    context.user_data["rounds"] = 0
    context.user_data["correct"] = 0
    context.user_data["wrong"] = 0
    context.user_data["used_images"] = set()  # Запоминаем использованные картинки

    await send_images(update.message.chat_id, context)  # Запускаем первый раунд

async def send_images(chat_id, context: CallbackContext) -> None:
    if context.user_data["rounds"] >= 10:
        await show_results(chat_id, context)
        return

    images = get_images_from_google_sheets()

    correct_images = [img for img in images if img["is_correct"] == 1 and img["image_url"] not in context.user_data["used_images"]]
    wrong_images = [img for img in images if img["is_correct"] == 0 and img["image_url"] not in context.user_data["used_images"]]

    if not correct_images or not wrong_images:
        await context.bot.send_message(chat_id, "Ошибка: недостаточно изображений в базе данных.")
        return

    image1 = random.choice(correct_images)
    image2 = random.choice(wrong_images)

    context.user_data["used_images"].add(image1["image_url"])
    context.user_data["used_images"].add(image2["image_url"])

    keyboard1 = [[InlineKeyboardButton("Выбрать", callback_data=f"choose_1_{image1['is_correct']}")]]
    keyboard2 = [[InlineKeyboardButton("Выбрать", callback_data=f"choose_2_{image2['is_correct']}")]]

    reply_markup1 = InlineKeyboardMarkup(keyboard1)
    reply_markup2 = InlineKeyboardMarkup(keyboard2)

    msg1 = await context.bot.send_photo(chat_id=chat_id, photo=image1["image_url"], reply_markup=reply_markup1)
    msg2 = await context.bot.send_photo(chat_id=chat_id, photo=image2["image_url"], reply_markup=reply_markup2)

    context.user_data["messages"] = [msg1.message_id, msg2.message_id]

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    await query.answer()

    data = query.data.split('_')
    choice = int(data[1])
    is_correct = int(data[2])
    user_id = query.from_user.id

    save_to_firebase(user_id, choice, is_correct)

    if "messages" in context.user_data:
        for msg_id in context.user_data["messages"]:
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg_id, reply_markup=None)

    context.user_data["rounds"] += 1
    if is_correct:
        context.user_data["correct"] += 1
    else:
        context.user_data["wrong"] += 1

    response_text = f"Вы выбрали изображение {choice}: {'✅ Правильно!' if is_correct else '❌ Неправильно!'}"
    await query.message.reply_text(response_text)

    await send_images(chat_id, context)  # Отправляем новые картинки

async def show_results(chat_id, context: CallbackContext) -> None:
    correct = context.user_data.get("correct", 0)
    wrong = context.user_data.get("wrong", 0)
    total = correct + wrong

    result_text = f"""🏁 *Игра окончена!*  
Вы сделали 10 выборов.  
✅ Правильных: {correct}  
❌ Неправильных: {wrong}  
🎯 Точность: {round(correct / total * 100, 2)}%"""

    await context.bot.send_message(chat_id, result_text, parse_mode="Markdown")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()

if __name__ == '__main__':
    main()
