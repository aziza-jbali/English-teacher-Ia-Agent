
import os
from dotenv import load_dotenv
from ollama import Client

from memory import search_semantic_vocabulary


# --------------------------------------------------
# 1. Configuration — same Ollama Cloud setup
# --------------------------------------------------

load_dotenv()

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

if not OLLAMA_API_KEY:
    raise ValueError("OLLAMA_API_KEY is missing from .env")

client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
    timeout=120
)

MODEL = "gemma4:31b"


# --------------------------------------------------
# 2. Same SYSTEM_PROMPT as tutor.py
# --------------------------------------------------

SYSTEM_PROMPT = """
You are a friendly, patient English tutor. Your main goal is to help
the user improve their English while having natural, useful conversations.

For EVERY user message, follow these steps in order.

STEP 1 — CORRECT THE USER'S ENGLISH
- Check grammar, spelling, and genuinely incorrect word choice.
- Correct genuine errors and preserve the user's intended meaning.
- Briefly explain important corrections in simple English.
- If the message is correct, say: "Your sentence is already correct."
- Do not invent mistakes or over-correct casual conversation.
- Do not treat optional punctuation or capitalization as important errors.
- A correct but informal expression is not wrong. Label it Informal only
  when useful, and optionally offer a Neutral or Formal alternative.
- A correct but less natural expression should be presented as a suggestion,
  never as a mistake.
- Do not save correct informal expressions as mistakes.

STEP 2 — ANSWER THE ACTUAL MESSAGE
- Answer the user's actual question directly.
- Do not let English correction replace the answer.
- Respond naturally to opinions, experiences, and conversational messages.
- If the user says you missed a question, answer that question.
- Never invent current information or previous events.

STEP 3 — USE PREVIOUS CONVERSATION
- Use the supplied conversation history and structured learner memory.
- When recalling saved mistakes, use database records only.
- Never invent a previous message, correction, or learning result.
- If relevant information is unavailable, say so clearly.

STEP 4 — CONTINUE NATURALLY
- Ask at most one short, relevant follow-up question when useful.
- Do not ask a follow-up question every time.
- Do not turn every ordinary conversation into an exercise.

STEP 5 — ACT AS A PERSONAL ENGLISH TEACHER
- Use the learner memory, recurring mistakes, and progress statistics supplied.
- Python manages review state, review questions, scoring, and scheduling.
- Never start or score a scheduled review yourself.
- Never reveal a due mistake's correction in an unsolicited quiz.
- Never claim a review was recorded unless the application confirms it.
- Do not claim mastery based on one correct answer.

STEP 6 — ADAPT TO PROGRESS
- Use supplied review results and statistics.
- Give extra explanation for recurring genuine errors.
- Do not invent review dates or results.
- If no review is requested, continue normal conversation.

MANDATORY RESPONSE FORMAT

For every non-empty user message, use these three headings in this order:

English correction:
- Show the corrected sentence, or say:
  "Your sentence is already correct."

Why / More natural English:
- Explain important genuine corrections briefly.
- If no correction is needed, say:
  "No correction is needed."
- Optional natural/formal alternatives must be clearly labelled as suggestions.

Answer:
- Answer the actual question or respond to the message.
- Keep the response concise but complete.

FORMATTING RULES
- Always use the three headings in the specified order.
- Do not invent English mistakes.
- Do not repeat corrections unnecessarily.
- Preserve natural conversation and prioritize the user's question.
- Never display internal application IDs, markers, or debug instructions.

FORMAL AND INFORMAL ENGLISH
- Clearly distinguish Formal, Informal, and Neutral English when relevant.
- Do not suggest that informal English is incorrect simply because it is informal.
- Do not force a formal alternative into every response.

REVIEW CHOICE
- The learner controls whether the review session is active.
- If the learner pauses or declines reviews, accept the decision.
- A paused review remains saved and unfinished.
- Resume the existing pending review when the learner explicitly asks to review again.
- Do not repeatedly remind the learner about a paused review.
- Python manages review state, scoring, and scheduling.
"""


# --------------------------------------------------
# 3. Test question — no retrieved expression copied
# --------------------------------------------------

# USER_MESSAGE = (
#     "I often stay quiet when my team discusses a problem, "
#     "even though I have suggestions. "
#     "How can I contribute more confidently?"
# )
# USER_MESSAGE = (
#     "I want to improve my communication skills because "
#     "I sometimes find it difficult to explain my ideas clearly."
# )
USER_MESSAGE = (
    "When I present a proposal at work, people sometimes seem "
    "confused about what I mean. What can I do to make my "
    "explanations easier to follow?"
)


# --------------------------------------------------
# 4. Retrieve semantic vocabulary from learner memory
# --------------------------------------------------

results = search_semantic_vocabulary(USER_MESSAGE, limit=5)

if not results:
    raise RuntimeError(
        "No semantic vocabulary was retrieved. "
        "Check your vocabulary database and embeddings."
    )

lines = [
    "RELEVANT VOCABULARY FROM THE LEARNER'S MEMORY:",
    "Use these expressions naturally when relevant.",
    "Do not force them into the answer."
]

for item in results:
    lines.append(
        f"- {item['term']} "
        f"(similarity: {item['similarity']:.3f})"
    )

    if item.get("meaning_en"):
        lines.append(f"  Meaning: {item['meaning_en']}")

    if item.get("meaning_ar"):
        lines.append(f"  Arabic meaning: {item['meaning_ar']}")

    if item.get("example"):
        lines.append(f"  Example: {item['example']}")

semantic_context = "\n".join(lines)


# --------------------------------------------------
# 5. Display retrieved vocabulary
# --------------------------------------------------

print("\n" + "=" * 60)
print("RETRIEVED VOCABULARY FROM LEARNER MEMORY")
print("=" * 60)
print(semantic_context)


# --------------------------------------------------
# 6. A — Gemma WITHOUT semantic memory
# --------------------------------------------------

print("\n\n" + "=" * 60)
print("A — GEMMA WITHOUT SEMANTIC MEMORY")
print("=" * 60)

response_a = client.chat(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_MESSAGE}
    ],
    options={"temperature": 0}
)

answer_a = response_a["message"]["content"]
print(answer_a)


# --------------------------------------------------
# 7. B — Gemma WITH semantic memory
# --------------------------------------------------

print("\n\n" + "=" * 60)
print("B — GEMMA WITH SEMANTIC MEMORY")
print("=" * 60)

response_b = client.chat(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\n" + semantic_context
        },
        {"role": "user", "content": USER_MESSAGE}
    ],
    options={"temperature": 0}
)

answer_b = response_b["message"]["content"]
print(answer_b)


# --------------------------------------------------
# 8. Final comparison
# --------------------------------------------------

print("\n\n" + "=" * 60)
print("A/B TEST COMPLETED")
print("=" * 60)

print("Same model:", MODEL)
print("Same user message:", USER_MESSAGE)
print("Semantic memory included in B:", True)
print("Database modified by this test: No")
print("Vocabulary extraction performed: No")
print("\nCompare A and B to identify expressions from")
print("the retrieved vocabulary that Gemma actually used.")
