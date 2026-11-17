
from memory import get_connection

relationship_id = 167

with get_connection() as connection:
    connection.execute("""
        DELETE FROM semantic_relationships
        WHERE id = ?
    """, (relationship_id,))

    print("Deleted relationship:", relationship_id)
