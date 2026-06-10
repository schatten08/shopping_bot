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
        Ты помощник по покупкам. Извлеки список продуктов из следующего сообщения пользователя.
        Для каждого продукта определи подходящую категорию с иконкой (например, "🍎 Овощи и фрукты", "🥛 Молочное", "🥖 Бакалея", "🧼 Хозтовары", "🥩 Мясо и птица", "🐟 Рыба и морепродукты", "📦 Другое").
        
        Верни ответ ТОЛЬКО в формате JSON списка объектов:
        [
            {{"name": "Название товара", "category": "Иконка Категория"}}
        ]
        
        Сообщение пользователя: "{text}"
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Извлекаем JSON из ответа (иногда модель добавляет ```json ... ```)
            content = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except Exception as e:
            print(f"AI Error: {e}")
            # Fallback
            return [{"name": i.strip().capitalize(), "category": "📦 Другое"} for i in text.split(',') if i.strip()]

ai_provider = AIProvider()
