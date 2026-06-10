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

        # Промпт стал максимально жестким в плане обязательств по наполнению "items"
        prompt = f"""
        Ты — робот-составитель списков покупок. Твой ответ ВСЕГДА должен содержать список продуктов.
        
        ТВОЯ ЗАДАЧА:
        1. Если запрос "продукты на [БЛЮДО]", ты ОБЯЗАН найти классический рецепт и выписать все основные ингредиенты в "items".
           Пример запроса "продукты на оладьи":
           "items": [
               {{"name": "Кефир", "category": "🥛 Молочные продукты"}},
               {{"name": "Мука", "category": "🥖 Бакалея"}},
               {{"name": "Яйца", "category": "🥚 Прочее"}},
               {{"name": "Сахар", "category": "🥖 Бакалея"}},
               {{"name": "Растительное масло", "category": "🧴 Бакалея"}}
           ]
        2. Если в запросе уже есть список продуктов, просто разложи их по категориям.
        3. "recipe_advice": напиши короткий совет (1-2 предложения) и дай ссылку на Google.
        
        НИКОГДА не возвращай пустой список "items", если в запросе упоминается еда!

        ОТВЕТЬ В СТРОГОМ JSON:
        {{
            "items": [
                {{"name": "Название", "category": "Категория с иконкой"}}
            ],
            "recipe_advice": "Твой совет и ссылка"
        }}

        Запрос пользователя: "{text}"
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            
            print(f"DEBUG AI Response: {response.text}") # Видно в логах Render
            data = json.loads(response.text.strip())
            
            # Гарантируем наличие ключа items
            if "items" not in data:
                data["items"] = []
            return data
        except Exception as e:
            print(f"AI ERROR: {e}")
            return {"items": [], "recipe_advice": "Произошла ошибка при связи с Gemini."}

ai_provider = AIProvider()
