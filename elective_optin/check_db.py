import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Show all tables
print("=== ALL TABLES IN DATABASE ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f" - {table[0]}")

print("\n=== SAMPLE DATA FROM electives_course ===")
# Example: read your table
try:
    cursor.execute("SELECT * FROM electives_course LIMIT 5;")
    rows = cursor.fetchall()

    for row in rows:
        print(row)
except sqlite3.OperationalError:
    print("Table electives_course not found or empty.")

conn.close()
