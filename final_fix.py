import sqlite3
import os

# List all .db files in your folder
db_files = [f for f in os.listdir('.') if f.endswith('.db')]
print(f"🔎 Found {len(db_files)} database files: {db_files}")

for db_file in db_files:
    print(f"\n--- Checking {db_file} ---")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Find tables in THIS file
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"   Found tables: {tables}")

    for table in tables:
        if table != 'sqlite_sequence':
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN ai_tags TEXT;")
                conn.commit()
                print(f"   ✅ SUCCESS: Added 'ai_tags' to '{table}' in '{db_file}'")
            except sqlite3.OperationalError as e:
                print(f"   💡 INFO: {e}")
    conn.close()

print("\n🚀 All database files processed!")