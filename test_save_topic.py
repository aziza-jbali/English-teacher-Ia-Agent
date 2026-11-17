from memory import save_vocabulary, get_connection

vocabulary_id = save_vocabulary(
    term="topic normalization test",
    item_type="word",
    meaning_ar="اختبار تطبيع المواضيع",
    topic="Personal Growth"
)

print("Saved ID:", vocabulary_id)

with get_connection() as connection:
    row = connection.execute("""
        SELECT id, term, topic
        FROM vocabulary_items
        WHERE id = ?
    """, (vocabulary_id,)).fetchone()

    print("Database result:", row)

    connection.execute("""
        DELETE FROM vocabulary_items
        WHERE id = ?
    """, (vocabulary_id,))

print("Test vocabulary deleted.")