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
        1. Распознавание рецептов: если просят "продукты на суп", предложи полный список необходимых ингредиентов в массиве "items".
        2. Дополнение: если говорят "есть курица, что докупить для ужина", предложи недостающие товары в "items".
        3. Подбор рецепта: если пользователь пишет список имеющихся продуктов, предложи ОДНО конкретное блюдо и напиши в "items" только те продукты, которых обычно не хватает (масло, специи, основные овощи).
        4. ВСЕГДА: Любой продукт, который должен попасть в список покупок, ОБЯЗАТЕЛЬНО должен быть в массиве "items". Поле "recipe_advice" — только для текста совета и ссылок.
        5. Пропорции: если указано количество людей, адаптируй список (в скобках пиши объем).
        6. Категории: подбери подходящую категорию с иконкой.

        Верни ответ ТОЛЬКО в формате JSON:
        {{
            "items": [
                {{"name": "Название (кол-во)", "category": "🍎 Категория"}}
            ],
            "recipe_advice": "Краткий кулинарный совет и ссылка на Google (https://www.google.com/search?q=рецепт+...)"
        }}

        Текст запроса: "{text}"
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            
            text_response = response.text
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]
            
            data = json.loads(text_response.strip())
            
            # Универсальный возврат для поддержки старого кода
            if isinstance(data, list):
                return data
            return data
        except Exception as e:
            print(f"AI Error details: {e}")
            return []

ai_provider = AIProvider()

ai_provider = AIProvider()
