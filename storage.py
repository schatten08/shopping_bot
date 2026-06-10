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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopping_items (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT DEFAULT '📦 Другое'
                )
            """)
            # Таблица для истории (каталога)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchase_history (
                    name TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 1
                )
            """)
            # Добавляем колонку category, если её нет (для существующих БД)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='shopping_items' AND column_name='category') THEN
                        ALTER TABLE shopping_items ADD COLUMN category TEXT DEFAULT '📦 Другое';
                    END IF;
                END $$;
            """)
        conn.commit()
        conn.close()

    def _update_history(self, item_name):
        if not self.db_url: return
        conn = psycopg2.connect(self.db_url)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO purchase_history (name, count) 
                VALUES (%s, 1) 
                ON CONFLICT (name) DO UPDATE SET count = purchase_history.count + 1
            """, (item_name.strip(),))
        conn.commit()
        conn.close()

    def get_frequent_items(self, limit=12):
        if not self.db_url: return []
        conn = psycopg2.connect(self.db_url)
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM purchase_history ORDER BY count DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
        conn.close()
        return [row[0] for row in rows]

    @property
    def items(self):
        if not self.db_url:
            return self._items_local
        
        conn = psycopg2.connect(self.db_url)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, category FROM shopping_items ORDER BY category, name")
            rows = cur.fetchall()
        conn.close()
        return rows

    @items.setter
    def items(self, value):
        # Только для локального режима
        self._items_local = value

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

    def add_item(self, item, category='📦 Другое'):
        if self.db_url:
            try:
                # Обновляем историю при каждом добавлении
                self._update_history(item)
                
                conn = psycopg2.connect(self.db_url)
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO shopping_items (name, category) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id", 
                        (item, category)
                    )
                    result = cur.fetchone()
                conn.commit()
                conn.close()
                return result is not None
            except Exception as e:
                print(f"DB Error: {e}")
                return False
        else:
            if item not in self.items:
                self.items.append(item)
                self.save_data_local()
                return True
            return False

    def remove_item(self, index):
        items = self.items # На этом этапе items - это список словарей
        if 0 <= index < len(items):
            item_name = items[index]['name']
            if self.db_url:
                conn = psycopg2.connect(self.db_url)
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM shopping_items WHERE name = %s", (item_name,))
                conn.commit()
                conn.close()
                return item_name
            else:
                removed = self.items.pop(index)
                self.save_data_local()
                return removed
        return None

    def clear_list(self):
        if self.db_url:
            conn = psycopg2.connect(self.db_url)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM shopping_items")
            conn.commit()
            conn.close()
        else:
            self.items = []
            self.save_data_local()
