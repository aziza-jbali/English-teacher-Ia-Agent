
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "learner_memory.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n========== DATABASE TABLES ==========")

cursor.execute("""
    SELECT name FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

for row in cursor.fetchall():
    print("-", row["name"])

print("\n========== VOCABULARY SUMMARY ==========")

cursor.execute("PRAGMA table_info(vocabulary_items)")
columns = [row["name"] for row in cursor.fetchall()]
print("Columns:", columns)

cursor.execute("""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN embedding IS NOT NULL
                  AND embedding != '' THEN 1 ELSE 0 END) AS embedded,
        SUM(CASE WHEN embedding_model = 'gemini-embedding-001'
                  THEN 1 ELSE 0 END) AS gemini_embeddings
    FROM vocabulary_items
""")

print(dict(cursor.fetchone()))

print("\n========== SAVED VOCABULARY ==========")

cursor.execute("""
    SELECT id, term, item_type, meaning_en,
           occurrence_count, embedding_model
    FROM vocabulary_items
    ORDER BY id DESC
    LIMIT 20
""")

for row in cursor.fetchall():
    print(dict(row))

print("\n========== SEMANTIC RELATIONSHIPS ==========")

cursor.execute("""
    SELECT COUNT(*) AS total FROM semantic_relationships
""")
print("Total relationships:", cursor.fetchone()["total"])

cursor.execute("""
    SELECT * FROM semantic_relationships
    ORDER BY id DESC
    LIMIT 15
""")

for row in cursor.fetchall():
    print(dict(row))

conn.close()

print("\n========== INSPECTION COMPLETE ==========")
