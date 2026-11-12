
from memory import (
    init_db,
    get_connection,
    search_semantic_vocabulary,
    EMBEDDING_MODEL,
)

init_db()

print("\n========== EMBEDDING STATUS ==========")

with get_connection() as connection:
    total = connection.execute("""
        SELECT COUNT(*) FROM vocabulary_items
    """).fetchone()[0]

    embedded = connection.execute("""
        SELECT COUNT(*)
        FROM vocabulary_items
        WHERE embedding IS NOT NULL
          AND embedding_model = ?
    """, (EMBEDDING_MODEL,)).fetchone()[0]

    missing = connection.execute("""
        SELECT id, term
        FROM vocabulary_items
        WHERE embedding IS NULL
           OR embedding_model IS NULL
    """).fetchall()

print("Total vocabulary:", total)
print("With valid model embeddings:", embedded)
print("Missing embeddings:", missing)

print("\n========== SEMANTIC SEARCH ==========")

query = "I faced many problems, but I managed to solve them."

print("Query:", query)

results = search_semantic_vocabulary(query, limit=10)

print("\nRetrieved expressions:")

for item in results:
    print(
        f"{item['term']} | "
        f"Similarity: {item['similarity']:.4f}"
    )

if not results:
    print("No vocabulary retrieved.")
