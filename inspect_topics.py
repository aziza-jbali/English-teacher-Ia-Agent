
import sqlite3

connection = sqlite3.connect("learner_memory.db")
cursor = connection.cursor()

# 1. Total vocabulary
total = cursor.execute(
    "SELECT COUNT(*) FROM vocabulary_items"
).fetchone()[0]

print(f"\nTOTAL VOCABULARY: {total}")

# 2. Topics and counts
print("\nTOPICS AND COUNTS:")

topics = cursor.execute("""
    SELECT
        COALESCE(NULLIF(TRIM(topic), ''), '[No topic]'),
        COUNT(*)
    FROM vocabulary_items
    GROUP BY 1
    ORDER BY 2 DESC
""").fetchall()

for topic, count in topics:
    print(f"{topic}: {count}")

# 3. All vocabulary items
print("\nVOCABULARY ITEMS:")

items = cursor.execute("""
    SELECT
        COALESCE(NULLIF(TRIM(topic), ''), '[No topic]'),
        term,
        item_type
    FROM vocabulary_items
    ORDER BY topic, term
""").fetchall()

for topic, term, item_type in items:
    print(f"Topic: {topic} | Term: {term} | Type: {item_type}")

connection.close()
