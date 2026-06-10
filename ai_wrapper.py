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
        Проанализируй запрос пользователя и составь структурированный список продуктов.
        
        ТВОИ ВОЗМОЖНОСТИ:
        1. Распознавание рецептов: если просят "продукты на суп", предложи полный список ингредиентов.
        2. Дополнение: если говорят "есть курица, что докупить для ужина", предложи недостающие товары (например, овощи, соус, гарнир).
        3. Пропорции: если указано количество людей (на 4 человека), адаптируй список (в скобках пиши примерный объем).
        4. Очистка мусора: игнорируй вводные слова, вежливость и случайные фразы.
        5. Категории: обязательно подбери подходящую категорию с иконкой для каждого товара.
        6. Исключения: строго соблюдай условия "кроме", "без", "не добавляй".

        Верни ответ ТОЛЬКО в формате JSON:
        [
            {{"name": "Название (кол-во)", "category": "🍎 Категория"}}
        ]

        Текст запроса: "{text}"
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            # Новый SDK возвращает ответ в response.text
            text_response = response.text
            
            # Очистка JSON от markdown
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]
            
            items = json.loads(text_response.strip())
            # Проверка, что это список и там есть продукты
            if isinstance(items, list) and len(items) > 0:
                return items
            return []

        except Exception as e:
            print(f"AI Error details: {e}")
            return []

ai_provider = AIProvider()

ai_provider = AIProvider()
