
import sqlite3
import json
import math
from collections import defaultdict
from memory import DB_PATH


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ==================================================
# 1. LOAD DATA FROM DATABASE (READ ONLY)
# ==================================================

connection = sqlite3.connect(DB_PATH)
connection.row_factory = sqlite3.Row

try:
    rows = connection.execute("""
        SELECT topic, term, embedding, embedding_model
        FROM vocabulary_items
        WHERE topic IS NOT NULL
          AND TRIM(topic) != ''
          AND embedding IS NOT NULL
          AND embedding != ''
    """).fetchall()

    missing = connection.execute("""
        SELECT term
        FROM vocabulary_items
        WHERE topic IS NULL OR TRIM(topic) = ''
    """).fetchall()

finally:
    connection.close()


# ==================================================
# 2. GROUP EMBEDDINGS AND VOCABULARY BY TOPIC
# ==================================================

topic_vectors = defaultdict(list)
topic_terms = defaultdict(list)

models = set()
dimensions = set()
invalid = []

for row in rows:
    try:
        vector = json.loads(row["embedding"])

        if not isinstance(vector, list) or not vector:
            raise ValueError("Invalid embedding format")

        if not all(
            isinstance(x, (int, float)) and math.isfinite(x)
            for x in vector
        ):
            raise ValueError("Non-numeric or non-finite values")

        topic_vectors[row["topic"]].append(vector)
        topic_terms[row["topic"]].append(row["term"])

        dimensions.add(len(vector))

        if row["embedding_model"]:
            models.add(row["embedding_model"])

    except (ValueError, TypeError, json.JSONDecodeError) as error:
        invalid.append((row["term"], str(error)))


print("\n=== EMBEDDING VALIDATION ===")

print(
    "Valid vocabulary items:",
    sum(len(v) for v in topic_vectors.values())
)

print("Topics:", len(topic_vectors))
print("Dimensions:", dimensions)
print("Models:", models)
print("Invalid embeddings:", len(invalid))

if invalid:
    print("\nInvalid items:")

    for term, error in invalid:
        print(term, "-", error)

if invalid:
    raise ValueError("Invalid embeddings detected.")

if len(dimensions) != 1:
    raise ValueError("Inconsistent embedding dimensions.")

if len(models) != 1:
    raise ValueError("Inconsistent embedding models.")


# ==================================================
# 3. BUILD TOPIC-LEVEL SEMANTIC REPRESENTATIONS
# ==================================================

topic_representations = {}

for topic, vectors in topic_vectors.items():

    dimension = len(vectors[0])

    if not all(len(v) == dimension for v in vectors):
        raise ValueError(
            f"Inconsistent dimensions in topic: {topic}"
        )

    mean_vector = [
        sum(vector[i] for vector in vectors) / len(vectors)
        for i in range(dimension)
    ]

    topic_representations[topic] = mean_vector


print("\n=== TOPIC REPRESENTATIONS ===")

for topic, vector in topic_representations.items():

    print(
        f"{topic}: "
        f"{len(topic_vectors[topic])} items | "
        f"{len(vector)} dimensions"
    )


# ==================================================
# 4. CALCULATE COSINE SIMILARITY BETWEEN TOPICS
# ==================================================

similarities = []

topics = list(topic_representations.keys())

for i in range(len(topics)):

    for j in range(i + 1, len(topics)):

        topic_a = topics[i]
        topic_b = topics[j]

        score = cosine_similarity(
            topic_representations[topic_a],
            topic_representations[topic_b]
        )

        similarities.append(
            (topic_a, topic_b, score)
        )


similarities.sort(
    key=lambda x: x[2],
    reverse=True
)


# ==================================================
# 5. DISPLAY TOP 30 RELATED TOPIC PAIRS
# ==================================================

print("\n=== TOP 30 RELATED TOPIC PAIRS ===")

for topic_a, topic_b, score in similarities[:30]:

    print(
        f"{score:.4f} | "
        f"{topic_a} <-> {topic_b}"
    )


# ==================================================
# 6. INSPECT VOCABULARY BEHIND RELATED TOPICS
# ==================================================

print("\n=== DETAILED TOPIC RELATIONSHIPS ===")

for topic_a, topic_b, score in similarities[:30]:

    print("\n" + "=" * 70)

    print(f"Similarity: {score:.4f}")

    print(f"\nTOPIC A: {topic_a}")

    for term in topic_terms[topic_a]:
        print(" -", term)

    print(f"\nTOPIC B: {topic_b}")

    for term in topic_terms[topic_b]:
        print(" -", term)


# ==================================================
# 7. IDENTIFY IDENTICAL TOPIC REPRESENTATIONS
# ==================================================

print("\n=== IDENTICAL TOPIC REPRESENTATIONS ===")

identical_count = 0

for i in range(len(topics)):

    for j in range(i + 1, len(topics)):

        topic_a = topics[i]
        topic_b = topics[j]

        score = cosine_similarity(
            topic_representations[topic_a],
            topic_representations[topic_b]
        )

        if math.isclose(score, 1.0, abs_tol=1e-9):

            identical_count += 1

            print(
                f"{topic_a} <-> {topic_b} "
                f"| Similarity: {score:.4f}"
            )

if identical_count == 0:
    print("No identical topic representations found.")


# ==================================================
# 8. SHOW VOCABULARY ITEMS WITHOUT TOPICS
# ==================================================

print("\n=== ITEMS WITHOUT TOPICS ===")

for row in missing:
    print("-", row["term"])


# ==================================================
# 9. ANALYSIS SUMMARY
# ==================================================

print("\n=== ANALYSIS SUMMARY ===")

print(
    "Topic representations:",
    len(topic_representations)
)

print(
    "Compared topic pairs:",
    len(similarities)
)

print(
    "Items without topics:",
    len(missing)
)

print(
    "Identical topic pairs:",
    identical_count
)

print("\nAnalysis completed successfully.")
print("Database was not modified.")
