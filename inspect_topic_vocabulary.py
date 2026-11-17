
from memory import get_connection

topics_to_inspect = [
    "Career Development",
    "Business Etiquette",
    "Soft Skills",
    "Professional Training",
    "Professionalism",
    "Workplace Stress",
    "Workplace/Psychology",
    "Communication Skills",
    "Psychology / Personal Growth",
    "Emotions & Psychology",
]

with get_connection() as connection:
    for topic in topics_to_inspect:
        rows = connection.execute("""
            SELECT term, meaning_en, meaning_ar
            FROM vocabulary_items
            WHERE LOWER(TRIM(topic)) = LOWER(TRIM(?))
            ORDER BY term
        """, (topic,)).fetchall()

        print(f"\n{'=' * 60}")
        print(f"TOPIC: {topic}")
        print(f"Vocabulary items: {len(rows)}")
        print("=" * 60)

        for term, meaning_en, meaning_ar in rows:
            print(f"\nTerm: {term}")
            print(f"Meaning EN: {meaning_en}")
            print(f"Meaning AR: {meaning_ar}")
