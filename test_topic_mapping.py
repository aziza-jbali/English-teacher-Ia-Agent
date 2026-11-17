
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
connection = sqlite3.connect(DB_PATH)

rows = connection.execute("""
    SELECT topic, COUNT(*)
    FROM vocabulary_items
    GROUP BY topic
""").fetchall()

connection.close()

print("\nACTUAL VOCABULARY COUNTS AFTER NORMALIZATION\n")

counts = Counter()

for topic, number in rows:
    normalized = normalize_topic(topic)
    counts[normalized] += number

for topic, number in counts.most_common():
    print(f"{topic}: {number}")