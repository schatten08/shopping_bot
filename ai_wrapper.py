import os
import json
import google.generativeai as genai

class AIProvider:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def parse_items(self, text):
        if not self.model:
            # Fallback if AI not configured
            return [{"name": i.strip().capitalize(), "category": "📦 Другое"} for i in text.split(',') if i.strip()]

        prompt = f"""
        Ты — эксперт-помощник по покупкам. 
        Твоя задача: проанализировать текст пользователя и составить список продуктов для добавления в корзину.
        
        ПРАВИЛА:
        1. Если пользователь просит "продукты на борщ" или другое блюдо, добавь все основные ингредиенты для него.
        2. Учитывай исключения (например, "кроме свеклы" — значит свеклу добавлять НЕЛЬЗЯ).
        3. Исправляй опечатки и пиши названия с заглавной буквы.
        4. Если в тексте нет названий продуктов, верни пустой список [].
        5. Для каждого товара определи категорию с иконкой:
           "🍎 Овощи и фрукты", "🥛 Молочное", "🥖 Бакалея", "🧼 Хозтовары", "🥩 Мясо и птица", "🐟 Рыба и морепродукты", "🧊 Заморозка", "📦 Другое".

        Верни ответ ТОЛЬКО в формате JSON (без лишнего текста):
        [
            {{"name": "Картофель", "category": "🍎 Овощи и фрукты"}},
            {{"name": "Говядина", "category": "🥩 Мясо и птица"}}
        ]

        Текст пользователя: "{text}"
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Очистка ответа от возможных Markdown-тегов
            text_response = response.text
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]
            
            return json.loads(text_response.strip())
        except Exception as e:
            print(f"AI Error: {e}")
            # Если AI упал, пробуем простое разделение по запятой только если там есть слова
            return [{"name": i.strip().capitalize(), "category": "📦 Другое"} for i in text.split(',') if len(i.strip()) > 3]

ai_provider = AIProvider()
