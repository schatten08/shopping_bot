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

# Список разрешенных пользователей
ALLOWED_USERS = [int(id.strip()) for id in os.getenv('ALLOWED_USERS', '').split(',') if id.strip()]

def restricted(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id not in ALLOWED_USERS:
            print(f"Доступ запрещен для пользователя {user_id}")
            bot.send_message(message.chat.id, "Извините, у вас нет доступа к этому боту. 🔒")
            return
        return func(message, *args, **kwargs)
    return wrapper

@bot.message_handler(commands=['start', 'help'])
@restricted
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
@restricted
def handle_list_command(message):
    show_list(message)

@bot.message_handler(commands=['clear'])
@restricted
def handle_clear_command(message):
    storage.clear_list()
    bot.send_message(message.chat.id, "Список полностью очищен! 🧹")

@bot.message_handler(func=lambda message: True)
@restricted
def handle_message(message):
    if message.text == "📝 Показать список":
        show_list(message)
    elif message.text == "❌ Очистить всё":
        storage.clear_list()
        bot.send_message(message.chat.id, "Список полностью очищен! 🧹")
    else:
        # Разбиваем сообщение по запятым и убираем лишние пробелы
        items = [i.strip() for i in message.text.split(',') if i.strip()]
        
        if len(items) > 1:
            added_count = 0
            for item in items:
                if storage.add_item(item):
                    added_count += 1
            
            if added_count > 0:
                bot.send_message(message.chat.id, f"✅ Добавлено несколько товаров ({added_count})!")
            else:
                bot.send_message(message.chat.id, "Все эти товары уже есть в списке!")
        else:
            # Одиночный товар
            item = items[0]
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
    # Проверка доступа для callback-запросов
    if call.from_user.id not in ALLOWED_USERS:
        bot.answer_callback_query(call.id, "У вас нет доступа! 🔒", show_alert=True)
        return

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
