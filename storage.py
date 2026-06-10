import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

class ShoppingList:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if self.db_url:
            self._init_db()
        else:
            # Локальный режим, если нет DATABASE_URL
            self.file_path = 'data/shopping_list.json'
            self._ensure_data_dir()
            self.items = self._load_data_local()

    def _init_db(self):
        conn = psycopg2.connect(self.db_url)
        with conn.cursor() as cur:
            # 1. Сначала просто создаем таблицы, если их нет
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopping_items (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT DEFAULT 0,
                    name TEXT NOT NULL,
                    category TEXT DEFAULT '📦 Другое'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchase_history (
                    user_id BIGINT DEFAULT 0,
                    name TEXT NOT NULL,
                    category TEXT,
                    count INTEGER DEFAULT 1
                )
            """)
            
            # 2. Аккуратно добавляем колонки и чистим дубликаты для уникальности
            cur.execute("""
                DO $$
                BEGIN
                    -- Добавляем колонку user_id, если её не было
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='shopping_items' AND column_name='user_id') THEN
                        ALTER TABLE shopping_items ADD COLUMN user_id BIGINT DEFAULT 0;
                    END IF;

                    -- Чистим дубликаты перед созданием уникального ключа (оставляем только один ID для каждой пары user/name)
                    DELETE FROM shopping_items a USING shopping_items b 
                    WHERE a.id < b.id AND a.name = b.name AND a.user_id = b.user_id;

                    -- Удаляем старые ключи и создаем правильный составной ключ
                    ALTER TABLE shopping_items DROP CONSTRAINT IF EXISTS shopping_items_name_key;
                    ALTER TABLE shopping_items DROP CONSTRAINT IF EXISTS shopping_items_user_name_key;
                    ALTER TABLE shopping_items ADD CONSTRAINT shopping_items_user_name_key UNIQUE (user_id, name);

                    -- То же самое для истории
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='purchase_history' AND column_name='user_id') THEN
                        ALTER TABLE purchase_history ADD COLUMN user_id BIGINT DEFAULT 0;
                    END IF;
                    
                    -- У истории первичный ключ должен быть составным (user_id + name)
                    ALTER TABLE purchase_history DROP CONSTRAINT IF EXISTS purchase_history_pkey;
                    ALTER TABLE purchase_history ADD PRIMARY KEY (user_id, name);
                EXCEPTION WHEN OTHERS THEN
                    -- Если что-то пошло не так (например, ключ уже есть), просто идем дальше
                    RAISE NOTICE 'Migration message: %', SQLERRM;
                END $$;
            """)
        conn.commit()
        conn.close()

    def _update_history(self, item_name, user_id=0):
        if not self.db_url: return
        conn = psycopg2.connect(self.db_url)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO purchase_history (name, user_id, count) 
                VALUES (%s, %s, 1) 
                ON CONFLICT (name, user_id) DO UPDATE SET count = purchase_history.count + 1
            """, (item_name.strip(), user_id))
        conn.commit()
        conn.close()

    def get_frequent_items(self, user_id=0, limit=12):
        if not self.db_url: return []
        conn = psycopg2.connect(self.db_url)
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM purchase_history WHERE user_id = %s ORDER BY count DESC LIMIT %s", (user_id, limit))
            rows = cur.fetchall()
        conn.close()
        return [row[0] for row in rows]

    def get_items(self, user_id=0):
        if not self.db_url:
            return self._items_local
        
        conn = psycopg2.connect(self.db_url)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, category FROM shopping_items WHERE user_id = %s ORDER BY category, name", (user_id,))
            rows = cur.fetchall()
        conn.close()
        return rows

    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def _load_data_local(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def save_data_local(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self._items_local, f, ensure_ascii=False, indent=4)

    def add_item(self, item, category='📦 Другое', user_id=0):
        if self.db_url:
            try:
                # Обновляем историю при каждом добавлении
                self._update_history(item, user_id)
                
                conn = psycopg2.connect(self.db_url)
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO shopping_items (name, category, user_id) VALUES (%s, %s, %s) ON CONFLICT (name, user_id) DO NOTHING RETURNING id", 
                        (item, category, user_id)
                    )
                    result = cur.fetchone()
                conn.commit()
                conn.close()
                return result is not None
            except Exception as e:
                print(f"DB Error: {e}")
                return False
        else:
            if item not in self._items_local:
                self._items_local.append({"name": item, "category": category})
                self.save_data_local()
                return True
            return False

    def remove_item(self, index, user_id=0):
        items = self.get_items(user_id) # На этом этапе items - это список словарей
        if 0 <= index < len(items):
            item_name = items[index]['name']
            if self.db_url:
                conn = psycopg2.connect(self.db_url)
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM shopping_items WHERE name = %s AND user_id = %s", (item_name, user_id))
                conn.commit()
                conn.close()
                return item_name
            else:
                removed = self._items_local.pop(index)
                self.save_data_local()
                return removed['name']
        return None

    def clear_list(self, user_id=0):
        if self.db_url:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shopping_items WHERE user_id = %s", (user_id,))
            conn.commit()
            conn.close()
        else:
            self._items_local = []
            self.save_data_local()
