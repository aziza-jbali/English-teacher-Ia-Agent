# import os
# import json
# import sqlite3

# from dotenv import load_dotenv
# from ollama import Client
# import memory

# load_dotenv()

# # 1. Search semantically for related vocabulary
# query = "communicate effectively with colleagues"
# query_embedding = memory.generate_embedding(query)

# conn = sqlite3.connect(memory.DB_PATH)

# rows = conn.execute(
#     """
#     SELECT id, term, meaning_en, meaning_ar, embedding
#     FROM vocabulary_items
#     WHERE embedding IS NOT NULL AND embedding_model = ?
#     """,
#     (memory.EMBEDDING_MODEL,)
# ).fetchall()

# scores = []

# for row in rows:
#     item_id, term, meaning_en, meaning_ar, embedding = row

#     similarity = memory.cosine_similarity(
#         query_embedding,
#         json.loads(embedding)
#     )

#     if similarity is not None and similarity >= memory.SIMILARITY_THRESHOLD:
#         scores.append((item_id, term, meaning_en, meaning_ar, similarity))

# conn.close()

# scores.sort(key=lambda x: x[4], reverse=True)
# matches = scores[:5]

# print("\nRetrieved vocabulary:")
# for item in matches:
#     print(item[1], round(item[4], 4))

# # 2. Build context for Gemma
# vocabulary_context = "\n".join(
#     f"- {term}: {meaning_en or meaning_ar or 'Meaning unavailable'}"
#     for _, term, meaning_en, meaning_ar, _ in matches
# )

# # 3. Ask Gemma to use the retrieved vocabulary
# client = Client(
#     host="https://ollama.com",
#     headers={"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"},
#     timeout=120,
# )

# response = client.chat(
#     model="gemma4:31b",
#     messages=[
#         {
#             "role": "system",
#             "content": (
#                 "You are an English tutor. Use the learner's previously "
#                 "learned vocabulary when relevant. Do not force unrelated words."
#             ),
#         },
#         {
#             "role": "system",
#             "content": "Previously learned vocabulary:\n" + vocabulary_context,
#         },
#         {
#             "role": "user",
#             "content": (
#                 "I want to communicate effectively with my colleagues. "
#                 "Help me express this idea naturally in English."
#             ),
#         },
#     ],
# )

# print("\nGemma response:")
# print(response.message.content)


































from memory import search_semantic_vocabulary

results = search_semantic_vocabulary(
    "improve the way I communicate with people"
)

print("\nSemantic search results:\n")

for item in results:
    print(
        item["term"],
        "| Similarity:",
        round(item["similarity"], 4)
    )