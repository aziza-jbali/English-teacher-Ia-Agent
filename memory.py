

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta



# Store the database beside this file.
DB_PATH = Path(__file__).parent / "learner_memory.db"

# Spaced-repetition intervals, in days.
REVIEW_INTERVALS = [1, 3, 7, 14, 40]


def init_db():
    """Create the tables and safely update an existing database."""

    with sqlite3.connect(DB_PATH) as connection:

        # Table for English mistakes.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_sentence TEXT NOT NULL,
                correction TEXT NOT NULL,
                explanation TEXT,
                category TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table for English vocabulary and expressions.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL,
                item_type TEXT NOT NULL
                    CHECK (item_type IN ('word', 'expression')),
                meaning_ar TEXT NOT NULL,
                definition_en TEXT NOT NULL,
                example TEXT,
                synonyms TEXT,
                topic TEXT,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                mastery_status TEXT NOT NULL DEFAULT 'Learning'
                    CHECK (
                        mastery_status IN (
                            'Learning',
                            'Review',
                            'Mastered'
                        )
                    ),
                review_count INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                wrong_count INTEGER NOT NULL DEFAULT 0,
                next_review_at TEXT,
                last_reviewed_at TEXT
            )
        """)

        # Table for conversation history.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add Phase 3 columns to existing databases.
        existing_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(mistakes)"
            ).fetchall()
        }

        new_columns = {
            "next_review_at": "TEXT",
            "review_count": "INTEGER NOT NULL DEFAULT 0",
            "correct_streak": "INTEGER NOT NULL DEFAULT 0",
            "correct_count": "INTEGER NOT NULL DEFAULT 0",
            "wrong_count": "INTEGER NOT NULL DEFAULT 0",
            "last_reviewed_at": "TEXT",
            "last_review_result": "INTEGER",
        }

        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE mistakes "
                    f"ADD COLUMN {column_name} {column_type}"
                )

        # Schedule existing mistakes based on their original creation date.
        # Old mistakes will already be due if their review date has passed.
        connection.execute("""
            UPDATE mistakes
            SET next_review_at = COALESCE(
                datetime(created_at, '+1 day'),
                datetime('now')
            )
            WHERE next_review_at IS NULL
        """)

        connection.commit()


def save_mistake(original, correction, explanation, category):
    """Save a mistake and schedule its first review for tomorrow."""

    now = datetime.now().replace(microsecond=0)
    next_review = now + timedelta(days=1)

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            INSERT INTO mistakes (
                original_sentence,
                correction,
                explanation,
                category,
                created_at,
                next_review_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            original,
            correction,
            explanation,
            category,
            now.isoformat(sep=" "),
            next_review.isoformat(sep=" "),
        ))

        connection.commit()
        return cursor.lastrowid


def get_mistakes():
    """
    Retrieve saved mistakes.

    Keeps the original six-field return format so existing tutor.py
    code can continue to unpack the results.
    """

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            SELECT
                id,
                original_sentence,
                correction,
                explanation,
                category,
                created_at
            FROM mistakes
            ORDER BY id
        """)

        return cursor.fetchall()


def get_due_mistakes(limit=3):
    """Retrieve mistakes whose scheduled review time has arrived."""

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            SELECT
                id,
                original_sentence,
                correction,
                explanation,
                category,
                created_at,
                next_review_at,
                review_count,
                correct_streak,
                correct_count,
                wrong_count,
                last_reviewed_at,
                last_review_result
            FROM mistakes
            WHERE datetime(next_review_at) <= datetime('now', 'localtime')
            ORDER BY datetime(next_review_at) ASC, id ASC
            LIMIT ?
        """, (limit,))

        return cursor.fetchall()


def record_review_result(mistake_id, was_correct):
    """
    Record the result of an exercise.

    Correct answers receive increasingly longer review intervals.
    Incorrect answers are scheduled again for tomorrow.
    """

    now = datetime.now().replace(microsecond=0)

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute("""
            SELECT
                review_count,
                correct_streak,
                correct_count,
                wrong_count
            FROM mistakes
            WHERE id = ?
        """, (mistake_id,)).fetchone()

        if row is None:
            return False

        review_count, streak, correct_count, wrong_count = row

        review_count += 1

        if was_correct:
            streak += 1
            correct_count += 1

            # 1, 3, 7, 14, then every 40 days.
            interval_index = min(streak - 1, len(REVIEW_INTERVALS) - 1)
            interval_days = REVIEW_INTERVALS[interval_index]

        else:
            streak = 0
            wrong_count += 1
            interval_days = 1

        next_review = now + timedelta(days=interval_days)

        connection.execute("""
            UPDATE mistakes
            SET
                review_count = ?,
                correct_streak = ?,
                correct_count = ?,
                wrong_count = ?,
                last_reviewed_at = ?,
                last_review_result = ?,
                next_review_at = ?
            WHERE id = ?
        """, (
            review_count,
            streak,
            correct_count,
            wrong_count,
            now.isoformat(sep=" "),
            1 if was_correct else 0,
            next_review.isoformat(sep=" "),
            mistake_id,
        ))

        connection.commit()
        return True


def get_learning_stats():
    """Return basic statistics about the learner's saved mistakes."""

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute("""
            SELECT
                COUNT(*),
                COALESCE(SUM(correct_count), 0),
                COALESCE(SUM(wrong_count), 0),
                COALESCE(SUM(
                    CASE
                        WHEN datetime(next_review_at)
                             <= datetime('now', 'localtime')
                        THEN 1
                        ELSE 0
                    END
                ), 0)
            FROM mistakes
        """).fetchone()

    return {
        "total_mistakes": row[0],
        "correct_answers": row[1],
        "wrong_answers": row[2],
        "due_reviews": row[3],
    }


def save_message(role, content):
    """Save one user or tutor message."""

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO conversations (role, content)
            VALUES (?, ?)
        """, (role, content))

        connection.commit()


def get_chat_history(limit=30):
    """Return recent conversation messages in chronological order."""

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            SELECT role, content
            FROM conversations
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        # The query returns newest first; reverse for the tutor.
        return list(reversed(cursor.fetchall()))





# def get_mistake_category_stats():
#     """Count saved mistakes by category."""

#     with sqlite3.connect(DB_PATH) as connection:
#         rows = connection.execute("""
#             SELECT
#                 COALESCE(NULLIF(TRIM(category), ''), 'Uncategorized'),
#                 COUNT(*)
#             FROM mistakes
#             GROUP BY COALESCE(
#                 NULLIF(TRIM(category), ''),
#                 'Uncategorized'
#             )
#             ORDER BY COUNT(*) DESC
#         """).fetchall()

#     return [
#         {"category": category, "count": count}
#         for category, count in rows
#     ]




def get_mistake_category_stats():
    """Count saved mistakes using consistent, meaningful category labels."""

    category_aliases = {
        "grammar": "Grammar",
        "grammar and punctuation": "Grammar/Punctuation",
        "grammar/punctuation": "Grammar/Punctuation",
        "grammar and spelling": "Grammar/Spelling",
        "grammar/spelling": "Grammar/Spelling",
        "grammar/word order": "Grammar/Word Order",
        "verb tense": "Verb Tense",
        "punctuation": "Punctuation",
        "spelling": "Spelling",
        "vocabulary": "Vocabulary",
        "word choice": "Word Choice",
        "word_choice": "Word Choice",
    }

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute("""
            SELECT
                COALESCE(NULLIF(TRIM(category), ''), 'Uncategorized'),
                COUNT(*)
            FROM mistakes
            GROUP BY COALESCE(
                NULLIF(TRIM(category), ''),
                'Uncategorized'
            )
        """).fetchall()

    counts = {}

    for category, count in rows:
        key = category.strip().lower()
        normalized = category_aliases.get(key, category.strip())
        counts[normalized] = counts.get(normalized, 0) + count

    return [
        {"category": category, "count": count}
        for category, count in sorted(
            counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
    ]


# def get_recurring_mistakes():
#     """Group identical saved mistakes and count their occurrences."""

#     with sqlite3.connect(DB_PATH) as connection:
#         rows = connection.execute("""
#             SELECT
#                 original_sentence,
#                 correction,
#                 category,
#                 COUNT(*) AS occurrences
#             FROM mistakes
#             GROUP BY
#                 LOWER(TRIM(original_sentence)),
#                 LOWER(TRIM(correction)),
#                 LOWER(TRIM(COALESCE(category, '')))
#             HAVING COUNT(*) > 1
#             ORDER BY occurrences DESC
#         """).fetchall()

#     return [
#         {
#             "original": original,
#             "correction": correction,
#             "category": category,
#             "occurrences": occurrences,
#         }
#         for original, correction, category, occurrences in rows
#     ]


def get_recurring_mistakes():
    """Identify recurring error patterns across different sentences."""

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute("""
            SELECT original_sentence, correction, category
            FROM mistakes
            ORDER BY id
        """).fetchall()

    patterns = {
        "Verb Tense": [
            "past tense",
            "verb tense",
            "irregular verb",
        ],
        "Grammar/Word Order": [
            "word order",
            "indirect question",
        ],
        "Grammar/Punctuation": [
            "punctuation",
            "comma",
            "question mark",
            "capitalization",
            "capital letter",
        ],
        "Grammar/Spelling": [
            "spelling",
            "misspelled",
        ],
    }

    recurring = {}

    for original, correction, category in rows:
        original_lower = original.lower()
        correction_lower = correction.lower()
        category_lower = (category or "").lower()

        # Identify patterns using the saved category and explanation-free
        # sentence comparison.
        matched_patterns = []

        if category_lower == "verb tense":
            matched_patterns.append("Verb Tense")
        elif "word order" in category_lower:
            matched_patterns.append("Grammar/Word Order")
        elif "spelling" in category_lower:
            matched_patterns.append("Grammar/Spelling")
        elif "punctuation" in category_lower:
            matched_patterns.append("Grammar/Punctuation")

        # Recognize common past-tense errors in different sentences.
        if (
            "yesterday" in original_lower
            and original_lower != correction_lower
        ):
            if "Verb Tense" not in matched_patterns:
                matched_patterns.append("Verb Tense")

        for pattern in matched_patterns:
            if pattern not in recurring:
                recurring[pattern] = {
                    "original": original,
                    "correction": correction,
                    "category": pattern,
                    "occurrences": 0,
                    "examples": [],
                }

            recurring[pattern]["occurrences"] += 1

            if len(recurring[pattern]["examples"]) < 5:
                recurring[pattern]["examples"].append({
                    "original": original,
                    "correction": correction,
                })

    return [
        item
        for item in recurring.values()
        if item["occurrences"] > 1
    ]



# TO SAVE VOCABULARY
# def save_vocabulary(
#     term,
#     item_type,
#     meaning_ar,
#     definition_en,
#     example=None,
#     synonyms=None,
#     topic=None,
#     source=None,
# ):
#     """Save an English word or expression."""

#     if item_type not in ("word", "expression"):
#         raise ValueError("item_type must be 'word' or 'expression'.")

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             INSERT INTO vocabulary (
#                 term,
#                 item_type,
#                 meaning_ar,
#                 definition_en,
#                 example,
#                 synonyms,
#                 topic,
#                 source
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             term.strip(),
#             item_type,
#             meaning_ar.strip(),
#             definition_en.strip(),
#             example,
#             synonyms,
#             topic,
#             source,
#         ))

#         connection.commit()
#         return cursor.lastrowid
def save_vocabulary(
    term,
    item_type,
    meaning_ar,
    definition_en,
    example=None,
    synonyms=None,
    topic=None,
    source=None,
):
    """Save an English word or expression without duplicates."""

    if item_type not in ("word", "expression"):
        raise ValueError("item_type must be 'word' or 'expression'.")

    term = term.strip()

    with sqlite3.connect(DB_PATH) as connection:
        # Check whether this term already exists (case-insensitive).
        existing = connection.execute("""
            SELECT id
            FROM vocabulary
            WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
            LIMIT 1
        """, (term,)).fetchone()

        if existing:
            return existing[0]

        cursor = connection.execute("""
            INSERT INTO vocabulary (
                term,
                item_type,
                meaning_ar,
                definition_en,
                example,
                synonyms,
                topic,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            term,
            item_type,
            meaning_ar.strip(),
            definition_en.strip(),
            example,
            synonyms,
            topic,
            source,
        ))

        connection.commit()
        return cursor.lastrowid
# TO GET ALL VOCABULARY 
def get_vocabulary():
    """Retrieve all saved vocabulary items."""

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            SELECT
                id,
                term,
                item_type,
                meaning_ar,
                definition_en,
                example,
                synonyms,
                topic,
                source,
                created_at,
                mastery_status,
                review_count,
                correct_count,
                wrong_count,
                next_review_at,
                last_reviewed_at
            FROM vocabulary
            ORDER BY id
        """)

        return cursor.fetchall()

def search_vocabulary(term):
    """Search vocabulary by word or expression."""

    with sqlite3.connect(DB_PATH) as connection:
            cursor = connection.execute("""
                SELECT
                    id,
                    term,
                    item_type,
                    meaning_ar,
                    definition_en,
                    example,
                    synonyms,
                    topic,
                    source,
                    created_at,
                    mastery_status,
                    review_count,
                    correct_count,
                    wrong_count,
                    next_review_at,
                    last_reviewed_at
                FROM vocabulary
                WHERE term LIKE ?
                ORDER BY term
            """, (f"%{term.strip()}%",))

            return cursor.fetchall()
# results = search_vocabulary("Encoder")
# for item in results:
#         print("itemnnn",item)    

def update_vocabulary(
    vocabulary_id,
    meaning_ar=None,
    definition_en=None,
    example=None,
    synonyms=None,
    topic=None,
    source=None,
):
    """Update selected information for a vocabulary item."""

    fields = {
        "meaning_ar": meaning_ar,
        "definition_en": definition_en,
        "example": example,
        "synonyms": synonyms,
        "topic": topic,
        "source": source,
    }

    updates = {
        key: value
        for key, value in fields.items()
        if value is not None
    }

    if not updates:
        return False

    set_clause = ", ".join(
        f"{column} = ?" for column in updates
    )

    values = list(updates.values())
    values.append(vocabulary_id)

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            f"UPDATE vocabulary SET {set_clause} WHERE id = ?",
            values,
        )

        connection.commit()
        return cursor.rowcount > 0



def delete_vocabulary(vocabulary_id):
    """Delete a vocabulary item by its ID."""

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "DELETE FROM vocabulary WHERE id = ?",
            (vocabulary_id,)
        )

        connection.commit()
        return cursor.rowcount > 0




























if __name__ == "__main__":
    init_db()

    print(f"Database initialized at: {DB_PATH}")

    print("\nSaved English mistakes:")
    for mistake in get_mistakes():
        print(mistake)

    print("\nMistakes due for review:")
    for mistake in get_due_mistakes():
        print(mistake)

    print("\nLearning statistics:")
    print(get_learning_stats())

    print("\nMistakes by category:")
    for item in get_mistake_category_stats():
        print(f"{item['category']}: {item['count']}")

    print("\nRecent conversation:")
    for message in get_chat_history():
        print(message)





















# if __name__ == "__main__":

    

#     init_db()

#     print(f"Database initialized at: {DB_PATH}")

#     print("\nSaved English mistakes:")
#     for mistake in get_mistakes():
#         print(mistake)

#     print("\nMistakes due for review:")
#     for mistake in get_due_mistakes():
#         print(mistake)

#     print("\nLearning statistics:")
#     print(get_learning_stats())

#     print("\nRecent conversation:")
#     for message in get_chat_history():
#         print(message)
