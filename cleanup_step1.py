"""
One-time cleanup after Step 1. Run ONCE, next to memory.py:

    python cleanup_step1.py

It will:
  1. Back up learner_memory.db to learner_memory_backup.db
  2. Merge duplicate mistakes (keeps one row, sums occurrence_count)
  3. Delete trivial "mistakes" (only capitalization/punctuation/spacing)
  4. Reset review statistics corrupted by the old scoring bug
  5. Clear the pending review
"""
import shutil
import sqlite3
from datetime import datetime

from memory import init_db, merge_duplicate_mistakes, DB_PATH, _normalize

backup_path = DB_PATH.with_name("learner_memory_backup.db")
if backup_path.exists():
    print(f"Backup already exists ({backup_path.name}); keeping the OLD backup.")
else:
    shutil.copy(DB_PATH, backup_path)
    print(f"Backup created: {backup_path.name}")

# 2) Merge duplicates
init_db()
print("Removed duplicates:", merge_duplicate_mistakes())

with sqlite3.connect(DB_PATH) as c:
    # 3) Delete trivial rows: original and correction are identical once
    #    case, spaces and punctuation are ignored.
    trivial_ids = [
        row[0]
        for row in c.execute("SELECT id, original_sentence, correction FROM mistakes")
        if _normalize(row[1]) == _normalize(row[2])
    ]
    for mistake_id in trivial_ids:
        c.execute("DELETE FROM mistakes WHERE id = ?", (mistake_id,))
    print("Deleted trivial rows (IDs):", trivial_ids)

    # 4) Reset review stats; make everything due now so you can test reviews.
    now = datetime.now().replace(microsecond=0).isoformat(sep=" ")
    c.execute("""
        UPDATE mistakes
        SET review_count = 0, correct_count = 0, wrong_count = 0,
            correct_streak = 0, last_reviewed_at = NULL,
            last_review_result = NULL, next_review_at = ?
    """, (now,))

    # 5) Clear the pending review (table may not exist yet on a fresh DB)
    try:
        c.execute("UPDATE tutor_state SET value = '' WHERE key = 'active_review_id'")
    except sqlite3.OperationalError:
        pass

    c.commit()

print("\nMistakes now in the database:")
with sqlite3.connect(DB_PATH) as c:
    for row in c.execute(
        "SELECT id, original_sentence, correction, occurrence_count FROM mistakes"
    ):
        print(row)
