
import sqlite3
from collections import Counter
from memory import normalize_topic, DB_PATH

connection = sqlite3.connect(DB_PATH)

topics = connection.execute("""
    SELECT DISTINCT topic
    FROM vocabulary_items
    ORDER BY topic
""").fetchall()

connection.close()

results = {}

for (topic,) in topics:
    normalized = normalize_topic(topic)
    results[topic] = normalized

print("\nORIGINAL TOPICS --> NORMALIZED TOPICS\n")

for original, normalized in results.items():
    print(f"{original} --> {normalized}")

print("\nNORMALIZED TOPIC COUNTS\n")

counts = Counter(results.values())

for topic, count in counts.items():
    print(f"{topic}: {count}")

print(f"\nTotal original topics: {len(results)}")
print(f"Total normalized topics: {len(counts)}")
