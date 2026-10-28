# # SQLite is already included in Python,
# # so you don't need to install anything.
# # Now we want to add persistent memory, so your tutor can remember your English mistakes between sessions. hata ki tsaker el system w tkol goodbye w tarja7 ydhaker conversation mabin el session 
# import sqlite3
# from pathlib import Path

# # Keep the database in the project folder
# DB_PATH = Path(__file__).parent / "learner_memory.db"

# print("hello")
# def init_db():
#     """Create the database table if it doesn't exist."""

#     with sqlite3.connect(DB_PATH) as connection:
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


# def save_mistake(original, correction, explanation, category):
#     """Save a learner's English mistake."""

#     with sqlite3.connect(DB_PATH) as connection:
#         connection.execute("""
#             INSERT INTO mistakes (
#                 original_sentence,
#                 correction,
#                 explanation,
#                 category
#             )
#             VALUES (?, ?, ?, ?)
#         """, (original, correction, explanation, category))


# def get_mistakes():
#     """Return all saved mistakes."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT id, original_sentence, correction,
#                    explanation, category, created_at
#             FROM mistakes
#             ORDER BY id
#         """)

#         return cursor.fetchall()
# #  static data

# if __name__ == "__main__":
#     init_db() # we 're calling this data base hadi da5lha instructions maktobin bel language SQL el role c est cree une base de donnes s appelle mistakes pour sauvgarder 
#     print(f"Database initialized at: {DB_PATH}")
#     print("STEP 1: Reached the save section")

#     # save_mistake(
#     #     "I am agree with you",
#     #     "I agree with you",
#     #     "We do not use 'am' before the verb agree.",
#     #     "grammar"
#     # )

#     print("STEP 2: Mistake saved")

#     print(get_mistakes())
#     print("STEP 3: Retrieved mistakes")
# # il permet d afficher un message dans terminal grace f on peut faire conncatination entre string et variable
# # RQ: if __name__ == "__main__": ya3ni idha ktebt python memory.py w 3mlt run lel file memory .py raho , el code eli ta7to bach ytnafedh ama moch ya3ni ki bach na3mel import ll memory.py w na3mel run lel tutor.py raho moch yetnafedh lazm en  rani memory.py"













































































# import sqlite3
# from pathlib import Path

# # Store the database in the same folder as this file
# DB_PATH = Path(__file__).parent / "learner_memory.db"


# def init_db():
#     """Create the database tables if they do not already exist."""
#     with sqlite3.connect(DB_PATH) as connection:

#         # Table for English mistakes
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

#         # Table for conversation history
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS conversations (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 role TEXT NOT NULL,
#                 content TEXT NOT NULL,
#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP
#             )
#         """)


# def save_mistake(original, correction, explanation, category):
#     """Save an English mistake in the database."""
#     with sqlite3.connect(DB_PATH) as connection:
#         connection.execute("""
#             INSERT INTO mistakes (
#                 original_sentence,
#                 correction,
#                 explanation,
#                 category
#             )
#             VALUES (?, ?, ?, ?)
#         """, (original, correction, explanation, category))


# def get_mistakes():
#     """Retrieve all saved English mistakes."""
#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT id, original_sentence, correction,
#                    explanation, category, created_at
#             FROM mistakes
#             ORDER BY id
#         """)
#         return cursor.fetchall()


# def save_message(role, content):
#     """Save one message from the user or the tutor."""
#     with sqlite3.connect(DB_PATH) as connection:
#         connection.execute("""
#             INSERT INTO conversations (role, content)
#             VALUES (?, ?)
#         """, (role, content))


# def get_chat_history(limit=30):
#     """Retrieve the most recent messages in chronological order."""
#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT role, content
#             FROM conversations
#             ORDER BY id DESC
#             LIMIT ?
#         """, (limit,))

#         # SQL returns newest first; reverse the list for the chatbot
#         return list(reversed(cursor.fetchall()))


# if __name__ == "__main__":
#     init_db()
#     print(f"Database initialized at: {DB_PATH}")

#     print("\nSaved English mistakes:")
#     for mistake in get_mistakes():
#         print(mistake)

#     print("\nRecent conversation:")
#     for message in get_chat_history():
#         print(message)


































































# import sqlite3
# from pathlib import Path
# from datetime import datetime, timedelta


# # Store the database in the same folder as this file
# DB_PATH = Path(__file__).parent / "learner_memory.db"


# # Review intervals, in days
# REVIEW_INTERVALS = [1, 3, 7, 14, 40]


# def init_db():
#     """Create tables and prepare existing mistakes for review."""

#     with sqlite3.connect(DB_PATH) as connection:

#         # Store English mistakes
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

#         # Store conversation history
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS conversations (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 role TEXT NOT NULL,
#                 content TEXT NOT NULL,
#                 created_at TEXT DEFAULT CURRENT_TIMESTAMP
#             )
#         """)

#         # Track each mistake's review schedule and progress
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS mistake_review_state (
#                 mistake_id INTEGER PRIMARY KEY,
#                 next_review_at TEXT NOT NULL,
#                 interval_days INTEGER NOT NULL DEFAULT 1,
#                 review_count INTEGER NOT NULL DEFAULT 0,
#                 correct_count INTEGER NOT NULL DEFAULT 0,
#                 last_reviewed_at TEXT,
#                 FOREIGN KEY (mistake_id) REFERENCES mistakes(id)
#             )
#         """)

#         # Record every review attempt
#         connection.execute("""
#             CREATE TABLE IF NOT EXISTS review_attempts (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 mistake_id INTEGER NOT NULL,
#                 was_correct INTEGER NOT NULL
#                     CHECK (was_correct IN (0, 1)),
#                 attempted_at TEXT DEFAULT CURRENT_TIMESTAMP,
#                 FOREIGN KEY (mistake_id) REFERENCES mistakes(id)
#             )
#         """)

#         # Schedule previously saved mistakes that have no review state.
#         # Existing review schedules and progress are left unchanged.
#         first_review = (
#             datetime.now() + timedelta(days=1)
#         ).strftime("%Y-%m-%d %H:%M:%S")

#         connection.execute("""
#             INSERT INTO mistake_review_state (
#                 mistake_id,
#                 next_review_at,
#                 interval_days
#             )
#             SELECT id, ?, 1
#             FROM mistakes
#             WHERE id NOT IN (
#                 SELECT mistake_id
#                 FROM mistake_review_state
#             )
#         """, (first_review,))


# def save_mistake(original, correction, explanation, category):
#     """Save a mistake and schedule its first review."""

#     with sqlite3.connect(DB_PATH) as connection:

#         cursor = connection.execute("""
#             INSERT INTO mistakes (
#                 original_sentence,
#                 correction,
#                 explanation,
#                 category
#             )
#             VALUES (?, ?, ?, ?)
#         """, (original, correction, explanation, category))

#         mistake_id = cursor.lastrowid

#         next_review = (
#             datetime.now() + timedelta(days=1)
#         ).strftime("%Y-%m-%d %H:%M:%S")

#         connection.execute("""
#             INSERT INTO mistake_review_state (
#                 mistake_id,
#                 next_review_at,
#                 interval_days
#             )
#             VALUES (?, ?, 1)
#         """, (mistake_id, next_review))

#         return mistake_id


# def get_mistakes():
#     """Retrieve all saved English mistakes."""

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


# def get_mistake_summary():
#     """Count saved mistakes by category."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 COALESCE(
#                     NULLIF(TRIM(category), ''),
#                     'Uncategorized'
#                 ) AS category,
#                 COUNT(*) AS total
#             FROM mistakes
#             GROUP BY COALESCE(
#                 NULLIF(TRIM(category), ''),
#                 'Uncategorized'
#             )
#             ORDER BY total DESC
#         """)

#         return cursor.fetchall()


# def get_recurring_mistakes(min_occurrences=2):
#     """Find identical original sentences saved multiple times."""

#     if min_occurrences < 2:
#         raise ValueError("min_occurrences must be at least 2")

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 original_sentence,
#                 correction,
#                 category,
#                 COUNT(*) AS occurrences
#             FROM mistakes
#             GROUP BY original_sentence COLLATE NOCASE
#             HAVING COUNT(*) >= ?
#             ORDER BY occurrences DESC
#         """, (min_occurrences,))

#         return cursor.fetchall()


# def schedule_review(mistake_id, interval_days=1):
#     """Schedule an existing mistake for a future review."""

#     if interval_days < 1:
#         raise ValueError("interval_days must be at least 1")

#     next_review = (
#         datetime.now() + timedelta(days=interval_days)
#     ).strftime("%Y-%m-%d %H:%M:%S")

#     with sqlite3.connect(DB_PATH) as connection:

#         mistake = connection.execute("""
#             SELECT id
#             FROM mistakes
#             WHERE id = ?
#         """, (mistake_id,)).fetchone()

#         if mistake is None:
#             raise ValueError(
#                 f"Mistake {mistake_id} does not exist"
#             )

#         connection.execute("""
#             INSERT INTO mistake_review_state (
#                 mistake_id,
#                 next_review_at,
#                 interval_days
#             )
#             VALUES (?, ?, ?)
#             ON CONFLICT(mistake_id) DO UPDATE SET
#                 next_review_at = excluded.next_review_at,
#                 interval_days = excluded.interval_days
#         """, (mistake_id, next_review, interval_days))


# def get_due_reviews(limit=5):
#     """Retrieve mistakes whose scheduled review time has arrived."""

#     if limit < 1:
#         raise ValueError("limit must be at least 1")

#     now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 m.id,
#                 m.original_sentence,
#                 m.correction,
#                 m.explanation,
#                 m.category,
#                 s.interval_days,
#                 s.review_count,
#                 s.correct_count,
#                 s.next_review_at
#             FROM mistakes AS m
#             JOIN mistake_review_state AS s
#                 ON m.id = s.mistake_id
#             WHERE s.next_review_at <= ?
#             ORDER BY s.next_review_at ASC
#             LIMIT ?
#         """, (now, limit))

#         return cursor.fetchall()


# def record_review(mistake_id, was_correct):
#     """
#     Record a review result and calculate the next review date.

#     Correct answer:
#         Move to the next interval: 1, 3, 7, 14, 40 days.

#     Incorrect answer:
#         Reset the next interval to 1 day.
#     """

#     if not isinstance(was_correct, bool):
#         raise ValueError("was_correct must be True or False")

#     now = datetime.now()
#     now_text = now.strftime("%Y-%m-%d %H:%M:%S")

#     with sqlite3.connect(DB_PATH) as connection:

#         state = connection.execute("""
#             SELECT interval_days
#             FROM mistake_review_state
#             WHERE mistake_id = ?
#         """, (mistake_id,)).fetchone()

#         if state is None:
#             raise ValueError(
#                 "No review schedule exists for this mistake. "
#                 "Call schedule_review() first."
#             )

#         current_interval = state[0]

#         if was_correct:
#             next_interval = next(
#                 (
#                     days for days in REVIEW_INTERVALS
#                     if days > current_interval
#                 ),
#                 REVIEW_INTERVALS[-1]
#             )
#         else:
#             next_interval = REVIEW_INTERVALS[0]

#         next_review = (
#             now + timedelta(days=next_interval)
#         ).strftime("%Y-%m-%d %H:%M:%S")

#         # Save this individual attempt
#         connection.execute("""
#             INSERT INTO review_attempts (
#                 mistake_id,
#                 was_correct,
#                 attempted_at
#             )
#             VALUES (?, ?, ?)
#         """, (mistake_id, int(was_correct), now_text))

#         # Update the learning progress
#         connection.execute("""
#             UPDATE mistake_review_state
#             SET next_review_at = ?,
#                 interval_days = ?,
#                 review_count = review_count + 1,
#                 correct_count = correct_count + ?,
#                 last_reviewed_at = ?
#             WHERE mistake_id = ?
#         """, (
#             next_review,
#             next_interval,
#             int(was_correct),
#             now_text,
#             mistake_id
#         ))

#         return {
#             "mistake_id": mistake_id,
#             "was_correct": was_correct,
#             "next_interval_days": next_interval,
#             "next_review_at": next_review
#         }


# def get_review_progress(mistake_id):
#     """Retrieve the review progress for one mistake."""

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT
#                 m.original_sentence,
#                 m.correction,
#                 s.interval_days,
#                 s.review_count,
#                 s.correct_count,
#                 s.last_reviewed_at,
#                 s.next_review_at
#             FROM mistakes AS m
#             JOIN mistake_review_state AS s
#                 ON m.id = s.mistake_id
#             WHERE m.id = ?
#         """, (mistake_id,))

#         return cursor.fetchone()


# def save_message(role, content):
#     """Save one message from the user or the tutor."""

#     with sqlite3.connect(DB_PATH) as connection:
#         connection.execute("""
#             INSERT INTO conversations (role, content)
#             VALUES (?, ?)
#         """, (role, content))


# def get_chat_history(limit=30):
#     """Retrieve recent messages in chronological order."""

#     if limit < 1:
#         raise ValueError("limit must be at least 1")

#     with sqlite3.connect(DB_PATH) as connection:
#         cursor = connection.execute("""
#             SELECT role, content
#             FROM conversations
#             ORDER BY id DESC
#             LIMIT ?
#         """, (limit,))

#         return list(reversed(cursor.fetchall()))


# if __name__ == "__main__":
#     init_db()

#     print(f"Database: {DB_PATH}")
#     print("\nSaved English mistakes:")

#     for mistake in get_mistakes():
#         print(mistake)

#     print("\nMistake summary by category:")

#     for category, total in get_mistake_summary():
#         print(f"{category}: {total}")

#     print("\nRecurring mistakes:")

#     for original, correction, category, count in (
#         get_recurring_mistakes()
#     ):
#         print(
#             f"{original} -> {correction} "
#             f"[{category}] ({count} occurrences)"
#         )

#     print("\nReviews currently due:")

#     for review in get_due_reviews():
#         print(review)

#     print("\nRecent conversation:")

#     for message in get_chat_history():
#         print(message)



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
