import sqlite3

# 1. Connect
conn = sqlite3.connect('assets.db')
cursor = conn.cursor()

# 2. Ask the database: "What tables do you have?"
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall() if row[0] != 'sqlite_sequence']
print(f"🔎 Found these tables: {tables}")

# 3. Clean the paths in EVERY table found
for table_name in tables:
    try:
        # This strips 'static/uploads/' from the file_path column
        cursor.execute(f"UPDATE {table_name} SET file_path = REPLACE(file_path, 'static/uploads/', '')")
        conn.commit()
        print(f"✅ Fixed paths in table: {table_name}")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Skipping {table_name}: {e} (Probably doesn't have a file_path column)")

conn.close()
print("✨ All done! Your images should now point to the correct filenames.")