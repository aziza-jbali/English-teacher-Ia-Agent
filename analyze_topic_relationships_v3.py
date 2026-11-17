
import sqlite3
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from memory import DB_PATH

# =====================================================
# CONFIGURATION
# =====================================================

MATCH_THRESHOLD = 0.70
STRONG_MATCH_THRESHOLD = 0.80
RELATED_TOPIC_THRESHOLD = 0.70
MERGE_TOPIC_THRESHOLD = 0.80

MIN_TOPIC_ITEMS_FOR_DECISION = 3
TOP_PAIRS_TO_DISPLAY = 30

REPORT_PATH = Path(__file__).parent / "topic_relationships_v3_report.json"

# =====================================================
# UTILITIES
# =====================================================

def cosine_similarity(a, b):
    if len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if not norm_a or not norm_b:
        return 0.0

    return dot / (norm_a * norm_b)


def normalize_vector(vector):
    norm = math.sqrt(sum(x * x for x in vector))

    if not norm:
        return vector

    return [x / norm for x in vector]


def load_embedding(value):
    try:
        vector = json.loads(value) if isinstance(value, str) else value

        if not isinstance(vector, list):
            return None

        vector = [float(x) for x in vector]

        if not vector or not all(math.isfinite(x) for x in vector):
            return None

        return vector

    except (ValueError, TypeError):
        return None


def get_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


# =====================================================
# 1. LOAD DATABASE (READ ONLY)
# =====================================================

def load_vocabulary():

    connection = sqlite3.connect(
        f"file:{Path(DB_PATH).resolve().as_posix()}?mode=ro",
        uri=True
    )

    connection.row_factory = sqlite3.Row

    try:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(vocabulary_items)"
            )
        }

        term_col = get_column(columns, ["term", "word"])
        topic_col = get_column(columns, ["topic"])
        embedding_col = get_column(columns, ["embedding"])

        if not all([term_col, topic_col, embedding_col]):
            raise RuntimeError(
                "Required columns not found in vocabulary_items."
            )

        query = f"""
            SELECT
                "{term_col}" AS term,
                "{topic_col}" AS topic,
                "{embedding_col}" AS embedding
            FROM vocabulary_items
            WHERE "{embedding_col}" IS NOT NULL
              AND "{topic_col}" IS NOT NULL
        """

        rows = connection.execute(query).fetchall()

        vocabulary = defaultdict(list)

        for row in rows:
            vector = load_embedding(row["embedding"])

            if vector is None:
                continue

            vocabulary[row["topic"]].append({
                "term": row["term"],
                "embedding": vector
            })

        return vocabulary

    finally:
        connection.close()


# =====================================================
# 2. TOPIC REPRESENTATIONS
# =====================================================

def build_topic_centroid(items):

    dimensions = len(items[0]["embedding"])

    valid = [
        item["embedding"]
        for item in items
        if len(item["embedding"]) == dimensions
    ]

    if not valid:
        return None

    centroid = [
        sum(vector[i] for vector in valid) / len(valid)
        for i in range(dimensions)
    ]

    return normalize_vector(centroid)


# =====================================================
# 3. WORD-LEVEL COMPARISON
# =====================================================

def compare_vocabulary(items_a, items_b):

    matches = []

    for item_a in items_a:
        for item_b in items_b:

            similarity = cosine_similarity(
                item_a["embedding"],
                item_b["embedding"]
            )

            matches.append({
                "term_a": item_a["term"],
                "term_b": item_b["term"],
                "similarity": round(similarity, 4)
            })

    matches.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    best_a = {}

    for item in items_a:
        candidates = [
            m for m in matches
            if m["term_a"] == item["term"]
        ]

        best_a[item["term"]] = (
            candidates[0]["similarity"] if candidates else 0
        )

    best_b = {}

    for item in items_b:
        candidates = [
            m for m in matches
            if m["term_b"] == item["term"]
        ]

        best_b[item["term"]] = (
            candidates[0]["similarity"] if candidates else 0
        )

    coverage_a = (
        sum(v >= MATCH_THRESHOLD for v in best_a.values())
        / len(items_a)
    )

    coverage_b = (
        sum(v >= MATCH_THRESHOLD for v in best_b.values())
        / len(items_b)
    )

    exact_matches = [
        m for m in matches
        if m["term_a"].strip().casefold()
        == m["term_b"].strip().casefold()
    ]

    return {
        "best_similarity": matches[0]["similarity"] if matches else 0,
        "average_best_similarity": round(
            (
                sum(best_a.values()) / len(best_a)
                + sum(best_b.values()) / len(best_b)
            ) / 2,
            4
        ),
        "coverage_a": round(coverage_a, 4),
        "coverage_b": round(coverage_b, 4),
        "exact_matches": exact_matches,
        "strong_matches": [
            m for m in matches
            if m["similarity"] >= STRONG_MATCH_THRESHOLD
        ],
        "top_matches": matches[:5]
    }


# =====================================================
# 4. RELATIONSHIP CLASSIFICATION
# =====================================================

def classify_relationship(topic_similarity, comparison, count_a, count_b):

    coverage_a = comparison["coverage_a"]
    coverage_b = comparison["coverage_b"]
    average = comparison["average_best_similarity"]

    if min(count_a, count_b) < MIN_TOPIC_ITEMS_FOR_DECISION:
        return "INSUFFICIENT_DATA"

    if (
        topic_similarity >= MERGE_TOPIC_THRESHOLD
        and average >= 0.72
        and coverage_a >= 0.50
        and coverage_b >= 0.50
    ):
        return "MERGE_CANDIDATE"

    if (
        topic_similarity >= RELATED_TOPIC_THRESHOLD
        and (
            (coverage_a >= 0.60 and coverage_b <= 0.35)
            or
            (coverage_b >= 0.60 and coverage_a <= 0.35)
        )
    ):
        return "PARENT_CHILD_REVIEW"

    if (
        topic_similarity >= RELATED_TOPIC_THRESHOLD
        or average >= 0.65
    ):
        return "RELATED_TOPICS"

    return "WEAK_OR_UNRELATED"


# =====================================================
# 5. ANALYZE ALL TOPIC PAIRS
# =====================================================

def analyze_topics(vocabulary):

    topic_names = sorted(vocabulary.keys())

    centroids = {
        topic: build_topic_centroid(items)
        for topic, items in vocabulary.items()
    }

    results = []

    for topic_a, topic_b in combinations(topic_names, 2):

        centroid_a = centroids[topic_a]
        centroid_b = centroids[topic_b]

        if centroid_a is None or centroid_b is None:
            continue

        topic_similarity = cosine_similarity(
            centroid_a,
            centroid_b
        )

        comparison = compare_vocabulary(
            vocabulary[topic_a],
            vocabulary[topic_b]
        )

        count_a = len(vocabulary[topic_a])
        count_b = len(vocabulary[topic_b])

        relationship = classify_relationship(
            topic_similarity,
            comparison,
            count_a,
            count_b
        )

        results.append({
            "topic_a": topic_a,
            "topic_b": topic_b,
            "topic_similarity": round(topic_similarity, 4),
            "count_a": count_a,
            "count_b": count_b,
            "relationship": relationship,
            **comparison
        })

    return results


# =====================================================
# 6. SAVE REPORT (DATABASE IS NOT MODIFIED)
# =====================================================

def save_report(results, vocabulary):

    report = {
        "analysis": "Semantic Topic Relationships V3",
        "database_modified": False,
        "topic_count": len(vocabulary),
        "vocabulary_count": sum(
            len(items) for items in vocabulary.values()
        ),
        "topic_pair_count": len(results),
        "thresholds": {
            "match": MATCH_THRESHOLD,
            "strong_match": STRONG_MATCH_THRESHOLD,
            "related_topic": RELATED_TOPIC_THRESHOLD,
            "merge_topic": MERGE_TOPIC_THRESHOLD
        },
        "results": results
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return report


# =====================================================
# 7. DISPLAY RESULTS
# =====================================================

def display_results(report):

    print("\n" + "=" * 85)
    print("SEMANTIC TOPIC RELATIONSHIPS - V3")
    print("=" * 85)

    print(f"Vocabulary: {report['vocabulary_count']}")
    print(f"Topics: {report['topic_count']}")
    print(f"Topic pairs: {report['topic_pair_count']}")

    categories = defaultdict(list)

    for result in report["results"]:
        categories[result["relationship"]].append(result)

    for category, pairs in categories.items():

        print("\n" + "=" * 85)
        print(category)
        print("=" * 85)

        pairs.sort(
            key=lambda x: (
                x["topic_similarity"],
                x["average_best_similarity"]
            ),
            reverse=True
        )

        for pair in pairs[:TOP_PAIRS_TO_DISPLAY]:

            print(
                f"\n{pair['topic_a']} <-> {pair['topic_b']}"
            )

            print(
                f"Topic similarity: {pair['topic_similarity']}"
            )

            print(
                f"Average best word similarity: "
                f"{pair['average_best_similarity']}"
            )

            print(
                f"Coverage: "
                f"{pair['coverage_a']} vs {pair['coverage_b']}"
            )

            print(
                f"Vocabulary: {pair['count_a']} vs {pair['count_b']}"
            )

            print("Top matches:")

            for match in pair["top_matches"]:
                print(
                    f"  {match['similarity']:.4f} | "
                    f"{match['term_a']} <-> {match['term_b']}"
                )

    print("\n" + "=" * 85)
    print("ANALYSIS COMPLETED")
    print("Database was not modified.")
    print(f"Report saved: {REPORT_PATH}")
    print("=" * 85)


# =====================================================
# MAIN
# =====================================================

def main():

    print("Loading vocabulary from read-only database...")

    vocabulary = load_vocabulary()

    if len(vocabulary) < 2:
        raise RuntimeError("Not enough topics for comparison.")

    print("Analyzing topic relationships...")

    results = analyze_topics(vocabulary)

    report = save_report(results, vocabulary)

    display_results(report)


if __name__ == "__main__":
    main()
