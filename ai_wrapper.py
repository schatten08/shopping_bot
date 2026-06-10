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
            print("AI Provider: No API key configured.")
            return []

        prompt = f"""
        Ты — интеллектуальный ассистент по покупкам. 
        Проанализируй запрос пользователя.
        
        ТВОИ ВОЗМОЖНОСТИ:
        1. Распознавание рецептов: если просят "продукты на суп", предложи полный список необходимых ингредиентов. Ты ОБЯЗАН заполнить ими массив "items".
        2. ГЛАВНОЕ ПРАВИЛО: Если в запросе есть намек на приготовление еды, поле "items" НЕ МОЖЕТ быть пустым. В "items" должны быть основные ингредиенты для этого блюда.
        3. Категории: подбери подходящую категорию с иконкой.

        СТРУКТУРА ОТВЕТА (JSON):
        {{
            "items": [
                {{"name": "Продукт", "category": "🍎 Категория"}}
            ],
            "recipe_advice": "Вежливый совет и ссылка (https://www.google.com/search?q=рецепт+...)"
        }}

        Текст запроса: "{text}"
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            
            text_response = response.text
            data = json.loads(text_response.strip())
            
            # Если ИИ вернул пустой список предметов при наличии рецепта - это ошибка логики ИИ
            # Исправляем это на лету, если возможно, или просто возвращаем данные
            return data
        except Exception as e:
            print(f"AI Error details: {e}")
            # Пробуем без JSON-мода если не получилось
            try:
                response = self.client.models.generate_content(model=self.model_id, contents=prompt)
                text_response = response.text
                if "```json" in text_response:
                    text_response = text_response.split("```json")[1].split("```")[0]
                return json.loads(text_response.strip())
            except:
                return {"items": [], "recipe_advice": None}

ai_provider = AIProvider()

ai_provider = AIProvider()
