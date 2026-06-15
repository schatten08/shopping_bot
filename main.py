import telebot
import os
import threading
import speech_recognition as sr
from pydub import AudioSegment
from flask import Flask
from telebot import types
from storage import ShoppingList
from ai_wrapper import ai_provider
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Настройка пути к ffmpeg для Render
if os.path.exists("/opt/render/project/src/ffmpeg_bin/ffmpeg"):
    AudioSegment.converter = "/opt/render/project/src/ffmpeg_bin/ffmpeg"

# Инициализация Flask для Render
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
        print(f"DEBUG: Попытка доступа от ID {user_id}")
        if user_id not in ALLOWED_USERS:
            print(f"DEBUG: Доступ запрещен для пользователя {user_id}. Разрешенные: {ALLOWED_USERS}")
            bot.send_message(message.chat.id, "Извините, у вас нет доступа к этому боту. 🔒")
            return
        return func(message, *args, **kwargs)
    return wrapper

@bot.message_handler(commands=['start', 'help'])
@restricted
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📝 Показать список")
    btn2 = types.KeyboardButton("⭐ Частое")
    btn3 = types.KeyboardButton("❌ Очистить всё")
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(
        message.chat.id, 
        "Привет! Я твой список покупок. 🛒\n\n"
        "• Просто напиши товар или отправь **голосовое**, чтобы добавить его.\n"
        "• Нажми «⭐ Частое», чтобы увидеть свои шаблоны.\n"
        "• Нажми на товар в списке (✅), чтобы удалить его.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['list'])
@restricted
def handle_list_command(message):
    show_list(message)

@bot.message_handler(commands=['clear'])
@restricted
def handle_clear_command(message):
    storage.clear_list(message.from_user.id)
    bot.send_message(message.chat.id, "Список полностью очищен! 🧹")

@bot.message_handler(commands=['debug_logs'])
@restricted
def handle_debug_logs(message):
    # Только для главного администратора (вас)
    if message.from_user.id != 367218525:
        bot.send_message(message.chat.id, "У вас нет прав для просмотра системных логов. 🛡️")
        return
        
    frequent = storage.get_frequent_items(message.from_user.id, limit=20)
    items = storage.get_items(message.from_user.id)
    
    log_msg = f"🔍 **Системная сводка:**\n\n"
    log_msg += f"👤 Ваш ID: `{message.from_user.id}`\n"
    log_msg += f"📦 Товаров в списке: {len(items)}\n"
    log_msg += f"⭐ Всего в истории (топ): {', '.join(frequent) if frequent else 'пусто'}\n"
    
    bot.send_message(message.chat.id, log_msg, parse_mode="Markdown")

@bot.message_handler(content_types=['voice'])
@restricted
def handle_voice(message):
    try:
        msg = bot.send_message(message.chat.id, "🔊 Распознаю голос...")
        
        # Скачиваем файл
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open("voice.ogg", "wb") as f:
            f.write(downloaded_file)
            
        # Конвертируем ogg в wav (требуется ffmpeg)
        # На Render нужно добавить ffmpeg в Build Step
        audio = AudioSegment.from_file("voice.ogg", format="ogg")
        audio.export("voice.wav", format="wav")
        
        # Распознаем
        r = sr.Recognizer()
        with sr.AudioFile("voice.wav") as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="ru-RU")
            
        bot.delete_message(message.chat.id, msg.message_id)
        
        # Обрабатываем текст через AI
        if text:
            res = ai_provider.parse_items(text)
            
            # Поддержка нового формата (словарь с советом или просто список)
            if isinstance(res, dict):
                items_data = res.get('items', [])
                recipe_advice = res.get('recipe_advice')
            else:
                items_data = res
                recipe_advice = None
                
            added_text = []
            for item in items_data:
                name = item.get('name', 'Неизвестно')
                cat = item.get('category', '📦 Другое')
                if storage.add_item(name, cat, message.from_user.id):
                    added_text.append(f"• {name} ({cat})")
            
            if added_text:
                res_msg = "✅ **Добавлено из голоса:**\n" + "\n".join(added_text)
                if recipe_advice:
                    res_msg += f"\n\n💡 {recipe_advice}"
                bot.send_message(message.chat.id, res_msg, parse_mode="Markdown")
                show_list(message)
            elif recipe_advice:
                bot.send_message(message.chat.id, f"💡 {recipe_advice}\n\n⚠️ Продукты не распознаны автоматически.", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Голос распознан, но продуктов в нем не найдено. 🤔")
            
    except Exception as e:
        bot.send_message(message.chat.id, "❌ Не удалось распознать голос. Попробуйте четче или проверьте связь.")
        print(f"Voice error: {e}")
    finally:
        # Чистим временные файлы
        for f in ["voice.ogg", "voice.wav"]:
            if os.path.exists(f): 
                try: os.remove(f)
                except: pass

@bot.message_handler(func=lambda message: True)
@restricted
def handle_message(message):
    if message.text == "📝 Показать список":
        show_list(message)
    elif message.text == "❌ Очистить всё":
        storage.clear_list(message.from_user.id)
        bot.send_message(message.chat.id, "Список полностью очищен! 🧹")
    elif message.text == "⭐ Частое":
        frequent = storage.get_frequent_items(message.from_user.id)
        if not frequent:
            bot.send_message(message.chat.id, "Ваш каталог пока пуст. Добавьте что-нибудь!")
            return
            
        markup = types.InlineKeyboardMarkup(row_width=2)
        btns = [types.InlineKeyboardButton(item, callback_data=f"add_{item}") for item in frequent]
        markup.add(*btns)
        bot.send_message(message.chat.id, "Часто добавляемые товары:", reply_markup=markup)
    else:
        # Обработка сообщения через Gemini AI
        msg_wait = bot.send_message(message.chat.id, "🤖 Думаю...")
        res = ai_provider.parse_items(message.text)
        bot.delete_message(message.chat.id, msg_wait.message_id)
        
        # Поддержка нового формата (словарь с советом или просто список)
        if isinstance(res, dict):
            items_data = res.get('items', [])
            recipe_advice = res.get('recipe_advice')
        else:
            items_data = res
            recipe_advice = None
            
        added_text = []
        for item in items_data:
            name = item.get('name', 'Неизвестно')
            cat = item.get('category', '📦 Другое')
            if storage.add_item(name, cat, message.from_user.id):
                added_text.append(f"• *{name}* ({cat})")
        
        # ЛОГИКА ОТВЕТА
        if added_text:
            res_msg = "✅ **Добавлено в список:**\n" + "\n".join(added_text)
            if recipe_advice:
                res_msg += f"\n\n💡 {recipe_advice}"
            bot.send_message(message.chat.id, res_msg, parse_mode="Markdown")
            show_list(message)
        elif recipe_advice:
            # Случай, когда ИИ дал совет, но не добавил продукты (или они уже были)
            # Если список пуст, значит ИИ действительно проигнорировал продукты
            items_in_db = storage.get_items(message.from_user.id)
            if not items_in_db:
                res_msg = f"💡 {recipe_advice}\n\n⚠️ **Внимание:** ИИ не добавил продукты в список. Попробуйте попросить иначе, например: 'Составь список продуктов для оладий'."
            else:
                res_msg = f"💡 {recipe_advice}\n\n(Все нужные продукты уже есть в вашем списке! ✅)"
            bot.send_message(message.chat.id, res_msg, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "Не нашел продуктов в сообщении. 🤔 Попробуйте написать по-другому.")

def show_list(message):
    items = storage.get_items(message.from_user.id)
    if not items:
        bot.send_message(message.chat.id, "Ваш список покупок пуст. 📭")
        return

    markup = types.InlineKeyboardMarkup()
    
    current_category = None
    for index, item_data in enumerate(items):
        item_name = item_data['name']
        item_category = item_data['category']
        
        # Добавляем заголовок категории, если она изменилась
        if item_category != current_category:
            current_category = item_category
            # Используем фиктивную кнопку как заголовок (не нажимается)
            header_button = types.InlineKeyboardButton(
                text=f"--- {current_category} ---", 
                callback_data="ignore"
            )
            markup.add(header_button)
            
        callback_button = types.InlineKeyboardButton(
            text=f"✅ {item_name}", 
            callback_data=f"remove_{index}"
        )
        markup.add(callback_button)
    
    bot.send_message(message.chat.id, "Ваш список (нажми на ✅, чтобы вычеркнуть):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'ignore')
def callback_ignore(call):
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('remove_') or call.data.startswith('add_'))
@restricted
def callback_inline(call):
    if call.data.startswith('remove_'):
        index = int(call.data.split('_')[1])
        removed_item = storage.remove_item(index, call.from_user.id)
        
        if removed_item:
            bot.answer_callback_query(call.id, f"Куплено: {removed_item}")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            # Чтобы show_list сработал корректно, подменим отправителя
            call.message.from_user = call.from_user
            show_list(call.message)
            
    elif call.data.startswith('add_'):
        item = call.data.replace('add_', '')
        # Для быстрых кнопок используем AI для определения категории
        items_data = ai_provider.parse_items(item)
        if items_data:
            # Обработка нового формата AI
            if isinstance(items_data, dict):
                actual_items = items_data.get('items', [])
            else:
                actual_items = items_data
                
            if actual_items:
                name = actual_items[0].get('name', item)
                cat = actual_items[0].get('category', '📦 Другое')
                if storage.add_item(name, cat, call.from_user.id):
                    bot.answer_callback_query(call.id, f"Добавлено: {name}")
                    # Обновляем список, если он открыт
                    call.message.from_user = call.from_user
                    show_list(call.message)
                bot.answer_callback_query(call.id, f"Добавлено: {name}")
                bot.send_message(call.message.chat.id, f"✅ Добавлено: {name} ({cat})")
            else:
                bot.answer_callback_query(call.id, "Уже в списке!")
        else:
            bot.answer_callback_query(call.id, "Ошибка AI")

if __name__ == '__main__':
    # Запуск Flask в отдельном потоке
    threading.Thread(target=run_flask).start()
    
    # Принудительно удаляем вебхук перед запуском polling
    bot.remove_webhook()
    
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
