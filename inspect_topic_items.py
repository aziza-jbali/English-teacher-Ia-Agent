
import sqlite3
from memory import DB_PATH

topics_to_inspect = [
    "Psychology / Personal Growth",
    "Psychology and Personal Growth",
    "Workplace/Psychology",
    "Workplace Stress",
    "Emotions / Stress",
    "Finance & Management",
    "Business & Management",
    "Soft Skills",
    "Professional Development",
    "Ambition",
    "Personal Development",
    "Education and Professional Skills",
    "Professional/General",
    "Work & Professionalism",
]

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

for topic in topics_to_inspect:
    print("\n" + "=" * 60)
    print(f"TOPIC: {topic}")
    print("=" * 60)

    rows = cursor.execute("""
        SELECT term, item_type, meaning_en
        FROM vocabulary_items
        WHERE topic = ?
        ORDER BY term
    """, (topic,)).fetchall()

    if not rows:
        print("No vocabulary items found.")
        continue

    for term, item_type, meaning in rows:
        print(f"- {term} ({item_type})")
        print(f"  Meaning: {meaning}")

connection.close()
