import sqlite3

from memory import DB_PATH, normalize_topic

connection = sqlite3.connect(DB_PATH)

rows = connection.execute("""
    SELECT DISTINCT topic
    FROM vocabulary_items
    WHERE topic IS NOT NULL
    ORDER BY topic
""").fetchall()

connection.close()

topics = [row[0] for row in rows]

print("Total unique topics:", len(topics))
print("\nVerification results:")

for topic in topics:
    normalized = normalize_topic(topic)

    status = "OK" if normalized == topic else "NEEDS REVIEW"

    print(f"{status}: {topic}")

print("\nVerification completed.")