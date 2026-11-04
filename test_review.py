
import sqlite3
import json
import math
import os

DB_PATH = os.path.abspath("learner_memory.db")

print("Database path:", DB_PATH)
print("Database exists:", os.path.exists(DB_PATH))

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Verify the database contains the expected expression
cursor.execute("""
    SELECT id, term, embedding IS NOT NULL
    FROM vocabulary_items
    WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
""", ("overcome obstacles",))

print("Existing expression:", cursor.fetchall())


def get_embedding(term):
    cursor.execute("""
        SELECT embedding
        FROM vocabulary_items
        WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
        AND embedding IS NOT NULL
        LIMIT 1
    """, (term,))

    result = cursor.fetchone()

    if result is None:
        return None

    return json.loads(result[0])


def cosine_similarity(vec1, vec2):
    if len(vec1) != len(vec2):
        raise ValueError("Embedding dimensions do not match")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0

    return dot_product / (norm1 * norm2)


def compare_terms(term1, term2):
    emb1 = get_embedding(term1)
    emb2 = get_embedding(term2)

    if emb1 is None:
        print(f"Embedding not found: {term1}")

    if emb2 is None:
        print(f"Embedding not found: {term2}")

    if emb1 is None or emb2 is None:
        return

    similarity = cosine_similarity(emb1, emb2)

    print("\nExpression 1:", term1)
    print("Expression 2:", term2)
    print("Dimensions:", len(emb1), len(emb2))
    print(f"Similarity: {similarity:.4f}")


# compare_terms(
#     "overcome obstacles",
#     "deal with difficulties"
# )
# compare_terms(
#     "overcome obstacles",
#     "overcome"
# )
compare_terms(
    "deal with difficulties",
    "overcome obstacles"
)
conn.close()
