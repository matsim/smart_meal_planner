import sqlite3, os

db_path = 'sql_app.db'
conn = sqlite3.connect(db_path, timeout=5)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('All tables:', tables)
for t in ['foods', 'food_portions', 'recipes', 'recipe_ingredients', 'alembic_version']:
    if t in tables:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'  {t}: {cur.fetchone()[0]} rows')
    else:
        print(f'  {t}: MISSING')

# Check food_portions columns
if 'foods' in tables:
    cur.execute("PRAGMA table_info(foods)")
    cols = [r[1] for r in cur.fetchall()]
    print('foods columns:', cols)
if 'recipe_ingredients' in tables:
    cur.execute("PRAGMA table_info(recipe_ingredients)")
    cols = [r[1] for r in cur.fetchall()]
    print('recipe_ingredients columns:', cols)

conn.close()
