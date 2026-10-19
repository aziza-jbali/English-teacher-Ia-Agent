# SQLite is already included in Python,
# so you don't need to install anything.
# Now we want to add persistent memory, so your tutor can remember your English mistakes between sessions. hata ki tsaker el system w tkol goodbye w tarja7 ydhaker conversation mabin el session 
import sqlite3
from pathlib import Path

# Keep the database in the project folder
DB_PATH = Path(__file__).parent / "learner_memory.db"


def init_db():
    """Create the database table if it doesn't exist."""

    with sqlite3.connect(DB_PATH) as connection:
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


def save_mistake(original, correction, explanation, category):
    """Save a learner's English mistake."""

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO mistakes (
                original_sentence,
                correction,
                explanation,
                category
            )
            VALUES (?, ?, ?, ?)
        """, (original, correction, explanation, category))


def get_mistakes():
    """Return all saved mistakes."""

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute("""
            SELECT id, original_sentence, correction,
                   explanation, category, created_at
            FROM mistakes
            ORDER BY id
        """)

        return cursor.fetchall()
# static data
# save_mistake(
#     "I am agree with you",
#     "I agree with you",
#     "We do not use 'am' before the verb agree.",
#     "grammar"
# )
   
# print(get_mistakes())

if __name__ == "__main__":
    init_db() # we 're calling this data base hadi da5lha instructions maktobin bel language SQL el role c est cree une base de donnes s appelle mistakes pour sauvgarder 
    print(f"Database initialized at: {DB_PATH}")# il permet d afficher un message dans terminal grace f on peut faire conncatination entre string et variable
# RQ: if __name__ == "__main__": ya3ni idha ktebt python memory.py w 3mlt run lel file memory .py raho , el code eli ta7to bach ytnafedh ama moch ya3ni ki bach na3mel import ll memory.py w na3mel run lel tutor.py raho moch yetnafedh lazm en  rani memory.py"