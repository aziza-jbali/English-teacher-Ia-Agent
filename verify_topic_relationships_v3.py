
import json
from pathlib import Path
from collections import Counter

REPORT_PATH = Path(__file__).parent / "topic_relationships_v3_report.json"

def main():

    if not REPORT_PATH.exists():
        raise FileNotFoundError(
            "Run analyze_topic_relationships_v3.py first."
        )

    report = json.loads(
        REPORT_PATH.read_text(encoding="utf-8")
    )

    results = report["results"]

    print("=" * 75)
    print("TOPIC RELATIONSHIP VERIFICATION")
    print("=" * 75)

    checks = {
        "Report contains results": bool(results),
        "Database marked unchanged": report["database_modified"] is False,
        "All topics have valid names": all(
            p["topic_a"] and p["topic_b"] for p in results
        ),
        "Similarity values are within range": all(
            0 <= p["topic_similarity"] <= 1
            for p in results
        ),
        "Coverage values are within range": all(
            0 <= p["coverage_a"] <= 1
            and 0 <= p["coverage_b"] <= 1
            for p in results
        ),
        "All relationships are classified": all(
            p["relationship"] in {
                "MERGE_CANDIDATE",
                "PARENT_CHILD_REVIEW",
                "RELATED_TOPICS",
                "WEAK_OR_UNRELATED",
                "INSUFFICIENT_DATA"
            }
            for p in results
        ),
        "No duplicate topic pairs": len({
            tuple(sorted((p["topic_a"], p["topic_b"])))
            for p in results
        }) == len(results)
    }

    for name, passed in checks.items():
        print(f"{'OK' if passed else 'FAILED'}: {name}")

    print("\nRelationship distribution:")

    distribution = Counter(
        p["relationship"] for p in results
    )

    for category, count in sorted(distribution.items()):
        print(f"{category}: {count}")

    print("\nTotal pairs:", len(results))

    if all(checks.values()):
        print("\nVerification completed successfully.")
    else:
        raise RuntimeError("Verification failed.")

    print("Database was not modified.")


if __name__ == "__main__":
    main()
