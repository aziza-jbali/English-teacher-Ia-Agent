
from memory import get_connection

vocabulary_id = 118

with get_connection() as connection:
    cursor = connection.execute("""
        SELECT *
        FROM semantic_relationships
        WHERE item_id = ? OR related_item_id = ?
    """, (vocabulary_id, vocabulary_id))

    columns = [description[0] for description in cursor.description]
    relationships = cursor.fetchall()

print("Columns:", columns)
print("Number of relationships:", len(relationships))

for relationship in relationships:
    print(dict(zip(columns, relationship)))
