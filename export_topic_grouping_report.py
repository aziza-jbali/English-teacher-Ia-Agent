
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

INPUT_PATH = BASE_DIR / "topic_relationships_v3_report.json"
OUTPUT_PATH = BASE_DIR / "topic_grouping_review_v3.md"


def main():

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Run V3 analysis first."
        )

    report = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    lines = [
        "# Semantic Topic Grouping - V3 Review",
        "",
        "## Dataset",
        "",
        f"- Vocabulary: {report['vocabulary_count']}",
        f"- Topics: {report['topic_count']}",
        f"- Topic pairs: {report['topic_pair_count']}",
        f"- Database modified: {report['database_modified']}",
        "",
        "## Relationship Candidates",
        ""
    ]

    categories = [
        "MERGE_CANDIDATE",
        "PARENT_CHILD_REVIEW",
        "RELATED_TOPICS",
        "WEAK_OR_UNRELATED",
        "INSUFFICIENT_DATA"
    ]

    for category in categories:

        pairs = [
            p for p in report["results"]
            if p["relationship"] == category
        ]

        lines.extend([
            f"## {category} ({len(pairs)})",
            ""
        ])

        pairs.sort(
            key=lambda p: (
                p["topic_similarity"],
                p["average_best_similarity"]
            ),
            reverse=True
        )

        for pair in pairs:

            lines.extend([
                f"### {pair['topic_a']} <-> {pair['topic_b']}",
                "",
                f"- Topic similarity: {pair['topic_similarity']}",
                f"- Average word similarity: {pair['average_best_similarity']}",
                f"- Coverage A: {pair['coverage_a']}",
                f"- Coverage B: {pair['coverage_b']}",
                f"- Vocabulary counts: {pair['count_a']} vs {pair['count_b']}",
                "",
                "**Top vocabulary matches:**",
                ""
            ])

            for match in pair["top_matches"]:
                lines.append(
                    f"- {match['term_a']} <-> {match['term_b']} "
                    f"({match['similarity']})"
                )

            lines.append("")

    lines.extend([
        "---",
        "",
        "## Important",
        "",
        "These are analytical candidates, not approved changes.",
        "",
        "No automatic topic merging was performed.",
        "",
        "The database was not modified."
    ])

    OUTPUT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    print("Report exported successfully.")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
