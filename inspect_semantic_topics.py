
import sqlite3
from memory import DB_PATH

connection = sqlite3.connect(DB_PATH)
connection.row_factory = sqlite3.Row

try:
    # 1. Inspect table structure
    columns = connection.execute("""
        PRAGMA table_info(vocabulary_items)
    """).fetchall()

    print("\n=== TABLE COLUMNS ===")

    for column in columns:
        print(column["name"], "-", column["type"])

    # 2. Count vocabulary items per topic
    topics = connection.execute("""
        SELECT
            topic,
            COUNT(*) AS vocabulary_count,
            SUM(
                CASE
                    WHEN embedding IS NOT NULL
                    AND embedding != ''
                    THEN 1 ELSE 0
                END
            ) AS embedded_count
        FROM vocabulary_items
        WHERE topic IS NOT NULL
          AND TRIM(topic) != ''
        GROUP BY topic
        ORDER BY topic
    """).fetchall()

    print("\n=== TOPIC STATISTICS ===")

    for topic in topics:
        print(
            f"{topic['topic']}: "
            f"{topic['vocabulary_count']} vocabulary items | "
            f"{topic['embedded_count']} embeddings"
        )

    # 3. Overall statistics
    totals = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN embedding IS NOT NULL
                    AND embedding != ''
                    THEN 1 ELSE 0
                END
            ) AS embedded,
            COUNT(DISTINCT topic) AS unique_topics
        FROM vocabulary_items
    """).fetchone()

    print("\n=== OVERALL STATISTICS ===")
    print("Total vocabulary:", totals["total"])
    print("Embedded vocabulary:", totals["embedded"])
    print("Unique topics:", totals["unique_topics"])

    # 4. Items without topics
    missing = connection.execute("""
        SELECT COUNT(*)
        FROM vocabulary_items
        WHERE topic IS NULL OR TRIM(topic) = ''
    """).fetchone()[0]

    print("Items without topics:", missing)

finally:
    connection.close()
