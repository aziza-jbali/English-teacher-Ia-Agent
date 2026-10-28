import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "learner_memory.db"
connection = sqlite3.connect(db_path)

print("=== TUTOR STATE ===")
tables = connection.execute(
    "SELECT name FROM sqlite_master WHERE type = ?",
    ("table",)
).fetchall()
print(tables)

if any(table[0] == "tutor_state" for table in tables):
    print(connection.execute("SELECT * FROM tutor_state").fetchall())

print("\n=== SAVED MISTAKE REVIEWS ===")
rows = connection.execute("""
    SELECT id, original_sentence, review_count,
           correct_count, wrong_count, next_review_at
    FROM mistakes
    ORDER BY id
""").fetchall()

for row in rows:
    print(row)

connection.close()