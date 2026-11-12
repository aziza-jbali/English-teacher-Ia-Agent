
from memory import search_semantic_vocabulary

test_queries = [
    "How can people recover after difficult experiences?",
    "What can help us deal with obstacles?",
    "I want to improve the way I express my ideas.",
    "How can I explain my opinion in more detail?"
]

for query in test_queries:
    print("\n" + "=" * 65)
    print("QUERY:", query)
    print("=" * 65)

    results = search_semantic_vocabulary(query, limit=5)

    if not results:
        print("No semantic matches found.")
        continue

    for item in results:
        print(
            f"- {item.get('term')} "
            f"| Similarity: {item.get('similarity', 0):.4f}"
        )
        print(f"  Meaning: {item.get('meaning_en')}")
