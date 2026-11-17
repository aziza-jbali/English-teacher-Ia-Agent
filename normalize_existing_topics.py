
from memory import get_connection, normalize_topic

with get_connection() as connection:
    rows = connection.execute("""
        SELECT id, term, topic
        FROM vocabulary_items
        WHERE topic IS NOT NULL
        ORDER BY id
    """).fetchall()

changes = []

for item_id, term, old_topic in rows:
    new_topic = normalize_topic(old_topic)

    if new_topic != old_topic:
        changes.append((item_id, term, old_topic, new_topic))

print("Total vocabulary records:", len(rows))
print("Topics requiring normalization:", len(changes))

for item_id, term, old_topic, new_topic in changes:
    print(f"\nID: {item_id}")
    print(f"Term: {term}")
    print(f"Old topic: {old_topic}")
    print(f"New topic: {new_topic}")
