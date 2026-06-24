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

        # Промпт переработан: разделяем "просто покупку" от "рецепта"
        prompt = f"""
        Ты — робот-составитель списков покупок.
        
        ТВОЯ ЛОГИКА:
        1. Если в запросе есть слово "РЕЦЕПТ", "СОСТАВ" или явная просьба найти ингредиенты для блюда:
           - Найди основные ингредиенты и добавь их в массив "items".
           - В "recipe_advice" напиши краткий совет по приготовлению и ссылку на Google.
        
        2. Если слова "рецепт/состав" НЕТ (например, "творожок клубничный", "пицца", "яблоки"):
           - Просто добавь указанный текст как товар в массив "items". 
           - Не выдумывай ингредиенты. Даже если написано "Пицца", просто добавь "Пицца" в категорию "Ready Meals".
           - В "recipe_advice" верни null.

        ОТВЕТЬ В СТРОГОМ JSON:
        {{
            "items": [
                {{"name": "Название", "category": "Категория с иконкой"}}
            ],
            "recipe_advice": "текст совета или null"
        }}

        Запрос пользователя: "{text}"
        """
        
        try:
            # Добавляем повторные попытки при 503 ошибке
            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=prompt,
                        config={'response_mime_type': 'application/json'}
                    )
                    
                    print(f"DEBUG AI Response: {response.text}") # Видно в логах
                    data = json.loads(response.text.strip())
                    
                    # Гарантируем наличие ключа items
                    if "items" not in data:
                        data["items"] = []
                    return data
                except Exception as e:
                    last_error = e
                    if "503" in str(e) or "Service Unavailable" in str(e):
                        print(f"AI 503 Attempt {attempt + 1} failed, retrying in 2s...")
                        import time
                        time.sleep(2)
                        continue
                    raise e
            
            print(f"AI ERROR after {max_retries} attempts: {last_error}")
            return {"items": [], "recipe_advice": "Gemini сейчас перегружен (503). Попробуйте позже или добавьте товар вручную."}
            
        except Exception as e:
            print(f"AI ERROR: {e}")
            return {"items": [], "recipe_advice": "Произошла ошибка при связи с Gemini."}

ai_provider = AIProvider()
