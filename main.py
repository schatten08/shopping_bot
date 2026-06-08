import telebot
import os
import threading
from flask import Flask
from telebot import types
from storage import ShoppingList
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Инициализация Flask для Render (чтобы сервис не засыпал и проходил Health Check)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
storage = ShoppingList()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📝 Показать список")
    btn2 = types.KeyboardButton("❌ Очистить всё")
    markup.add(btn1, btn2)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Я твой список покупок. 🛒\n\n"
        "• Просто напиши мне название товара, чтобы добавить его.\n"
        "• Нажми на товар в списке, чтобы удалить его.\n"
        "• Команда /list покажет ваш список.\n"
        "• Команда /clear очистит всё.",
        reply_markup=markup
    )

@bot.message_handler(commands=['list'])
def handle_list_command(message):
    show_list(message)

@bot.message_handler(commands=['clear'])
def handle_clear_command(message):
    storage.clear_list()
    bot.send_message(message.chat.id, "Список полностью очищен! 🧹")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "📝 Показать список":
        show_list(message)
    elif message.text == "❌ Очистить всё":
        storage.clear_list()
        bot.send_message(message.chat.id, "Список полностью очищен! 🧹")
    else:
        item = message.text.strip()
        if storage.add_item(item):
            bot.send_message(message.chat.id, f"✅ Добавлено: *{item}*", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "Этот товар уже есть в списке!")

def show_list(message):
    items = storage.items
    if not items:
        bot.send_message(message.chat.id, "Ваш список покупок пуст. 📭")
        return

    markup = types.InlineKeyboardMarkup()
    for index, item in enumerate(items):
        callback_button = types.InlineKeyboardButton(
            text=f"✅ {item}", 
            callback_data=f"remove_{index}"
        )
        markup.add(callback_button)
    
    bot.send_message(message.chat.id, "Ваш список (нажми на ✅, чтобы вычеркнуть):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('remove_'))
def callback_inline(call):
    index = int(call.data.split('_')[1])
    removed_item = storage.remove_item(index)
    
    if removed_item:
        bot.answer_callback_query(call.id, f"Куплено: {removed_item}")
        # Удаляем старое сообщение и показываем обновленный список
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_list(call.message)

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    threading.Thread(target=run_flask).start()
    
    # Установка команд в меню Telegram
    bot.set_my_commands([
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("list", "Показать список покупок"),
        types.BotCommand("clear", "Очистить список"),
        types.BotCommand("help", "Помощь")
    ])
    
    print("Бот запущен...")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при работе бота: {e}")
