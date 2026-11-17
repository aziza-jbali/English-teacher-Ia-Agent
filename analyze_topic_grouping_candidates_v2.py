
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
TOP_WORD_MATCHES = 5

SIMILARITY_LEVELS = [0.60, 0.70, 0.80, 0.90]


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
# 2. LOAD DATA (READ ONLY)
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

topic_items = defaultdict(list)

models = set()
dimensions = set()

for row in rows:

    try:
        vector = json.loads(row["embedding"])

    except (ValueError, TypeError, json.JSONDecodeError):
        raise ValueError(
            f"Invalid JSON embedding: {row['term']}"
        )

    if not isinstance(vector, list) or not vector:
        raise ValueError(
            f"Invalid embedding format: {row['term']}"
        )

    if not all(
        isinstance(x, (int, float)) and math.isfinite(x)
        for x in vector
    ):
        raise ValueError(
            f"Invalid embedding values: {row['term']}"
        )

    topic_items[row["topic"]].append(
        (row["term"], vector)
    )

    dimensions.add(len(vector))

    if row["embedding_model"]:
        models.add(row["embedding_model"])


if len(dimensions) != 1:
    raise ValueError("Inconsistent embedding dimensions.")

if len(models) != 1:
    raise ValueError("Inconsistent embedding models.")

all_topics = list(topic_items.keys())


# ==================================================
# 4. BUILD TOPIC REPRESENTATIONS
# ==================================================

topic_representations = {}

for topic, items in topic_items.items():

    vectors = [vector for _, vector in items]

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


# ==================================================
# 5. ANALYZE TOPIC PAIRS
# ==================================================

results = []

for topic_a, topic_b in combinations(all_topics, 2):

    items_a = topic_items[topic_a]
    items_b = topic_items[topic_b]

    topic_score = cosine_similarity(
        topic_representations[topic_a],
        topic_representations[topic_b]
    )

    word_scores = []

    for term_a, vector_a in items_a:

        for term_b, vector_b in items_b:

            score = cosine_similarity(vector_a, vector_b)

            word_scores.append(
                (term_a, term_b, score)
            )

    word_scores.sort(
        key=lambda x: x[2],
        reverse=True
    )

    total_comparisons = len(word_scores)

    average_word_similarity = (
        sum(x[2] for x in word_scores) / total_comparisons
        if total_comparisons else 0.0
    )

    best_word_similarity = (
        word_scores[0][2]
        if word_scores else 0.0
    )

    threshold_counts = {
        threshold: sum(
            1 for item in word_scores
            if item[2] >= threshold
        )
        for threshold in SIMILARITY_LEVELS
    }

    results.append({
        "topic_a": topic_a,
        "topic_b": topic_b,
        "topic_score": topic_score,
        "count_a": len(items_a),
        "count_b": len(items_b),
        "total_comparisons": total_comparisons,
        "average_word_similarity": average_word_similarity,
        "best_word_similarity": best_word_similarity,
        "threshold_counts": threshold_counts,
        "top_matches": word_scores[:TOP_WORD_MATCHES]
    })


# ==================================================
# 6. SORT RESULTS
# ==================================================

results.sort(
    key=lambda x: (
        x["best_word_similarity"],
        x["average_word_similarity"],
        x["topic_score"]
    ),
    reverse=True
)


# ==================================================
# 7. VALIDATION SUMMARY
# ==================================================

print("\n" + "=" * 80)
print("SEMANTIC TOPIC GROUPING - DEEP VOCABULARY ANALYSIS")
print("=" * 80)

print("\nDATA VALIDATION")

print("Vocabulary items:", len(rows))
print("Topics:", len(topic_items))
print("Dimensions:", dimensions)
print("Models:", models)
print("Topic pairs:", len(results))


# ==================================================
# 8. TOP 30 PAIRS BY WORD SIMILARITY
# ==================================================

print("\n" + "=" * 80)
print("TOP 30 TOPIC PAIRS BY BEST WORD SIMILARITY")
print("=" * 80)

for result in results[:TOP_TOPIC_PAIRS]:

    print("\n" + "-" * 80)

    print(
        f"{result['topic_a']} <-> {result['topic_b']}"
    )

    print(
        f"Topic similarity: "
        f"{result['topic_score']:.4f}"
    )

    print(
        f"Best word similarity: "
        f"{result['best_word_similarity']:.4f}"
    )

    print(
        f"Average word similarity: "
        f"{result['average_word_similarity']:.4f}"
    )

    print(
        f"Vocabulary counts: "
        f"{result['count_a']} vs {result['count_b']}"
    )

    print("Top word matches:")

    for term_a, term_b, score in result["top_matches"]:

        print(
            f"  {score:.4f} | "
            f"{term_a} <-> {term_b}"
        )

    print("Threshold counts:")

    for threshold, count in result["threshold_counts"].items():

        print(
            f"  >= {threshold:.2f}: {count}"
        )


# ==================================================
# 9. TOP PAIRS BY TOPIC REPRESENTATION
# ==================================================

topic_ranked = sorted(
    results,
    key=lambda x: x["topic_score"],
    reverse=True
)

print("\n" + "=" * 80)
print("TOP 20 PAIRS BY TOPIC REPRESENTATION")
print("=" * 80)

for result in topic_ranked[:20]:

    print(
        f"{result['topic_score']:.4f} | "
        f"{result['topic_a']} <-> {result['topic_b']} | "
        f"Best word: {result['best_word_similarity']:.4f} | "
        f"Average word: {result['average_word_similarity']:.4f}"
    )


# ==================================================
# 10. GLOBAL WORD SIMILARITY DISTRIBUTION
# ==================================================

all_word_scores = []

for result in results:

    all_word_scores.extend(
        match[2] for match in result["top_matches"]
    )

print("\n" + "=" * 80)
print("ANALYSIS SUMMARY")
print("=" * 80)

print("Topics:", len(topic_items))
print("Topic pairs:", len(results))

print("\nDatabase was not modified.")
print("Analysis completed successfully.")
