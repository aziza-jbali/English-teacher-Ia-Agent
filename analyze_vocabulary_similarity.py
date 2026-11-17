
import sqlite3
import json
import math
from pathlib import Path
from itertools import combinations
from collections import defaultdict

from memory import DB_PATH


# --------------------------------------------------
# Configuration
# --------------------------------------------------

TOP_TERMS_PER_TOPIC_PAIR = 5
MIN_SIMILARITY_TO_DISPLAY = 0.70

# --------------------------------------------------
# Similarity functions
# --------------------------------------------------

def cosine_similarity(vector_a, vector_b):
    if len(vector_a) != len(vector_b):
        return None

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))

    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return None

    return dot_product / (norm_a * norm_b)


def load_embedding(value):
    try:
        vector = json.loads(value)

        if not isinstance(vector, list) or not vector:
            return None

        vector = [float(x) for x in vector]

        if not all(math.isfinite(x) for x in vector):
            return None

        return vector

    except (TypeError, ValueError, json.JSONDecodeError):
        return None


# --------------------------------------------------
# Load vocabulary
# --------------------------------------------------

connection = sqlite3.connect(DB_PATH)
connection.row_factory = sqlite3.Row

rows = connection.execute("""
    SELECT id, term, topic, embedding, embedding_model
    FROM vocabulary_items
    WHERE topic IS NOT NULL
      AND TRIM(topic) != ''
      AND embedding IS NOT NULL
      AND TRIM(embedding) != ''
    ORDER BY topic, term
""").fetchall()

connection.close()

print("=" * 70)
print("INDIVIDUAL VOCABULARY SIMILARITY ANALYSIS")
print("=" * 70)

print(f"\nVocabulary records loaded: {len(rows)}")

items = []
invalid = 0
dimensions = set()
models = set()

for row in rows:
    vector = load_embedding(row["embedding"])

    if vector is None:
        invalid += 1
        continue

    dimensions.add(len(vector))

    if row["embedding_model"]:
        models.add(row["embedding_model"])

    items.append({
        "id": row["id"],
        "term": row["term"],
        "topic": row["topic"],
        "embedding": vector
    })

print(f"Valid embeddings: {len(items)}")
print(f"Invalid embeddings: {invalid}")
print(f"Dimensions: {dimensions}")
print(f"Models: {models}")

if not items:
    print("\nNo valid embeddings found.")
    raise SystemExit

if len(dimensions) != 1:
    print("\nERROR: Embeddings have inconsistent dimensions.")
    raise SystemExit


# --------------------------------------------------
# Group vocabulary by topic
# --------------------------------------------------

topics = defaultdict(list)

for item in items:
    topics[item["topic"]].append(item)

topic_names = sorted(topics)

print(f"\nUnique topics: {len(topic_names)}")
print("\nVocabulary count per topic:")

for topic in topic_names:
    print(f"  {topic}: {len(topics[topic])}")


# --------------------------------------------------
# Compare individual vocabulary across topics
# --------------------------------------------------

topic_pair_results = []

for topic_a, topic_b in combinations(topic_names, 2):

    matches = []

    for item_a in topics[topic_a]:
        for item_b in topics[topic_b]:

            similarity = cosine_similarity(
                item_a["embedding"],
                item_b["embedding"]
            )

            if similarity is None:
                continue

            matches.append({
                "term_a": item_a["term"],
                "term_b": item_b["term"],
                "similarity": similarity
            })

    if not matches:
        continue

    matches.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    average_similarity = sum(
        match["similarity"] for match in matches
    ) / len(matches)

    topic_pair_results.append({
        "topic_a": topic_a,
        "topic_b": topic_b,
        "average_similarity": average_similarity,
        "best_similarity": matches[0]["similarity"],
        "comparisons": len(matches),
        "matches": matches[:TOP_TERMS_PER_TOPIC_PAIR]
    })


# --------------------------------------------------
# Display topic-pair results
# --------------------------------------------------

topic_pair_results.sort(
    key=lambda x: x["average_similarity"],
    reverse=True
)

print("\n" + "=" * 70)
print("TOPIC PAIRS: INDIVIDUAL VOCABULARY SIMILARITY")
print("=" * 70)

for result in topic_pair_results:

    if result["average_similarity"] < MIN_SIMILARITY_TO_DISPLAY:
        continue

    print("\n" + "-" * 70)

    print(
        f"{result['topic_a']} <-> {result['topic_b']}"
    )

    print(
        f"Average similarity: "
        f"{result['average_similarity']:.4f}"
    )

    print(
        f"Best match: "
        f"{result['best_similarity']:.4f}"
    )

    print(
        f"Comparisons: {result['comparisons']}"
    )

    print("\nMost similar vocabulary:")

    for match in result["matches"]:
        print(
            f"  {match['similarity']:.4f} | "
            f"{match['term_a']} <-> {match['term_b']}"
        )


# --------------------------------------------------
# Summary
# --------------------------------------------------

displayed = [
    result for result in topic_pair_results
    if result["average_similarity"] >= MIN_SIMILARITY_TO_DISPLAY
]

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Total topic pairs compared: {len(topic_pair_results)}")
print(f"Pairs displayed: {len(displayed)}")
print(f"Minimum average similarity: {MIN_SIMILARITY_TO_DISPLAY}")

print("\nAnalysis completed successfully.")
print("Database was not modified.")
