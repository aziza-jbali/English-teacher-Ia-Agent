

# import sqlite3
# from pathlib import Path
# from datetime import datetime, timedelta



# # Store the database beside this file.
# DB_PATH = Path(__file__).parent / "learner_memory.db"

# # Spaced-repetition intervals, in days.
# REVIEW_INTERVALS = [1, 3, 7, 14, 40]


# def init_db():
#     """Create the tables and safely update an existing database."""

#     with sqlite3.connect(DB_PATH) as connection:

#         # Table for English mistakes.
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS mistakes (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 original_sentence TEXT NOT NULL,
#                 correction TEXT NOT NULL,
#                 explanation TEXT,
#                 category TEXT,
#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
#         # Table for English vocabulary and expressions.
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS vocabulary (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 term TEXT NOT NULL,
#                 item_type TEXT NOT NULL
#                     CHECK (item_type IN ('word', 'expression')),
#                 meaning_ar TEXT NOT NULL,
#                 definition_en TEXT NOT NULL,
#                 example TEXT,
#                 synonyms TEXT,
#                 topic TEXT,
#                 source TEXT,
#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
#                 mastery_status TEXT NOT NULL DEFAULT 'Learning'
#                     CHECK (
#                         mastery_status IN (
#                             'Learning',
#                             'Review',
#                             'Mastered'
#                         )
#                     ),
#                 review_count INTEGER NOT NULL DEFAULT 0,
#                 correct_count INTEGER NOT NULL DEFAULT 0,
#                 wrong_count INTEGER NOT NULL DEFAULT 0,
#                 next_review_at TEXT,
#                 last_reviewed_at TEXT
#             )
#         """)
#         # New unified table for all vocabulary items.
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS vocabulary_items (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,

#                 term TEXT NOT NULL COLLATE NOCASE,
#                 item_type TEXT NOT NULL CHECK (
#                     item_type IN (
#                         'word',
#                         'expression',
#                         'phrasal verb',
#                         'idiom',
#                         'collocation'
#                     )
#                 ),

#                 grammatical_class TEXT,
#                 meaning_ar TEXT NOT NULL,
#                 meaning_en TEXT,
#                 definition_en TEXT,
#                 example TEXT,
#                 synonyms TEXT,
#                 topic TEXT,
#                 source TEXT,

#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
#                 updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
#                 first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
#                 last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,

#                 occurrence_count INTEGER NOT NULL DEFAULT 1,

#                 mastery_status TEXT NOT NULL DEFAULT 'Learning'
#                     CHECK (
#                         mastery_status IN (
#                             'Learning',
#                             'Review',
#                             'Mastered'
#                         )
#                     ),

#                 review_count INTEGER NOT NULL DEFAULT 0,
#                 correct_count INTEGER NOT NULL DEFAULT 0,
#                 wrong_count INTEGER NOT NULL DEFAULT 0,
#                 correct_streak INTEGER NOT NULL DEFAULT 0,

#                 next_review_at TEXT,
#                 last_reviewed_at TEXT,
#                 mastered_at TEXT
#             )
#         """)
#         # Table for conversation history.
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS conversations (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 role TEXT NOT NULL,
#                 content TEXT NOT NULL,
#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP
#             )
#         """)

#         # Add Phase 3 columns to existing databases.
#         existing_columns = {
#             row[1]
#             for row in connection.execute(
#                 "PRAGMA table_info(mistakes)"
#             ).fetchall()
#         }

#         new_columns = {
#             "next_review_at": "TEXT",
#             "review_count": "INTEGER NOT NULL DEFAULT 0",
#             "correct_streak": "INTEGER NOT NULL DEFAULT 0",
#             "correct_count": "INTEGER NOT NULL DEFAULT 0",
#             "wrong_count": "INTEGER NOT NULL DEFAULT 0",
#             "last_reviewed_at": "TEXT",
#             "last_review_result": "INTEGER",
#         }

#         for column_name, column_type in new_columns.items():
#             if column_name not in existing_columns:
#                 connection.execute(
#                     f"ALTER TABLE mistakes "
#                     f"ADD COLUMN {column_name} {column_type}"
#                 )

#         # Schedule existing mistakes based on their original creation date.
#         # Old mistakes will already be due if their review date has passed.
#         connection.execute("""
#             UPDATE mistakes
#             SET next_review_at = COALESCE(
#                 datetime(created_at, '+1 day'),
#                 datetime('now')
#             )
#             WHERE next_review_at IS NULL
#         """)

#         connection.commit()


# def save_mistake(original, correction, explanation, category):
#     """Save a mistake and schedule its first review for tomorrow."""

#     now = datetime.now().replace(microsecond=0)
#     next_review = now + timedelta(days=1)

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             INSERT INTO mistakes (
#                 original_sentence,
#                 correction,
#                 explanation,
#                 category,
#                 created_at,
#                 next_review_at
#             )
#             VALUES (?, ?, ?, ?, ?, ?)
#         """, (
#             original,
#             correction,
#             explanation,
#             category,
#             now.isoformat(sep=" "),
#             next_review.isoformat(sep=" "),
#         ))

#         connection.commit()
#         return cursor.lastrowid


# def get_mistakes():
#     """
#     Retrieve saved mistakes.

#     Keeps the original six-field return format so existing tutor.py
#     code can continue to unpack the results.
#     """

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 id,
#                 original_sentence,
#                 correction,
#                 explanation,
#                 category,
#                 created_at
#             FROM mistakes
#             ORDER BY id
#         """)

#         return cursor.fetchall()


# def get_due_mistakes(limit=3):
#     """Retrieve mistakes whose scheduled review time has arrived."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 id,
#                 original_sentence,
#                 correction,
#                 explanation,
#                 category,
#                 created_at,
#                 next_review_at,
#                 review_count,
#                 correct_streak,
#                 correct_count,
#                 wrong_count,
#                 last_reviewed_at,
#                 last_review_result
#             FROM mistakes
#             WHERE datetime(next_review_at) <= datetime('now', 'localtime')
#             ORDER BY datetime(next_review_at) ASC, id ASC
#             LIMIT ?
#         """, (limit,))

#         return cursor.fetchall()


# def record_review_result(mistake_id, was_correct):
#     """
#     Record the result of an exercise.

#     Correct answers receive increasingly longer review intervals.
#     Incorrect answers are scheduled again for tomorrow.
#     """

#     now = datetime.now().replace(microsecond=0)

#     with sqlite3.connect(DB_PATH) as connection:
#         row = connection.execute("""
#             SELECT
#                 review_count,
#                 correct_streak,
#                 correct_count,
#                 wrong_count
#             FROM mistakes
#             WHERE id = ?
#         """, (mistake_id,)).fetchone()

#         if row is None:
#             return False

#         review_count, streak, correct_count, wrong_count = row

#         review_count += 1

#         if was_correct:
#             streak += 1
#             correct_count += 1

#             # 1, 3, 7, 14, then every 40 days.
#             interval_index = min(streak - 1, len(REVIEW_INTERVALS) - 1)
#             interval_days = REVIEW_INTERVALS[interval_index]

#         else:
#             streak = 0
#             wrong_count += 1
#             interval_days = 1

#         next_review = now + timedelta(days=interval_days)

#         connection.execute("""
#             UPDATE mistakes
#             SET
#                 review_count = ?,
#                 correct_streak = ?,
#                 correct_count = ?,
#                 wrong_count = ?,
#                 last_reviewed_at = ?,
#                 last_review_result = ?,
#                 next_review_at = ?
#             WHERE id = ?
#         """, (
#             review_count,
#             streak,
#             correct_count,
#             wrong_count,
#             now.isoformat(sep=" "),
#             1 if was_correct else 0,
#             next_review.isoformat(sep=" "),
#             mistake_id,
#         ))

#         connection.commit()
#         return True


# def get_learning_stats():
#     """Return basic statistics about the learner's saved mistakes."""

#     with sqlite3.connect(DB_PATH) as connection:
#         row = connection.execute("""
#             SELECT
#                 COUNT(*),
#                 COALESCE(SUM(correct_count), 0),
#                 COALESCE(SUM(wrong_count), 0),
#                 COALESCE(SUM(
#                     CASE
#                         WHEN datetime(next_review_at)
#                              <= datetime('now', 'localtime')
#                         THEN 1
#                         ELSE 0
#                     END
#                 ), 0)
#             FROM mistakes
#         """).fetchone()

#     return {
#         "total_mistakes": row[0],
#         "correct_answers": row[1],
#         "wrong_answers": row[2],
#         "due_reviews": row[3],
#     }


# def save_message(role, content):
#     """Save one user or tutor message."""

#     with sqlite3.connect(DB_PATH) as connection:
#         connection.execute("""
#             INSERT INTO conversations (role, content)
#             VALUES (?, ?)
#         """, (role, content))

#         connection.commit()


# def get_chat_history(limit=30):
#     """Return recent conversation messages in chronological order."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT role, content
#             FROM conversations
#             ORDER BY id DESC
#             LIMIT ?
#         """, (limit,))

#         # The query returns newest first; reverse for the tutor.
#         return list(reversed(cursor.fetchall()))





# # def get_mistake_category_stats():
# #     """Count saved mistakes by category."""

# #     with sqlite3.connect(DB_PATH) as connection:
# #         rows = connection.execute("""
# #             SELECT
# #                 COALESCE(NULLIF(TRIM(category), ''), 'Uncategorized'),
# #                 COUNT(*)
# #             FROM mistakes
# #             GROUP BY COALESCE(
# #                 NULLIF(TRIM(category), ''),
# #                 'Uncategorized'
# #             )
# #             ORDER BY COUNT(*) DESC
# #         """).fetchall()

# #     return [
# #         {"category": category, "count": count}
# #         for category, count in rows
# #     ]




# def get_mistake_category_stats():
#     """Count saved mistakes using consistent, meaningful category labels."""

#     category_aliases = {
#         "grammar": "Grammar",
#         "grammar and punctuation": "Grammar/Punctuation",
#         "grammar/punctuation": "Grammar/Punctuation",
#         "grammar and spelling": "Grammar/Spelling",
#         "grammar/spelling": "Grammar/Spelling",
#         "grammar/word order": "Grammar/Word Order",
#         "verb tense": "Verb Tense",
#         "punctuation": "Punctuation",
#         "spelling": "Spelling",
#         "vocabulary": "Vocabulary",
#         "word choice": "Word Choice",
#         "word_choice": "Word Choice",
#     }

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
#         """).fetchall()

#     counts = {}

#     for category, count in rows:
#         key = category.strip().lower()
#         normalized = category_aliases.get(key, category.strip())
#         counts[normalized] = counts.get(normalized, 0) + count

#     return [
#         {"category": category, "count": count}
#         for category, count in sorted(
#             counts.items(),
#             key=lambda item: item[1],
#             reverse=True
#         )
#     ]


# # def get_recurring_mistakes():
# #     """Group identical saved mistakes and count their occurrences."""

# #     with sqlite3.connect(DB_PATH) as connection:
# #         rows = connection.execute("""
# #             SELECT
# #                 original_sentence,
# #                 correction,
# #                 category,
# #                 COUNT(*) AS occurrences
# #             FROM mistakes
# #             GROUP BY
# #                 LOWER(TRIM(original_sentence)),
# #                 LOWER(TRIM(correction)),
# #                 LOWER(TRIM(COALESCE(category, '')))
# #             HAVING COUNT(*) > 1
# #             ORDER BY occurrences DESC
# #         """).fetchall()

# #     return [
# #         {
# #             "original": original,
# #             "correction": correction,
# #             "category": category,
# #             "occurrences": occurrences,
# #         }
# #         for original, correction, category, occurrences in rows
# #     ]


# def get_recurring_mistakes():
#     """Identify recurring error patterns across different sentences."""

#     with sqlite3.connect(DB_PATH) as connection:
#         rows = connection.execute("""
#             SELECT original_sentence, correction, category
#             FROM mistakes
#             ORDER BY id
#         """).fetchall()

#     patterns = {
#         "Verb Tense": [
#             "past tense",
#             "verb tense",
#             "irregular verb",
#         ],
#         "Grammar/Word Order": [
#             "word order",
#             "indirect question",
#         ],
#         "Grammar/Punctuation": [
#             "punctuation",
#             "comma",
#             "question mark",
#             "capitalization",
#             "capital letter",
#         ],
#         "Grammar/Spelling": [
#             "spelling",
#             "misspelled",
#         ],
#     }

#     recurring = {}

#     for original, correction, category in rows:
#         original_lower = original.lower()
#         correction_lower = correction.lower()
#         category_lower = (category or "").lower()

#         # Identify patterns using the saved category and explanation-free
#         # sentence comparison.
#         matched_patterns = []

#         if category_lower == "verb tense":
#             matched_patterns.append("Verb Tense")
#         elif "word order" in category_lower:
#             matched_patterns.append("Grammar/Word Order")
#         elif "spelling" in category_lower:
#             matched_patterns.append("Grammar/Spelling")
#         elif "punctuation" in category_lower:
#             matched_patterns.append("Grammar/Punctuation")

#         # Recognize common past-tense errors in different sentences.
#         if (
#             "yesterday" in original_lower
#             and original_lower != correction_lower
#         ):
#             if "Verb Tense" not in matched_patterns:
#                 matched_patterns.append("Verb Tense")

#         for pattern in matched_patterns:
#             if pattern not in recurring:
#                 recurring[pattern] = {
#                     "original": original,
#                     "correction": correction,
#                     "category": pattern,
#                     "occurrences": 0,
#                     "examples": [],
#                 }

#             recurring[pattern]["occurrences"] += 1

#             if len(recurring[pattern]["examples"]) < 5:
#                 recurring[pattern]["examples"].append({
#                     "original": original,
#                     "correction": correction,
#                 })

#     return [
#         item
#         for item in recurring.values()
#         if item["occurrences"] > 1
#     ]



# # TO SAVE VOCABULARY
# # def save_vocabulary(
# #     term,
# #     item_type,
# #     meaning_ar,
# #     definition_en,
# #     example=None,
# #     synonyms=None,
# #     topic=None,
# #     source=None,
# # ):
# #     """Save an English word or expression."""

# #     if item_type not in ("word", "expression"):
# #         raise ValueError("item_type must be 'word' or 'expression'.")

# #     with sqlite3.connect(DB_PATH) as connection:
# #         cursor = connection.execute("""
# #             INSERT INTO vocabulary (
# #                 term,
# #                 item_type,
# #                 meaning_ar,
# #                 definition_en,
# #                 example,
# #                 synonyms,
# #                 topic,
# #                 source
# #             )
# #             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
# #         """, (
# #             term.strip(),
# #             item_type,
# #             meaning_ar.strip(),
# #             definition_en.strip(),
# #             example,
# #             synonyms,
# #             topic,
# #             source,
# #         ))

# #         connection.commit()
# #         return cursor.lastrowid
# # def save_vocabulary(
# #     term,
# #     item_type,
# #     meaning_ar,
# #     definition_en,
# #     example=None,
# #     synonyms=None,
# #     topic=None,
# #     source=None,
# # ):
# #     """Save an English word or expression without duplicates."""

# #     if item_type not in ("word", "expression"):
# #         raise ValueError("item_type must be 'word' or 'expression'.")

# #     term = term.strip()

# #     with sqlite3.connect(DB_PATH) as connection:
# #         # Check whether this term already exists (case-insensitive).
# #         existing = connection.execute("""
# #             SELECT id
# #             FROM vocabulary
# #             WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
# #             LIMIT 1
# #         """, (term,)).fetchone()

# #         if existing:
# #             return existing[0]

# #         cursor = connection.execute("""
# #             INSERT INTO vocabulary (
# #                 term,
# #                 item_type,
# #                 meaning_ar,
# #                 definition_en,
# #                 example,
# #                 synonyms,
# #                 topic,
# #                 source
# #             )
# #             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
# #         """, (
# #             term,
# #             item_type,
# #             meaning_ar.strip(),
# #             definition_en.strip(),
# #             example,
# #             synonyms,
# #             topic,
# #             source,
# #         ))

# #         connection.commit()
# #         return cursor.lastrowid
# def save_vocabulary(
#     term,
#     item_type,
#     meaning_ar,
#     definition_en=None,
#     example=None,
#     synonyms=None,
#     topic=None,
#     source=None,
#     grammatical_class=None,
#     meaning_en=None,
# ):
#     """Save vocabulary items in the unified vocabulary_items table."""

#     allowed_types = (
#         "word",
#         "expression",
#         "phrasal verb",
#         "idiom",
#         "collocation",
#     )

#     if item_type not in allowed_types:
#         raise ValueError(
#             f"item_type must be one of: {', '.join(allowed_types)}"
#         )

#     term = term.strip()

#     if not term:
#         raise ValueError("term cannot be empty.")

#     if not meaning_ar or not meaning_ar.strip():
#         raise ValueError("meaning_ar cannot be empty.")

#     with sqlite3.connect(DB_PATH) as connection:

#         # Check for an existing item with the same term and type.
#         existing = connection.execute("""
#             SELECT id
#             FROM vocabulary_items
#             WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
#               AND item_type = ?
#             LIMIT 1
#         """, (term, item_type)).fetchone()

#         if existing:
#             vocabulary_id = existing[0]

#             # Record another occurrence without overwriting saved meanings.
#             connection.execute("""
#                 UPDATE vocabulary_items
#                 SET occurrence_count = occurrence_count + 1,
#                     last_seen_at = CURRENT_TIMESTAMP
#                 WHERE id = ?
#             """, (vocabulary_id,))

#             return vocabulary_id

#         # Insert a new vocabulary item.
#         cursor = connection.execute("""
#             INSERT INTO vocabulary_items (
#                 term,
#                 item_type,
#                 grammatical_class,
#                 meaning_ar,
#                 meaning_en,
#                 definition_en,
#                 example,
#                 synonyms,
#                 topic,
#                 source
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """, (
#             term,
#             item_type,
#             grammatical_class,
#             meaning_ar.strip(),
#             meaning_en.strip() if meaning_en else None,
#             definition_en.strip() if definition_en else None,
#             example,
#             synonyms,
#             topic,
#             source,
#         ))

#         return cursor.lastrowid
# # TO GET ALL VOCABULARY 
# # def get_vocabulary():
# #     """Retrieve all saved vocabulary items."""

# #     with sqlite3.connect(DB_PATH) as connection:
# #         cursor = connection.execute("""
# #             SELECT
# #                 id,
# #                 term,
# #                 item_type,
# #                 meaning_ar,
# #                 definition_en,
# #                 example,
# #                 synonyms,
# #                 topic,
# #                 source,
# #                 created_at,
# #                 mastery_status,
# #                 review_count,
# #                 correct_count,
# #                 wrong_count,
# #                 next_review_at,
# #                 last_reviewed_at
# #             FROM vocabulary
# #             ORDER BY id
# #         """)

# #         return cursor.fetchall()

# def get_vocabulary():
#     """Retrieve all saved vocabulary items from vocabulary_items."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 id,
#                 term,
#                 item_type,
#                 meaning_ar,
#                 definition_en,
#                 example,
#                 synonyms,
#                 topic,
#                 source,
#                 created_at,
#                 mastery_status,
#                 review_count,
#                 correct_count,
#                 wrong_count,
#                 next_review_at,
#                 last_reviewed_at,
#                 grammatical_class,
#                 meaning_en,
#                 occurrence_count,
#                 correct_streak
#             FROM vocabulary_items
#             ORDER BY id
#         """)

#         return cursor.fetchall()
# def search_vocabulary(term):
#     """Search vocabulary items in vocabulary_items."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 id,
#                 term,
#                 item_type,
#                 meaning_ar,
#                 definition_en,
#                 example,
#                 synonyms,
#                 topic,
#                 source,
#                 created_at,
#                 mastery_status,
#                 review_count,
#                 correct_count,
#                 wrong_count,
#                 next_review_at,
#                 last_reviewed_at,
#                 grammatical_class,
#                 meaning_en,
#                 occurrence_count,
#                 correct_streak
#             FROM vocabulary_items
#             WHERE term LIKE ?
#             ORDER BY term
#         """, (f"%{term.strip()}%",))

#         return cursor.fetchall()
# def update_vocabulary(
#     vocabulary_id,
#     meaning_ar=None,
#     meaning_en=None,
#     definition_en=None,
#     grammatical_class=None,
#     example=None,
#     synonyms=None,
#     topic=None,
#     source=None,
# ):
#     """Update selected information for a vocabulary item."""

#     fields = {
#         "meaning_ar": meaning_ar,
#         "meaning_en": meaning_en,
#         "definition_en": definition_en,
#         "grammatical_class": grammatical_class,
#         "example": example,
#         "synonyms": synonyms,
#         "topic": topic,
#         "source": source,
#     }

#     updates = {
#         key: value
#         for key, value in fields.items()
#         if value is not None
#     }

#     if not updates:
#         return False

#     set_clause = ", ".join(
#         f"{column} = ?" for column in updates
#     )
#     set_clause += ", updated_at = CURRENT_TIMESTAMP"

#     values = list(updates.values())
#     values.append(vocabulary_id)

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute(
#             f"UPDATE vocabulary_items SET {set_clause} WHERE id = ?",
#             values,
#         )

#         return cursor.rowcount > 0

# def delete_vocabulary(vocabulary_id):
#     """Delete a vocabulary item by its ID."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute(
#             "DELETE FROM vocabulary_items WHERE id = ?",
#             (vocabulary_id,)
#         )

#         return cursor.rowcount > 0



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

#     print("\nMistakes by category:")
#     for item in get_mistake_category_stats():
#         print(f"{item['category']}: {item['count']}")

#     print("\nRecent conversation:")
#     for message in get_chat_history():
#         print(message)





















# # if __name__ == "__main__":

    

# #     init_db()

# #     print(f"Database initialized at: {DB_PATH}")

# #     print("\nSaved English mistakes:")
# #     for mistake in get_mistakes():
# #         print(mistake)

# #     print("\nMistakes due for review:")
# #     for mistake in get_due_mistakes():
# #         print(mistake)

# #     print("\nLearning statistics:")
# #     print(get_learning_stats())

# #     print("\nRecent conversation:")
# #     for message in get_chat_history():
# #         print(message)































































































































import sqlite3
import os
import json
import math
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai
from google.genai import types  # add this import at the top of the file

# Store the database beside this file.
DB_PATH = Path(__file__).parent / "learner_memory.db"

# Spaced-repetition intervals, in days.
REVIEW_INTERVALS = [1, 3, 7, 14, 40]

# Semantic embedding configuration.
EMBEDDING_MODEL = "gemini-embedding-001"

# Initial similarity thresholds.
SIMILARITY_THRESHOLD = 0.65
STRONG_SIMILARITY_THRESHOLD = 0.85

ALLOWED_ITEM_TYPES = (
    "word",
    "expression",
    "phrasal verb",
    "idiom",
    "collocation",
)


@contextmanager
def get_connection():
    """
    Open a SQLite connection, commit on success, roll back on error,
    and ALWAYS close it.

    (Plain `with sqlite3.connect(...)` commits but never closes the
    connection, which can leave the database file locked.)
    """

    connection = sqlite3.connect(DB_PATH)

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    """Create the tables and safely update an existing database."""

    with get_connection() as connection:

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

        # Legacy table for English vocabulary and expressions.
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

        # Unified table for all vocabulary items.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                term TEXT NOT NULL COLLATE NOCASE,
                item_type TEXT NOT NULL CHECK (
                    item_type IN (
                        'word',
                        'expression',
                        'phrasal verb',
                        'idiom',
                        'collocation'
                    )
                ),

                grammatical_class TEXT,
                meaning_ar TEXT NOT NULL,
                meaning_en TEXT,
                definition_en TEXT,
                example TEXT,
                synonyms TEXT,
                topic TEXT,
                source TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,

                occurrence_count INTEGER NOT NULL DEFAULT 1,

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
                correct_streak INTEGER NOT NULL DEFAULT 0,

                next_review_at TEXT,
                last_reviewed_at TEXT,
                mastered_at TEXT
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
        # 'localtime' keeps the fallback consistent with the Python-written
        # timestamps and with the comparison used in get_due_mistakes().
        connection.execute("""
            UPDATE mistakes
            SET next_review_at = COALESCE(
                datetime(created_at, '+1 day'),
                datetime('now', 'localtime')
            )
            WHERE next_review_at IS NULL
        """)

        # Add embedding columns to existing vocabulary databases.
        vocabulary_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(vocabulary_items)"
            ).fetchall()
        }

        if "embedding" not in vocabulary_columns:
            connection.execute("""
                ALTER TABLE vocabulary_items
                ADD COLUMN embedding TEXT
            """)

        if "embedding_model" not in vocabulary_columns:
            connection.execute("""
                ALTER TABLE vocabulary_items
                ADD COLUMN embedding_model TEXT
            """)

        # Store semantic relationships between vocabulary items.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS semantic_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                related_item_id INTEGER NOT NULL,
                similarity REAL NOT NULL,
                relationship_type TEXT NOT NULL
                    CHECK (
                        relationship_type IN ('similar', 'strong')
                    ),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(item_id, related_item_id)
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_semantic_relationships_item
            ON semantic_relationships(item_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_semantic_relationships_related
            ON semantic_relationships(related_item_id)
        """)


# ----------------------------------------------------------------------
# Mistakes
# ----------------------------------------------------------------------

def save_mistake(original, correction, explanation, category):
    """Save a mistake and schedule its first review for tomorrow."""

    now = datetime.now().replace(microsecond=0)
    next_review = now + timedelta(days=1)

    with get_connection() as connection:
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

        return cursor.lastrowid


def get_mistakes():
    """
    Retrieve saved mistakes.

    Keeps the original six-field return format so existing tutor.py
    code can continue to unpack the results.
    """

    with get_connection() as connection:
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

    with get_connection() as connection:
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

    with get_connection() as connection:
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

        return True


def get_learning_stats():
    """Return basic statistics about the learner's saved mistakes."""

    with get_connection() as connection:
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


# ----------------------------------------------------------------------
# Conversation history
# ----------------------------------------------------------------------

def save_message(role, content):
    """Save one user or tutor message."""

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO conversations (role, content)
            VALUES (?, ?)
        """, (role, content))


def get_chat_history(limit=30):
    """Return recent conversation messages in chronological order."""

    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT role, content
            FROM conversations
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()

    # The query returns newest first; reverse for the tutor.
    return list(reversed(rows))


# ----------------------------------------------------------------------
# Mistake statistics
# ----------------------------------------------------------------------

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

    with get_connection() as connection:
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


def get_recurring_mistakes():
    """Identify recurring error patterns across different sentences."""

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT original_sentence, correction, category
            FROM mistakes
            ORDER BY id
        """).fetchall()

    recurring = {}

    for original, correction, category in rows:
        original_lower = original.lower()
        correction_lower = correction.lower()
        category_lower = (category or "").lower()

        # Identify patterns using the saved category.
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


# ----------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------

_gemini_client = None


def _get_gemini_client():
    """Create the Gemini client once and reuse it."""

    global _gemini_client

    if _gemini_client is None:
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY was not found in .env")

        # _gemini_client = genai.Client(api_key=api_key)
        

        _gemini_client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=60_000),  # 60 seconds
            )

    return _gemini_client


def generate_embedding(term):
    """
    Generate an embedding for an English vocabulary item
    using Gemini.
    """

    client = _get_gemini_client()

    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=term
    )

    return result.embeddings[0].values


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two embedding vectors."""

    if len(vector_a) != len(vector_b):
        return None

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return None

    return dot_product / (norm_a * norm_b)

def search_semantic_vocabulary(query, limit=5):
    """
    Search vocabulary_items using semantic similarity.

    Generates an embedding for the query, compares it with
    stored vocabulary embeddings, and returns the closest items.
    """

    if not query or not query.strip():
        return []

    query_embedding = generate_embedding(query.strip())

    with get_connection() as connection:
        rows = connection.execute(f"""
            SELECT
                {_VOCABULARY_COLUMNS},
                embedding,
                embedding_model
            FROM vocabulary_items
            WHERE embedding IS NOT NULL
              AND embedding_model = ?
        """, (EMBEDDING_MODEL,)).fetchall()

    matches = []

    for row in rows:
        vocabulary_data = row[:-2]
        stored_embedding = row[-2]
        stored_model = row[-1]

        if stored_model != EMBEDDING_MODEL:
            continue

        try:
            existing_embedding = json.loads(stored_embedding)

            similarity = cosine_similarity(
                query_embedding,
                existing_embedding
            )

            if similarity is None:
                continue

            if similarity >= SIMILARITY_THRESHOLD:
                item = dict(zip(
                    [
                        "id", "term", "item_type", "meaning_ar",
                        "definition_en", "example", "synonyms",
                        "topic", "source", "created_at",
                        "mastery_status", "review_count",
                        "correct_count", "wrong_count",
                        "next_review_at", "last_reviewed_at",
                        "grammatical_class", "meaning_en",
                        "occurrence_count", "correct_streak"
                    ],
                    vocabulary_data
                ))

                item["similarity"] = similarity
                matches.append(item)

        except (json.JSONDecodeError, TypeError, ValueError) as error:
            print(
                f"[WARNING] Could not compare embedding "
                f"for '{row[1]}': {error}"
            )

    matches.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return matches[:limit]
def find_semantic_matches(new_embedding, connection):
    """
    Compare a new embedding with existing embeddings.

    Returns items whose similarity is at least SIMILARITY_THRESHOLD.
    """

    rows = connection.execute("""
        SELECT id, term, embedding
        FROM vocabulary_items
        WHERE embedding IS NOT NULL
          AND embedding_model = ?
    """, (EMBEDDING_MODEL,)).fetchall()

    matches = []

    for vocabulary_id, term, stored_embedding in rows:

        try:
            existing_embedding = json.loads(stored_embedding)

            similarity = cosine_similarity(
                new_embedding,
                existing_embedding
            )

            if similarity is None:
                continue

            if similarity >= SIMILARITY_THRESHOLD:
                matches.append({
                    "id": vocabulary_id,
                    "term": term,
                    "similarity": similarity,
                })

        except (json.JSONDecodeError, TypeError, ValueError) as error:
            print(
                f"[WARNING] Could not compare embedding "
                f"for '{term}': {error}"
            )

    matches.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return matches


# ----------------------------------------------------------------------
# Vocabulary
# ----------------------------------------------------------------------

def _increment_existing_item(connection, term, item_type):
    """
    If the term already exists, record another occurrence and
    return its ID. Otherwise return None.
    """

    existing = connection.execute("""
        SELECT id
        FROM vocabulary_items
        WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
          AND item_type = ?
        LIMIT 1
    """, (term, item_type)).fetchone()

    if not existing:
        return None

    vocabulary_id = existing[0]

    connection.execute("""
        UPDATE vocabulary_items
        SET occurrence_count = occurrence_count + 1,
            last_seen_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (vocabulary_id,))

    return vocabulary_id


def save_vocabulary(
    term,
    item_type,
    meaning_ar,
    definition_en=None,
    example=None,
    synonyms=None,
    topic=None,
    source=None,
    grammatical_class=None,
    meaning_en=None,
):
    """
    Save vocabulary items in vocabulary_items.

    For new items:
    1. Generate an embedding.
    2. Compare it with existing embeddings.
    3. Save semantic relationships.
    4. Keep semantically similar expressions as separate items.

    Existing exact matches only increment occurrence_count.
    """

    if item_type not in ALLOWED_ITEM_TYPES:
        raise ValueError(
            f"item_type must be one of: {', '.join(ALLOWED_ITEM_TYPES)}"
        )

    term = term.strip()

    if not term:
        raise ValueError("term cannot be empty.")

    if not meaning_ar or not meaning_ar.strip():
        raise ValueError("meaning_ar cannot be empty.")

    # First, check for an exact existing item
    # (avoids a needless API call for duplicates).
    with get_connection() as connection:
        vocabulary_id = _increment_existing_item(
            connection, term, item_type
        )

    if vocabulary_id is not None:
        return vocabulary_id

    # Generate an embedding for a genuinely new item.
    embedding = None
    embedding_json = None

    try:
        embedding = generate_embedding(term)
        embedding_json = json.dumps(embedding)

        print(f"[EMBEDDING] Generated for: {term}")

    except Exception as error:
        # Do not prevent vocabulary saving if Gemini is unavailable.
        print(
            f"[WARNING] Embedding generation failed for "
            f"'{term}': {error}"
        )

    with get_connection() as connection:

        # Check again in case the item was inserted in the meantime.
        vocabulary_id = _increment_existing_item(
            connection, term, item_type
        )

        if vocabulary_id is not None:
            return vocabulary_id

        # Compare against existing vocabulary before inserting.
        matches = []

        if embedding is not None:
            matches = find_semantic_matches(embedding, connection)

        # Insert the new vocabulary item.
        cursor = connection.execute("""
            INSERT INTO vocabulary_items (
                term,
                item_type,
                grammatical_class,
                meaning_ar,
                meaning_en,
                definition_en,
                example,
                synonyms,
                topic,
                source,
                embedding,
                embedding_model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            term,
            item_type,
            grammatical_class,
            meaning_ar.strip(),
            meaning_en.strip() if meaning_en else None,
            definition_en.strip() if definition_en else None,
            example,
            synonyms,
            topic,
            source,
            embedding_json,
            EMBEDDING_MODEL if embedding is not None else None,
        ))

        vocabulary_id = cursor.lastrowid

        # Save semantic relationships.
        for match in matches:

            similarity = match["similarity"]

            relationship_type = (
                "strong"
                if similarity >= STRONG_SIMILARITY_THRESHOLD
                else "similar"
            )

            connection.execute("""
                INSERT OR IGNORE INTO semantic_relationships (
                    item_id,
                    related_item_id,
                    similarity,
                    relationship_type
                )
                VALUES (?, ?, ?, ?)
            """, (
                vocabulary_id,
                match["id"],
                similarity,
                relationship_type,
            ))

            print(
                f"[SEMANTIC MATCH] {term} <-> {match['term']} "
                f"| Similarity: {similarity:.4f} "
                f"| Type: {relationship_type}"
            )

        print(
            f"[VOCABULARY] Saved '{term}' "
            f"with ID {vocabulary_id}"
        )

        return vocabulary_id


_VOCABULARY_COLUMNS = """
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
    last_reviewed_at,
    grammatical_class,
    meaning_en,
    occurrence_count,
    correct_streak
"""


def get_vocabulary():
    """Retrieve all saved vocabulary items from vocabulary_items."""

    with get_connection() as connection:
        cursor = connection.execute(f"""
            SELECT {_VOCABULARY_COLUMNS}
            FROM vocabulary_items
            ORDER BY id
        """)

        return cursor.fetchall()


def search_vocabulary(term):
    """Search vocabulary items in vocabulary_items."""

    with get_connection() as connection:
        cursor = connection.execute(f"""
            SELECT {_VOCABULARY_COLUMNS}
            FROM vocabulary_items
            WHERE term LIKE ?
            ORDER BY term
        """, (f"%{term.strip()}%",))

        return cursor.fetchall()


def get_semantic_relationships(vocabulary_id):
    """
    Retrieve semantic relationships for a vocabulary item.

    Searches in both directions because a relationship
    is stored from the newly inserted item to an older item.
    """

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                vocabulary_items.id,
                vocabulary_items.term,
                semantic_relationships.similarity,
                semantic_relationships.relationship_type

            FROM semantic_relationships

            JOIN vocabulary_items
                ON vocabulary_items.id =
                    CASE
                        WHEN semantic_relationships.item_id = ?
                        THEN semantic_relationships.related_item_id
                        ELSE semantic_relationships.item_id
                    END

            WHERE semantic_relationships.item_id = ?
               OR semantic_relationships.related_item_id = ?

            ORDER BY semantic_relationships.similarity DESC
        """, (
            vocabulary_id,
            vocabulary_id,
            vocabulary_id,
        )).fetchall()

    return [
        {
            "id": row[0],
            "term": row[1],
            "similarity": row[2],
            "relationship_type": row[3],
        }
        for row in rows
    ]


def update_vocabulary(
    vocabulary_id,
    meaning_ar=None,
    meaning_en=None,
    definition_en=None,
    grammatical_class=None,
    example=None,
    synonyms=None,
    topic=None,
    source=None,
):
    """Update selected information for a vocabulary item."""

    fields = {
        "meaning_ar": meaning_ar,
        "meaning_en": meaning_en,
        "definition_en": definition_en,
        "grammatical_class": grammatical_class,
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
    set_clause += ", updated_at = CURRENT_TIMESTAMP"

    values = list(updates.values())
    values.append(vocabulary_id)

    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE vocabulary_items SET {set_clause} WHERE id = ?",
            values,
        )

        return cursor.rowcount > 0


def delete_vocabulary(vocabulary_id):
    """
    Delete a vocabulary item by its ID,
    together with its semantic relationships (no orphan rows).
    """

    with get_connection() as connection:
        connection.execute("""
            DELETE FROM semantic_relationships
            WHERE item_id = ? OR related_item_id = ?
        """, (vocabulary_id, vocabulary_id))

        cursor = connection.execute(
            "DELETE FROM vocabulary_items WHERE id = ?",
            (vocabulary_id,)
        )

        return cursor.rowcount > 0


if __name__ == "__main__":
    init_db()

    print(f"Database initialized at: {DB_PATH}")

    # Quick manual test. This used to run at import time (before the
    # tables existed, and every time another file imported this module).
    save_vocabulary(
        "deal with difficulties",
        "expression",
        "التعامل مع الصعوبات"
    )

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