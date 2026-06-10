import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

class AIProvider:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            # Используем новый SDK google-genai
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = 'gemini-flash-latest'
        else:
            self.client = None

    def parse_items(self, text):
        if not self.client:
            return {"items": [], "recipe_advice": None}

        prompt = f"""
        Ты — ассистент по покупкам. Твоя главная цель: превращать запросы в список продуктов.
        
        ПРАВИЛА:
        1. Если пользователь пишет категорию или блюдо (например: "продукты на оладьи"), ты ДОЛЖЕН найти базовый рецепт и добавить ВСЕ ингредиенты в список "items". 
           Например, для оладий: ["Мука", "Кефир или Молоко", "Яйца", "Сахар", "Растительное масло"].
        2. Если в запросе есть "добавь продукты на...", это команда ДОБАВИТЬ их в список, а не просто дать совет.
        3. Поле "recipe_advice" используется ТОЛЬКО для краткого совета.
        4. Поле "items" НИКОГДА не должно быть пустым, если в запросе упоминается еда.

        ОТВЕТЬ ТОЛЬКО В JSON:
        {{
            "items": [
                {{"name": "Название", "category": "🛒 Категория"}}
            ],
            "recipe_advice": "Короткий совет и ссылка: https://www.google.com/search?q=рецепт+..."
        }}

        Запрос: "{text}"
        """
        
        try:
            # Используем JSON Mode
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                }
            )
            
            data = json.loads(response.text.strip())
            return data
        except Exception as e:
            print(f"AI Error: {e}")
            return {"items": [], "recipe_advice": "Извините, произошла ошибка при разборе продуктов."}

ai_provider = AIProvider()
