from memory import get_connection

vocabulary_id = 118

with get_connection() as connection:
    item = connection.execute("""
        SELECT id, term
        FROM vocabulary_items
        WHERE id = ?
    """, (vocabulary_id,)).fetchone()

    relationships = connection.execute("""
        SELECT COUNT(*)
        FROM semantic_relationships
        WHERE item_id = ? OR related_item_id = ?
    """, (vocabulary_id, vocabulary_id)).fetchone()[0]

print("Vocabulary item:", item)
print("Remaining semantic relationships:", relationships)