
# # import os
# # import json
# # import sqlite3
# # from dotenv import load_dotenv
# # from google import genai

# # load_dotenv(override=True)

# # key = os.getenv("GEMINI_API_KEY")

# # if not key:
# #     raise ValueError("GEMINI_API_KEY not found")

# # client = genai.Client(api_key=key)

# # MODEL = "gemini-embedding-001"

# # conn = sqlite3.connect("learner_memory.db")
# # cursor = conn.cursor()

# # cursor.execute("""
# # SELECT id, term
# # FROM vocabulary_items
# # WHERE embedding IS NULL OR embedding = ''
# # ORDER BY id
# # """)

# # items = cursor.fetchall()

# # print("Vocabulary items to process:", len(items))

# # success = 0

# # try:
# #     for item_id, term in items:
# #         result = client.models.embed_content(
# #             model=MODEL,
# #             contents=term
# #         )

# #         embedding = result.embeddings[0].values

# #         cursor.execute("""
# #             UPDATE vocabulary_items
# #             SET embedding = ?,
# #                 embedding_model = ?
# #             WHERE id = ?
# #         """, (
# #             json.dumps(embedding),
# #             MODEL,
# #             item_id
# #         ))

# #         conn.commit()
# #         success += 1

# #         print(f"[{success}/{len(items)}] Embedded: {term}")

# # except Exception as e:
# #     print("Error:", e)

# # finally:
# #     conn.close()

# # print("Successfully processed:", success)













































# import os
# import json
# import sqlite3
# from dotenv import load_dotenv
# from google import genai


# load_dotenv(override=True)

# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# MODEL = "gemini-embedding-001"

# DB_PATH = "learner_memory.db"

# term = "overcome obstacles"

# # 1. Generate embedding
# result = client.models.embed_content(
#     model=MODEL,
#     contents=term
# )

# embedding = result.embeddings[0].values

# # 2. Save embedding in the database
# with sqlite3.connect(DB_PATH) as conn:
#     cursor = conn.cursor()

#     cursor.execute("""
#         SELECT id FROM vocabulary_items
#         WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
#         LIMIT 1
#     """, (term,))

#     row = cursor.fetchone()

#     if row:
#         cursor.execute("""
#             UPDATE vocabulary_items
#             SET embedding = ?, embedding_model = ?
#             WHERE id = ?
#         """, (json.dumps(embedding), MODEL, row[0]))

#         conn.commit()
#         print("Embedding saved for:", term)
#     else:
#         print("Vocabulary item not found:", term)

# # 3. Verify
# with sqlite3.connect(DB_PATH) as conn:
#     row = conn.execute("""
#         SELECT term, LENGTH(embedding), embedding_model
#         FROM vocabulary_items
#         WHERE LOWER(TRIM(term)) = LOWER(TRIM(?))
#         LIMIT 1
#     """, (term,)).fetchone()

#     print("Verification:", row)








































































import os
import json
import sqlite3
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

MODEL = "gemini-embedding-001"
DB_PATH = "learner_memory.db"


def generate_missing_embeddings():

    success = 0
    failed = 0

    with sqlite3.connect(DB_PATH) as conn:

        cursor = conn.cursor()

        # Retrieve only vocabulary items without embeddings
        cursor.execute("""
            SELECT id, term
            FROM vocabulary_items
            WHERE embedding IS NULL OR embedding = ''
            ORDER BY id
        """)

        items = cursor.fetchall()

        print("Vocabulary items to process:", len(items))

        if not items:
            print("All vocabulary items already have embeddings.")
            return

        for index, (item_id, term) in enumerate(items, start=1):

            try:
                # Generate embedding
                result = client.models.embed_content(
                    model=MODEL,
                    contents=term
                )

                embedding = result.embeddings[0].values

                if not embedding:
                    raise ValueError("Empty embedding returned")

                # Save without overwriting existing embeddings
                cursor.execute("""
                    UPDATE vocabulary_items
                    SET embedding = ?,
                        embedding_model = ?
                    WHERE id = ?
                    AND (embedding IS NULL OR embedding = '')
                """, (
                    json.dumps(embedding),
                    MODEL,
                    item_id
                ))

                conn.commit()

                if cursor.rowcount > 0:
                    success += 1
                    print(
                        f"[{index}/{len(items)}] "
                        f"Embedded: {term}"
                    )

            except Exception as e:
                failed += 1
                print(f"Failed: {term} | Error: {e}")

    print("\n========== RESULTS ==========")
    print("Successfully processed:", success)
    print("Failed:", failed)


if __name__ == "__main__":
    generate_missing_embeddings()
