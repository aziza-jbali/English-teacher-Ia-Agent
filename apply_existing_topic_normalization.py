
import sqlite3

from memory import get_connection, normalize_topic, DB_PATH


backup_path = str(DB_PATH) + ".before_topic_normalization.bak"


with get_connection() as connection:

    # 1. Create a database backup
    backup = sqlite3.connect(backup_path)

    try:
        connection.backup(backup)
    finally:
        backup.close()

    # 2. Read existing topics
    rows = connection.execute("""
        SELECT id, topic
        FROM vocabulary_items
        WHERE topic IS NOT NULL
    """).fetchall()

    updated = 0

    # 3. Normalize existing topics
    for item_id, old_topic in rows:

        new_topic = normalize_topic(old_topic)

        if new_topic != old_topic:

            connection.execute("""
                UPDATE vocabulary_items
                SET topic = ?
                WHERE id = ?
            """, (new_topic, item_id))

            updated += 1

# 4. Display results
print("Database backup:", backup_path)
print("Total records:", len(rows))
print("Updated records:", updated)
