
import sqlite3
import json
import math
from collections import defaultdict
from itertools import combinations

from memory import DB_PATH


# ==================================================
# CONFIGURATION
# ==================================================

TOP_TOPIC_PAIRS = 30
MIN_TOPIC_SIMILARITY = 0.70
MIN_WORD_SIMILARITY = 0.75

# ==================================================
# 1. COSINE SIMILARITY
# ==================================================

def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ==================================================
# 2. LOAD DATABASE (READ ONLY)
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
finally:
    connection.close()


# ==================================================
# 3. VALIDATE AND GROUP DATA
# ==================================================

topic_vectors = defaultdict(list)
topic_terms = defaultdict(list)

models = set()
dimensions = set()

for row in rows:
    vector = json.loads(row["embedding"])

    if not isinstance(vector, list) or not vector:
        raise ValueError(f"Invalid embedding: {row['term']}")

    if not all(
        isinstance(x, (int, float)) and math.isfinite(x)
        for x in vector
    ):
        raise ValueError(f"Invalid values: {row['term']}")

    topic_vectors[row["topic"]].append(vector)
    topic_terms[row["topic"]].append(
        (row["term"], vector)
    )

    dimensions.add(len(vector))

    if row["embedding_model"]:
        models.add(row["embedding_model"])


if len(dimensions) != 1:
    raise ValueError("Inconsistent embedding dimensions.")

if len(models) != 1:
    raise ValueError("Inconsistent embedding models.")


# ==================================================
# 4. BUILD TOPIC REPRESENTATIONS
# ==================================================

topic_representations = {}

for topic, vectors in topic_vectors.items():

    dimension = len(vectors[0])

    mean_vector = [
        sum(vector[i] for vector in vectors) / len(vectors)
        for i in range(dimension)
    ]

    topic_representations[topic] = mean_vector


# ==================================================
# 5. ANALYZE EVERY TOPIC PAIR
# ==================================================

results = []

for topic_a, topic_b in combinations(topic_vectors.keys(), 2):

    topic_score = cosine_similarity(
        topic_representations[topic_a],
        topic_representations[topic_b]
    )

    matches = []

    for term_a, vector_a in topic_terms[topic_a]:

        for term_b, vector_b in topic_terms[topic_b]:

            score = cosine_similarity(vector_a, vector_b)

            if score >= MIN_WORD_SIMILARITY:
                matches.append(
                    (term_a, term_b, score)
                )

    matches.sort(key=lambda x: x[2], reverse=True)

    count_a = len(topic_terms[topic_a])
    count_b = len(topic_terms[topic_b])

    total_comparisons = count_a * count_b

    match_density = (
        len(matches) / total_comparisons
        if total_comparisons else 0
    )

    results.append({
        "topic_a": topic_a,
        "topic_b": topic_b,
        "topic_score": topic_score,
        "count_a": count_a,
        "count_b": count_b,
        "total_comparisons": total_comparisons,
        "matches": matches,
        "match_count": len(matches),
        "match_density": match_density
    })


# ==================================================
# 6. RANK CANDIDATES
# ==================================================

results.sort(
    key=lambda x: (
        x["topic_score"],
        x["match_density"],
        x["match_count"]
    ),
    reverse=True
)


# ==================================================
# 7. DISPLAY RESULTS
# ==================================================

print("\n" + "=" * 75)
print("ADVANCED SEMANTIC TOPIC GROUPING ANALYSIS")
print("=" * 75)

print("\nDATA VALIDATION")

print("Vocabulary items:", len(rows))
print("Topics:", len(topic_vectors))
print("Dimensions:", dimensions)
print("Embedding models:", models)
print("Topic pairs analyzed:", len(results))


print("\nTOPIC GROUPING CANDIDATES")

displayed = 0

for result in results:

    if result["topic_score"] < MIN_TOPIC_SIMILARITY:
        continue

    displayed += 1

    print("\n" + "-" * 75)

    print(
        f"{result['topic_a']} <-> {result['topic_b']}"
    )

    print(
        f"Topic similarity: "
        f"{result['topic_score']:.4f}"
    )

    print(
        f"Vocabulary counts: "
        f"{result['count_a']} vs {result['count_b']}"
    )

    print(
        f"Similar word pairs: "
        f"{result['match_count']}"
    )

    print(
        f"Match density: "
        f"{result['match_density']:.2%}"
    )

    print("Strongest vocabulary matches:")

    if result["matches"]:

        for term_a, term_b, score in result["matches"][:10]:

            print(
                f"  {score:.4f} | "
                f"{term_a} <-> {term_b}"
            )

    else:
        print("  No word pairs above threshold.")


if displayed == 0:
    print("No topic pairs passed the similarity threshold.")


# ==================================================
# 8. IDENTIFY SMALL TOPICS
# ==================================================

print("\n" + "=" * 75)
print("SMALL TOPICS - LOW DATA CONFIDENCE")
print("=" * 75)

for topic, terms in sorted(
    topic_terms.items(),
    key=lambda x: len(x[1])
):

    if len(terms) <= 2:

        print(f"\n{topic}: {len(terms)} item(s)")

        for term, _ in terms:
            print(" -", term)


# ==================================================
# 9. FINAL SUMMARY
# ==================================================

print("\n" + "=" * 75)
print("ANALYSIS SUMMARY")
print("=" * 75)

print("Total topics:", len(topic_vectors))
print("Total topic pairs:", len(results))

print(
    "Candidates above threshold:",
    sum(
        1 for result in results
        if result["topic_score"] >= MIN_TOPIC_SIMILARITY
    )
)

print("\nAnalysis completed.")
print("Database was not modified.")
