import sqlite3
from memory import DB_PATH

connection = sqlite3.connect(DB_PATH)

connection.execute(
    "UPDATE mistakes SET next_review_at = datetime('now', '-1 minute') WHERE id = ?",
    (1,)
)

connection.commit()

result = connection.execute(
    "SELECT id, original_sentence, next_review_at FROM mistakes WHERE id = ?",
    (1,)
).fetchone()

print("Test review prepared:", result)

connection.close()