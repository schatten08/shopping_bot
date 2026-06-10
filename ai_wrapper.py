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
        Ты — эксперт-помощник по покупкам. 
        Проанализируй текст и составь список продуктов.
        
        ПРАВИЛА:
        1. Если просят "продукты на борщ/салат" и т.д., добавь основные ингредиенты.
        2. Учитывай исключения ("кроме Х").
        3. Исправляй опечатки.
        4. Обязательно определи категорию с иконкой.
        
        Верни ответ ТОЛЬКО в формате JSON:
        [
            {{"name": "Товар", "category": "🍎 Категория"}}
        ]

        Текст: "{text}"
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
