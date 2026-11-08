
import os
from dotenv import load_dotenv
from ollama import Client

from memory import search_semantic_vocabulary


import re


# def tokenize_expression(text):
#     """Normalize text into lowercase word tokens."""
#     return re.findall(r"\b[\w']+\b", text.lower())


# def normalize_adaptable_pronouns(tokens):
#     """Normalize possessive pronouns for contextual comparison."""

#     possessive_pronouns = {
#         "my", "your", "his", "her", "its", "our", "their"
#     }

#     return [
#         "<possessive>" if token in possessive_pronouns else token
#         for token in tokens
#     ]


# def contains_token_sequence(answer_tokens, expression_tokens):
#     """Check whether an expression appears as a complete token sequence."""

#     length = len(expression_tokens)

#     return any(
#         answer_tokens[i:i + length] == expression_tokens
#         for i in range(len(answer_tokens) - length + 1)
#     )


# def verify_vocabulary_usage(answer, retrieved_vocabulary):
#     """
#     Verify retrieved vocabulary usage.

#     Categories:
#     1. Exact matches
#     2. Adapted matches (possessive pronoun changes)
#     3. Unused expressions
#     """

#     exact_matches = []
#     adapted_matches = []
#     unused_expressions = []

#     answer_tokens = tokenize_expression(answer)

#     for item in retrieved_vocabulary:

#         term_tokens = tokenize_expression(item["term"])

#         if not term_tokens:
#             unused_expressions.append(item)
#             continue

#         # 1. Exact match
#         if contains_token_sequence(answer_tokens, term_tokens):
#             exact_matches.append(item)
#             continue

#         # 2. Adapted match
#         normalized_term = normalize_adaptable_pronouns(term_tokens)
#         normalized_answer = normalize_adaptable_pronouns(answer_tokens)

#         if contains_token_sequence(
#             normalized_answer,
#             normalized_term
#         ):
#             adapted_matches.append(item)

#         else:
#             unused_expressions.append(item)

#     return {
#         "exact_matches": exact_matches,
#         "adapted_matches": adapted_matches,
#         "unused_expressions": unused_expressions,
#         "total_verified": len(exact_matches) + len(adapted_matches)
#     }

import re


def tokenize_expression(text):
    """Normalize text into lowercase word tokens."""
    return re.findall(r"\b[\w']+\b", text.lower())


def deduplicate_vocabulary(items):
    """
    Remove exact duplicate expressions from retrieved vocabulary.
    Keep the item with the highest similarity score.
    """

    unique = {}
    order = []

    for item in items:
        key = tuple(tokenize_expression(item["term"]))

        if not key:
            continue

        if key not in unique:
            unique[key] = item
            order.append(key)

        elif item.get("similarity", 0) > unique[key].get("similarity", 0):
            unique[key] = item

    return [unique[key] for key in order]


def normalize_adaptable_pronouns(tokens):
    """Normalize possessive pronouns for contextual comparison."""

    possessive_pronouns = {
        "my", "your", "his", "her", "its", "our", "their"
    }

    return [
        "<possessive>" if token in possessive_pronouns else token
        for token in tokens
    ]


def contains_token_sequence(answer_tokens, expression_tokens):
    """Check whether an expression appears as a complete token sequence."""

    length = len(expression_tokens)

    return any(
        answer_tokens[i:i + length] == expression_tokens
        for i in range(len(answer_tokens) - length + 1)
    )


def verify_vocabulary_usage(answer, retrieved_vocabulary):
    """
    Verify actual vocabulary usage.

    EXACT MATCH:
        Expression appears literally.

    ADAPTED MATCH:
        Expression appears with a possessive pronoun change.

    UNUSED:
        Expression does not appear.
    """

    retrieved_vocabulary = deduplicate_vocabulary(
        retrieved_vocabulary
    )

    exact_matches = []
    adapted_matches = []
    unused_expressions = []

    answer_tokens = tokenize_expression(answer)

    normalized_answer = normalize_adaptable_pronouns(
        answer_tokens
    )

    for item in retrieved_vocabulary:

        term_tokens = tokenize_expression(item["term"])

        if not term_tokens:
            continue

        # 1. Exact match
        if contains_token_sequence(answer_tokens, term_tokens):
            exact_matches.append(item)
            continue

        # 2. Adapted match
        normalized_term = normalize_adaptable_pronouns(
            term_tokens
        )

        if contains_token_sequence(
            normalized_answer,
            normalized_term
        ):
            adapted_matches.append(item)

        else:
            unused_expressions.append(item)

    return {
        "exact_matches": exact_matches,
        "adapted_matches": adapted_matches,
        "unused_expressions": unused_expressions,
        "total_verified": (
            len(exact_matches) + len(adapted_matches)
        ),
        "total_unique_retrieved": len(retrieved_vocabulary)
    }

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
# USER_MESSAGE = (
#     "When I present a proposal at work, people sometimes seem "
#     "confused about what I mean. What can I do to make my "
#     "explanations easier to follow?"
# )
USER_MESSAGE = (
    "	Sometimes I struggle to express my opinions when discussing problems with colleagues. How can I improve?"
    
)


# --------------------------------------------------
# 4. Retrieve semantic vocabulary from learner memory
# --------------------------------------------------

# results = search_semantic_vocabulary(USER_MESSAGE, limit=5)

results = search_semantic_vocabulary(USER_MESSAGE, limit=5)

results = deduplicate_vocabulary(results)
if not results:
    raise RuntimeError(
        "No semantic vocabulary was retrieved. "
        "Check your vocabulary database and embeddings."
    )

# lines = [
#     "RELEVANT VOCABULARY FROM THE LEARNER'S MEMORY:",
#     "Use these expressions naturally when relevant.",
#     "Do not force them into the answer."
# ]
lines = [
    "RELEVANT VOCABULARY FROM THE LEARNER'S MEMORY:",
    "These expressions were previously learned by the user.",
    "Try to incorporate at least one expression naturally "
    "when answering, if it fits the context.",
    "Do not use an expression if it sounds unnatural."
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
# 7.1 Verify actual vocabulary usage
# --------------------------------------------------
# --------------------------------------------------
# 7.1 Verify actual vocabulary usage in A and B
# --------------------------------------------------

verification_a = verify_vocabulary_usage(answer_a, results)
verification_b = verify_vocabulary_usage(answer_b, results)


def print_verification_report(label, verification):

    print("\n" + "=" * 60)
    print(label)
    print("=" * 60)

    print("\nEXACT MATCHES:")

    for item in verification["exact_matches"]:
        print(
            f"  [EXACT] {item['term']} "
            f"(similarity: {item['similarity']:.3f})"
        )

    print("\nADAPTED MATCHES:")

    for item in verification["adapted_matches"]:
        print(
            f"  [ADAPTED] {item['term']} "
            f"(similarity: {item['similarity']:.3f})"
        )

    print("\nUNUSED EXPRESSIONS:")

    for item in verification["unused_expressions"]:
        print(
            f"  [UNUSED] {item['term']} "
            f"(similarity: {item['similarity']:.3f})"
        )

    print("\n" + "-" * 60)

    print("Total retrieved expressions:", 
          len(results))

    print("Exact matches:",
          len(verification["exact_matches"]))

    print("Adapted matches:",
          len(verification["adapted_matches"]))

    print("Unused expressions:",
          len(verification["unused_expressions"]))

    print("Total verified expressions:",
          verification["total_verified"])

    print("=" * 60)


print_verification_report(
    "A — VOCABULARY USAGE WITHOUT SEMANTIC MEMORY",
    verification_a
)

print_verification_report(
    "B — VOCABULARY USAGE WITH SEMANTIC MEMORY",
    verification_b
)

# --------------------------------------------------
# 8. Final comparison
# --------------------------------------------------

# --------------------------------------------------
# 8. Final A/B comparison
# --------------------------------------------------

print("\n\n" + "=" * 60)
print("A/B SEMANTIC VOCABULARY COMPARISON")
print("=" * 60)

for item in results:

    term = item["term"]

    def get_status(verification, term):

        if any(
            x["term"] == term
            for x in verification["exact_matches"]
        ):
            return "EXACT MATCH"

        if any(
            x["term"] == term
            for x in verification["adapted_matches"]
        ):
            return "ADAPTED MATCH"

        return "NOT USED"

    status_a = get_status(verification_a, term)
    status_b = get_status(verification_b, term)

    print(f"\nExpression: {term}")
    print(f"Without memory (A): {status_a}")
    print(f"With memory (B):    {status_b}")

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)

print(
    "Verified without memory (A):",
    verification_a["total_verified"]
)

print(
    "Verified with memory (B):",
    verification_b["total_verified"]
)

print(
    "Vocabulary retrieved from database:",
    len(results)
)

print("\nSame model:", MODEL)
print("Same user message:", USER_MESSAGE)
print("Semantic memory included in B: True")
print("Database modified by this test: No")
print("Vocabulary extraction performed: No")

print("\nA/B TEST COMPLETED")
print("=" * 60)
