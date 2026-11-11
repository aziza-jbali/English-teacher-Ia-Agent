import os
import json
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from ollama import Client

from memory import (
    init_db,
    save_message,
    get_chat_history,
    save_mistake,
    get_mistakes,
    get_due_mistakes,
    record_review_result,
    get_learning_stats,
    get_recurring_mistakes,  # Added for Phase 3 personalization
    save_vocabulary,
    get_vocabulary,
    search_vocabulary,
    update_vocabulary,
    delete_vocabulary,
    search_semantic_vocabulary,
    get_vocabulary_by_topic,  # NEW: same-topic vocabulary lookup
)


# ============================================================
# 1. CONNECT TO OLLAMA CLOUD
# ============================================================

load_dotenv()
api_key = os.getenv("OLLAMA_API_KEY")

if not api_key:
    raise RuntimeError("OLLAMA_API_KEY not found. Check your .env file.")

client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=120,
)

MODEL = "gemma4:31b"
DB_PATH = Path(__file__).parent / "learner_memory.db"


def extract_vocabulary(text, source):
    """
    Extract up to 5 useful English vocabulary items
    from learner or tutor messages.
    """

    prompt = f"""
    You are an experienced English vocabulary teacher.
    Your task is to identify genuinely useful vocabulary
    that helps an English learner improve their language.

    Message source: {source}
    Message: {text}

    STRICT SELECTION RULES:

    1. Extract only vocabulary that actually appears
       in the message. Never invent terms.

    2. Prioritize:
       - Intermediate and advanced vocabulary.
       - Useful phrasal verbs.
       - Common and meaningful collocations.
       - Idioms and figurative expressions.
       - Natural expressions useful in real conversations.
       - Technical or professional vocabulary.

    3. DO NOT extract basic or obvious language, including:
       - Greetings: hello, hi, hey there, good morning.
       - Simple polite expressions: thank you, please, you're welcome.
       - Basic everyday words: good, nice, happy, sad, big, small.
       - Simple conversational phrases: how are you, see you later.
       - Basic words that an English learner is very likely
         to know already.

    4. Do not save a word or expression simply because
       it appears in the message.
       It must have genuine learning value.

    5. Prefer vocabulary at approximately B1 level or above.
       However, a lower-level word may be selected if it has
       important technical, professional, or contextual value.

    6. Do not classify every multi-word item as an expression.
       Use the most accurate category.

    7. Select from these five item types ONLY:
       - word
       - expression
       - phrasal verb
       - idiom
       - collocation

    8. Provide the grammatical class:
       noun, verb, adjective, adverb, noun phrase,
       verb phrase, adjective phrase, etc.

    9. Provide both Arabic and English meanings.

    10. Provide a clear English definition.

    11. Provide a natural example sentence.

    12. Provide useful synonyms and a relevant topic.

    13. Avoid duplicate terms and basic vocabulary.

    14. Return fewer than 5 items if necessary.
        If the message contains no genuinely useful vocabulary,
        return an empty vocabulary array.

    Return ONLY valid JSON in this format:

    {{
        "vocabulary": [
            {{
                "term": "overcome obstacles",
                "item_type": "collocation",
                "grammatical_class": "verb phrase",
                "meaning_ar": "التغلب على العقبات",
                "meaning_en": "To successfully deal with difficulties",
                "definition_en": "To succeed in dealing with problems or challenges.",
                "example": "She managed to overcome several obstacles.",
                "synonyms": "surmount difficulties, get past challenges",
                "topic": "Personal Development"
            }}
        ]
    }}
    """

    try:
        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json"
        )

        content = response["message"]["content"]

        print("[DEBUG] Vocabulary raw response:", repr(content))

        content = content.strip()

        if content.startswith("```"):
            content = content.removeprefix("```json").removeprefix("```")
            content = content.removesuffix("```").strip()

        data = json.loads(content)

        # FIX: the model may return a JSON list instead of an object.
        if not isinstance(data, dict):
            print("[Vocabulary skipped] Response is not a JSON object.")
            return

        allowed_types = {
            "word",
            "expression",
            "phrasal verb",
            "idiom",
            "collocation",
        }

        # FIX: removed the leftover empty `for` loop that sat here.
        vocabulary = data.get("vocabulary", [])

        if not isinstance(vocabulary, list):
            print("[Vocabulary skipped] Invalid vocabulary format.")
            return

        for item in vocabulary[:5]:

            # Make sure each item is a dictionary
            if not isinstance(item, dict):
                print(
                    f"[Vocabulary skipped] Invalid item structure: {item!r}"
                )
                continue

            if item.get("item_type") not in allowed_types:
                print(
                    f"[Vocabulary skipped] Invalid item type: "
                    f"{item.get('item_type')}"
                )
                continue

            if not all(
                item.get(field)
                for field in ("term", "meaning_ar")
            ):
                print("[Vocabulary skipped] Missing required fields.")
                continue

            save_vocabulary(
                term=item["term"],
                item_type=item["item_type"],
                meaning_ar=item["meaning_ar"],
                definition_en=item.get("definition_en"),
                example=item.get("example"),
                synonyms=item.get("synonyms"),
                topic=item.get("topic"),
                source=source,
                grammatical_class=item.get("grammatical_class"),
                meaning_en=item.get("meaning_en"),
            )
    except Exception as e:

        print(f"[Vocabulary extraction error] {e}")


def build_semantic_vocabulary_context(text, limit=5):
    """Retrieve semantically relevant vocabulary from learner memory."""

    if not text or not text.strip():
        return ""

    try:
        results = search_semantic_vocabulary(text, limit=limit)

        if not results:
            return ""

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

        return "\n".join(lines)

    except Exception as error:
        print(f"[WARNING] Semantic vocabulary search failed: {error}")
        return ""


# ============================================================
# NEW: VOCABULARY PLANNING, MANDATORY REUSE, AND VERIFICATION
# Python retrieves candidates (semantic + same topic), Gemma plans
# which expression fits (and how to adapt it), the answer prompt
# makes it mandatory, and Python verifies the final answer.
# ============================================================

def get_candidate_vocabulary(text, max_items=8):
    """Semantic matches (looser threshold) + items sharing their topics."""

    if not text or not text.strip():
        return []

    try:
        semantic = search_semantic_vocabulary(
            text, limit=5, threshold=0.55
        )
    except Exception as error:
        print(f"[WARNING] Candidate search failed: {error}")
        return []

    candidates = list(semantic)
    seen_ids = {item["id"] for item in candidates}

    # Same-topic expansion.
    topics = {
        item.get("topic") for item in semantic if item.get("topic")
    }

    for topic in topics:
        try:
            extras = get_vocabulary_by_topic(
                topic, limit=3, exclude_ids=seen_ids
            )
        except Exception as error:
            print(f"[WARNING] Topic lookup failed: {error}")
            continue

        for extra in extras:
            candidates.append(extra)
            seen_ids.add(extra["id"])

    return candidates[:max_items]


def plan_vocabulary_usage(user_message, candidates):
    """Ask Gemma to choose (and adapt) one candidate expression, or none."""

    if not candidates:
        return None

    candidate_lines = [
        {
            "term": c["term"],
            "meaning_en": c.get("meaning_en"),
            "example": c.get("example"),
            "topic": c.get("topic"),
        }
        for c in candidates
    ]

    prompt = f"""
You help an English tutor reuse the learner's saved vocabulary.

Learner message: {user_message}

Saved expressions:
{json.dumps(candidate_lines, ensure_ascii=False)}

Decide whether ONE expression fits naturally in the tutor's reply.
You may adapt it (tense, plural, pronoun) but keep its meaning.
Only choose it if it truly fits the topic of the message.

Return ONE JSON object only:
{{"chosen_term": "<exact saved term or null>",
  "adapted_form": "<how it will appear in the reply>",
  "reason": "<short reason>"}}
If nothing fits: {{"chosen_term": null, "adapted_form": "", "reason": ""}}
"""

    try:
        response = client.chat(
            model=MODEL,
            format="json",
            messages=[{"role": "user", "content": prompt}],
        )

        data = parse_json_object(
            response.get("message", {}).get("content", "")
        )

        if not data or not data.get("chosen_term"):
            return None

        chosen = normalize(data["chosen_term"])
        valid = {normalize(c["term"]) for c in candidates}

        # Never accept an invented term.
        if chosen not in valid:
            return None

        adapted = (
            data.get("adapted_form") or data["chosen_term"]
        ).strip()

        return {
            "term": data["chosen_term"].strip(),
            "adapted_form": adapted,
        }

    except Exception as error:
        print(f"[WARNING] Vocabulary planning failed: {error}")
        return None


def build_vocabulary_plan_context(plan):
    """Turn the plan into a mandatory instruction for the answer."""

    if not plan:
        return ""

    return (
        "MANDATORY VOCABULARY REUSE FOR THIS REPLY:\n"
        f"You MUST use this saved expression in the Answer section: "
        f"\"{plan['adapted_form']}\" (saved term: \"{plan['term']}\").\n"
        "Use it in a natural, meaningful sentence. Do not list it, "
        "do not explain it, and do not mention that it is saved vocabulary."
    )


def _stem(word):
    return word[:5] if len(word) > 5 else word


def answer_uses_expression(answer, plan):
    """Tolerant check: every word of the expression appears (stem match)."""

    answer_words = [_stem(w) for w in normalize(answer).split()]

    for word in normalize(plan["adapted_form"]).split():
        if _stem(word) not in answer_words:
            return False

    return True


# ============================================================
# 2. PERSISTENT REVIEW STATE
# ============================================================

def init_tutor_state():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tutor_state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        connection.execute("""
            INSERT OR IGNORE INTO tutor_state (key, value)
            VALUES ('active_review_id', '')
        """)
        connection.execute("""
            INSERT OR IGNORE INTO tutor_state (key, value)
            VALUES ('review_session_active', '0')
        """)


def get_state_value(key, default=""):
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT value FROM tutor_state WHERE key = ?", (key,)
        ).fetchone()
    return row[0] if row else default


def set_state_value(key, value):
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO tutor_state (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))


def get_active_review_id():
    value = get_state_value("active_review_id", "")
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def set_active_review_id(review_id):
    value = "" if review_id is None else str(int(review_id))
    set_state_value("active_review_id", value)


def is_review_session_active():
    return get_state_value("review_session_active", "0") == "1"


def set_review_session_active(active):
    set_state_value("review_session_active", "1" if active else "0")


# ============================================================
# 3. REVIEW SESSION INTENT
# Reviews start only when the learner asks. A pending review is
# preserved when paused and resumes when the learner asks again.
# ============================================================

def wants_to_start_reviews(message):
    text = normalize(message).strip()

    # FIX: normalize() keeps apostrophes, so "let's" must be matched
    # explicitly. `let'?s` matches both "lets" and "let's".
    patterns = [
        # Explicit review commands
        r"\b(start|begin|resume|continue|return to)\s+(my\s+|the\s+|our\s+)?(english\s+)?reviews?\b",

        # Natural expressions
        r"\b(let us|let'?s)\s+(start|begin|do|continue|resume|return to|come back to|get back to|go back to)\s+(the\s+|my\s+|our\s+)?(english\s+)?reviews?\b",
        r"\b(can we|could we|shall we)\s+(start|begin|do|continue|resume|return to|come back to|get back to|go back to)\s+(the\s+|my\s+|our\s+)?(english\s+)?reviews?\b",
        r"\bi (want|would like|wanna)\s+to\s+(start|begin|do|continue|resume|return to|get back to|go back to)\s+(the\s+|my\s+|our\s+)?(english\s+)?reviews?\b",

        # Short or imperfect expressions
        r"^(let\s+s|let'?s|let us)\s+(go\s+)?back$",
        r"^(come|get)\s+back$",
        r"^back\s+to\s+(the\s+)?review$",
        r"^(continue|resume)\s*$",

        # Other expressions
        r"\bquiz me on my mistakes\b",
        r"\bpractice my saved mistakes\b",
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def wants_to_pause_reviews(message):
    text = normalize(message)
    patterns = [
        r"\b(stop|pause|disable|cancel)\s+(the\s+)?(reviews?|review session)\b",
        r"\bno more reviews?\b",
        r"\bno reviews? (for now|right now|today)\b",
        r"\bnot now\b",
        r"\bmaybe later\b",
        r"\blet's talk about something else\b",
        r"\blet us talk about something else\b",
        r"\bchange the subject\b",
        r"\bi do not want (a )?review\b",
        r"\bi don't want (a )?review\b",
        r"\bcould you stop giving me reviews?\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


# ============================================================
# 4. ENGLISH TUTOR INSTRUCTIONS
# ============================================================

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
STEP 7 — PERSONALIZED VOCABULARY REUSE

You have access to the learner's personal vocabulary memory.
It contains English words and expressions the learner has
previously encountered or learned.

Your responsibility is not simply to retrieve this vocabulary.
You must actively help the learner reuse it in real conversations.

Follow these rules:

1. Before composing your answer, review the retrieved vocabulary
   and identify expressions that fit the current conversation.

2. When one or more expressions are genuinely relevant,
   prioritize using at least ONE of them naturally in your answer.

3. Prefer vocabulary from the learner's memory over repeatedly
   using basic or generic expressions when both communicate
   the same meaning naturally.

4. Use the retrieved expressions in meaningful sentences.
   Do not simply list them or mention them without context.

5. Respect the meaning, grammatical structure, and natural
   usage of every expression.

6. Do not force vocabulary into unrelated topics or answers.

7. If none of the retrieved expressions fits the conversation,
   answer naturally without using them.

8. Vary your vocabulary. Avoid repeatedly selecting the same
   expression when other relevant expressions are available.

9. Do not invent previously learned expressions.
   Only use vocabulary explicitly supplied in the learner's memory.

10. Your priority is to help the learner gradually incorporate
    previously learned vocabulary into active communication.

11. If a section called "MANDATORY VOCABULARY REUSE FOR THIS REPLY"
    is supplied, you MUST follow it. You may also add other useful
    English words and expressions of your own, naturally.

IMPORTANT:
Vocabulary reuse is part of your teaching methodology,
not an optional decorative feature.
"""


# ============================================================
# 5. NORMALIZATION AND DUPLICATE-SAFE MISTAKE SAVING
# ============================================================

def normalize(text):
    """Ignore case, repeated whitespace, and punctuation for comparison."""
    text = str(text or "").casefold()
    text = re.sub(r"[^\w\s']", "", text)
    return " ".join(text.split())


def extract_review_answer(message):
    """Extract an explicitly submitted answer to a pending review."""
    pattern = r"^\s*my answer to the review is\s*:\s*(.+?)\s*$"
    match = re.match(
        pattern,
        message or "",
        flags=re.IGNORECASE | re.DOTALL
    )
    return match.group(1).strip() if match else None


def save_mistake_if_new(mistake):
    """Save a genuine mistake unless its normalized pair already exists."""
    try:
        target_original = normalize(mistake["original_sentence"])
        target_correction = normalize(mistake["correction"])

        if not target_original or not target_correction:
            return False

        for row in get_mistakes():
            # Existing rows: (id, original, correction, explanation,
            # category, created_at).
            if (
                normalize(row[1]) == target_original
                and normalize(row[2]) == target_correction
            ):
                print("[DEBUG] This mistake is already saved.")
                return False

        save_mistake(
            mistake["original_sentence"].strip(),
            mistake["correction"].strip(),
            mistake["explanation"].strip(),
            mistake["category"].strip(),
        )
        print("[DEBUG] New English mistake saved.")
        return True

    except Exception as error:
        print("[DEBUG] Could not save English mistake:", error)
        return False


# ============================================================
# 6. JSON PARSING AND GENUINE MISTAKE DETECTION
# ============================================================

def parse_json_object(content):
    """Parse a JSON object, tolerating surrounding whitespace/fences."""
    if not isinstance(content, str) or not content.strip():
        return None

    content = content.strip()
    try:
        data = json.loads(content)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def detect_english_mistake(user_text, tutor_answer=None):
    """
    Detect only genuine errors in the latest user message.
    The tutor's answer is intentionally not sent to the detector.
    """
    extraction_prompt = """
You are a strict, careful English mistake detector.

Analyze ONLY the user's latest message. Identify only genuine,
unambiguous grammar, spelling, or vocabulary errors.

Return exactly one JSON object with these fields:
{
  "has_mistake": false,
  "original_sentence": "",
  "correction": "",
  "explanation": "",
  "category": ""
}

Rules:
1. Do not invent mistakes.
2. Do not classify correct informal English as incorrect.
3. Do not classify short conversational expressions or fragments as errors.
4. Do not treat optional punctuation or capitalization in casual chat
   as genuine learning mistakes.
5. Do not save stylistic preferences as mistakes.
6. A correct but informal expression is NOT a mistake.
7. A correct but less natural expression is NOT a mistake.
8. Only identify genuine errors that are useful for English learning.
9. Preserve the user's exact original wording in original_sentence.
10. Do not use a tutor's response or suggested alternative as evidence.
11. If the message contains no clear English error, set has_mistake to false.
12. If the message is mainly not English, set has_mistake to false.
13. Do not mark a sentence wrong merely because another wording is preferred.

Use a category such as grammar, spelling, vocabulary, or word_choice.
Return JSON only.
"""

    try:
        response = client.chat(
            model=MODEL,
            format="json",
            messages=[
                {"role": "system", "content": extraction_prompt},
                {"role": "user", "content": f"User's message:\n{user_text}"},
            ],
        )

        content = response.get("message", {}).get("content", "")
        data = parse_json_object(content)

        if not data or data.get("has_mistake") is not True:
            return None

        fields = ("original_sentence", "correction", "explanation", "category")
        for field in fields:
            if not isinstance(data.get(field), str) or not data[field].strip():
                return None

        # Reject identical original/correction pairs.
        if normalize(data["original_sentence"]) == normalize(data["correction"]):
            return None

        return data

    except Exception as error:
        print("[DEBUG] Mistake detection failed:", error)
        return None


# ============================================================
# 7. STRUCTURED MISTAKE MEMORY AND DUE REVIEWS
# ============================================================

def build_mistake_memory():
    saved_mistakes = get_mistakes()
    unique_mistakes = []
    seen = set()

    for row in reversed(saved_mistakes):
        original, correction = row[1], row[2]
        key = (normalize(original), normalize(correction))

        if key in seen:
            continue

        seen.add(key)
        unique_mistakes.append(row)
        if len(unique_mistakes) >= 10:
            break

    lines = [
        "STRUCTURED ENGLISH MISTAKE MEMORY:",
        "These are database records, not invented examples.",
        "When asked to list saved mistakes, use only these records.",
        "Preserve original sentences and corrections exactly.",
    ]

    for row in unique_mistakes:
        _, original, correction, explanation, category, _ = row
        lines.extend([
            f"Original: {original}",
            f"Correction: {correction}",
            f"Explanation: {explanation}",
            f"Category: {category}",
            "",
        ])

    if not unique_mistakes:
        lines.append("No structured mistakes have been saved.")

    return "\n".join(lines), len(unique_mistakes)


def build_recurring_mistake_memory():
    """Prepare recurring mistakes for personalized English practice."""
    recurring = get_recurring_mistakes()
    lines = [
        "RECURRING MISTAKE ANALYSIS:",
        "Use these patterns to personalize explanations and practice.",
        "Occurrence counts are saved database records, not guaranteed separate attempts.",
    ]

    if not recurring:
        lines.append("No recurring mistakes identified yet.")
    else:
        for item in recurring[:5]:
            lines.append(
                f"Original: {item['original']} | "
                f"Correction: {item['correction']} | "
                f"Category: {item['category']} | "
                f"Saved records: {item['occurrences']}"
            )

    return "\n".join(lines)


def build_due_review_context(limit=2):
    """Return distinct due mistakes for Python-managed review selection."""
    candidates = get_due_mistakes(limit=1000)
    due_mistakes = []
    seen = set()

    for row in candidates:
        key = (normalize(row[1]), normalize(row[2]))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        due_mistakes.append(row)
        if len(due_mistakes) >= limit:
            break

    if not due_mistakes:
        return "No scheduled mistake reviews are due.", []

    lines = [
        "SCHEDULED ENGLISH REVIEWS (application-managed):",
        "These saved mistakes are due for review.",
        "Python selects and displays a review only when the learner has an active review session.",
        "Do not ask a review question yourself.",
        "Do not reveal corrections unless the learner asks for help.",
    ]

    for row in due_mistakes:
        (
            mistake_id, original, correction, explanation, category,
            created_at, next_review_at, review_count, correct_streak,
            correct_count, wrong_count, last_reviewed_at, last_review_result,
        ) = row
        lines.extend([
            "",
            f"Internal review ID: {mistake_id}",
            f"Original mistake: {original}",
            f"Expected correction: {correction}",
            f"Explanation: {explanation}",
            f"Category: {category}",
            f"Previous attempts: {review_count}",
            f"Correct answers: {correct_count}",
            f"Incorrect answers: {wrong_count}",
        ])

    return "\n".join(lines), due_mistakes


# ============================================================
# 8. REVIEW HELP AND ANSWER EVALUATION
# ============================================================

def looks_like_review_help_request(message):
    """Recognize clear requests for help with a pending review."""
    stripped = normalize(message)
    patterns = [
        r"\brepeat\b",
        r"\bsay that again\b",
        r"\bwhat was the sentence\b",
        r"\bwhat sentence (do|did|should|must|need to)\b",
        r"\bwhich sentence\b",
        r"\bgive me a hint\b",
        r"\bhelp me\b",
        r"\bexplain (it|that|the sentence|the question)\b",
        r"\bi (do not|don't|dont) remember\b",
        r"\bi (do not|don't|dont) understand\b",
        r"\bcan we skip\b",
        r"\bwhat do i need to correct\b",
        r"\btell me (the )?(sentence|question)\b",
    ]
    return any(re.search(pattern, stripped) for pattern in patterns)


def find_mistake_by_id(mistake_id):
    """Find a saved mistake by its database ID."""
    for row in get_mistakes():
        if row[0] == mistake_id:
            return row
    return None


def evaluate_review_answer(user_answer, mistake):
    """Return (correct, feedback), or (None, error_message) on failure."""
    original = mistake[1]
    correction = mistake[2]
    explanation = mistake[3]

    prompt = f"""
Evaluate the learner's answer to an English review.

Saved original mistake: {original}
Expected correction: {correction}
Rule/explanation: {explanation}
Learner's answer: {user_answer}

Judge whether the answer correctly demonstrates the target rule.
Accept equivalent wording if it demonstrates the same rule and meaning.
Return one JSON object only:
{{"correct": true, "feedback": "Short, learner-friendly feedback"}}
The correct value must be a JSON boolean, not a string.
"""

    last_error = "The model returned an empty or invalid response."

    for attempt in range(2):
        try:
            response = client.chat(
                model=MODEL,
                format="json",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Evaluate the answer now."},
                ],
            )
            content = response.get("message", {}).get("content", "")
            data = parse_json_object(content)

            if data and isinstance(data.get("correct"), bool):
                feedback = data.get("feedback", "")
                if not isinstance(feedback, str):
                    feedback = ""
                return data["correct"], feedback.strip()

            last_error = f"Invalid evaluator response: {content[:200]!r}"

        except Exception as error:
            last_error = str(error)

    return None, last_error


# ============================================================
# 9. INITIALIZE
# ============================================================

init_db()
init_tutor_state()

print("\nEnglish Tutor is ready!")
print("Your conversation history and saved mistakes are available.")

# Remind the learner about an unfinished review without activating it.
startup_review_id = get_active_review_id()

if startup_review_id is not None:
    pending_review = find_mistake_by_id(startup_review_id)

    if pending_review:
        print("\n" + "=" * 60)
        print("🔥 YOUR ENGLISH PROGRESS IS WAITING FOR YOU! 🔥")
        print("=" * 60)
        print("\nYou have an unfinished English review.")
        print("Remember: Every mistake is an opportunity to become better.")
        print("Real progress comes from practicing, making mistakes,")
        print("learning from them, and never giving up!")

        print("\n💪 Don't leave your progress unfinished.")
        print("Take a moment, challenge yourself, and prove what you have learned!")

        print(f'\nYour pending sentence:\n"{pending_review[1]}"')

        print("\n👉 Type 'resume review' to continue your review.")
        print("Your English journey continues one step at a time!")
        print("=" * 60)
    else:
        print("\nAn unfinished review was found, but its saved mistake is unavailable.")

print("\nType 'exit' to close the tutor.\n")


# ============================================================
# 10. MAIN CONVERSATION LOOP
# ============================================================

while True:
    message = input("You: ").strip()

    if message.lower() == "exit":
        print("Goodbye! Your conversation has been saved.")
        break

    if not message:
        continue

    try:
        review_feedback = ""
        active_review_id = get_active_review_id()
        review_session_active = is_review_session_active()
        review_answer = extract_review_answer(message)

        review_was_scored = False
        review_help_requested = False
        pause_requested = wants_to_pause_reviews(message)
        start_requested = wants_to_start_reviews(message)

        # FIX: always define the variable first, so it is never undefined
        # or left over from the previous message.
        semantic_vocabulary_context = ""
        vocabulary_plan = None            # NEW
        vocabulary_plan_context = ""      # NEW

        if not (pause_requested or start_requested or review_answer is not None):
            # extract_vocabulary(message, "Learner")
            # semantic_vocabulary_context = build_semantic_vocabulary_context(
            #     message,
            #     limit=5
            # )
            semantic_vocabulary_context = build_semantic_vocabulary_context(
                    message,
                    limit=5
                )

            # NEW: plan which saved expression (if any) to reuse.
            # Runs BEFORE extract_vocabulary so the message is not
            # retrieved as its own match.
            candidates = get_candidate_vocabulary(message)
            vocabulary_plan = plan_vocabulary_usage(message, candidates)
            vocabulary_plan_context = build_vocabulary_plan_context(
                vocabulary_plan
            )
            print("[DEBUG] Vocabulary plan:", vocabulary_plan)

            extract_vocabulary(message, "Learner")

        # Pause takes priority over any other review intent.
        if pause_requested:
            set_review_session_active(False)
            review_session_active = False
            review_feedback = (
                "\nREVIEW SESSION PAUSED:\n"
                "The learner has chosen to pause reviews. Respect this choice. "
                "Do not display a review or reminder. Continue the conversation "
                "normally. Keep any unfinished review saved for later.\n"
            )
            print("[DEBUG] Review session paused; pending review preserved.")

        elif start_requested:
            set_review_session_active(True)
            review_session_active = True
            review_feedback = (
                "\nREVIEW SESSION STARTED OR RESUMED:\n"
                "The learner explicitly asked to start or resume reviews. "
                "Python will provide the pending review or select a due review "
                "after the normal answer. Do not create a review yourself.\n"
            )
            print("[DEBUG] Review session activated.")

        # Reload the active ID after processing the user's intent.
        active_review_id = get_active_review_id()

        # An explicitly prefixed answer may complete the saved pending review
        # even if the learner had previously paused the review session.
        if (
            (review_session_active or review_answer is not None)
            and active_review_id is not None
        ):
            if review_answer is not None:
                set_review_session_active(True)
                review_session_active = True

            active_review = find_mistake_by_id(active_review_id)

            if active_review is None:
                set_active_review_id(None)
                active_review_id = None
                print("[DEBUG] Active review no longer exists; cleared its ID.")

            elif review_answer is not None:
                result, feedback = evaluate_review_answer(
                    review_answer, active_review
                )

                if result is not None:
                    record_review_result(active_review_id, result)
                    review_was_scored = True

                    if result:
                        # Correct answer: complete this review.
                        set_active_review_id(None)
                        active_review_id = None
                        print("[DEBUG] Review completed successfully.")

                    else:
                        # Incorrect answer: preserve the same review ID.
                        print(
                            "[DEBUG] Incorrect answer. "
                            "Keeping the same review ID for retry."
                        )

                    review_feedback += (
                        "\nRESULT OF THE JUST-ANSWERED REVIEW:\n"
                        f"Recorded result: {'correct' if result else 'incorrect'}.\n"
                        f"Evaluator feedback: {feedback or 'No extra feedback provided.'}\n"
                        "Acknowledge this result accurately. Do not claim mastery "
                        "from one correct answer.\n"
                    )
                    if result is False:
                        review_feedback += (
                            "\nSTRICT REVIEW RETRY INSTRUCTION:\n"
                            "The learner's answer is incorrect.\n"
                            "Explain the specific error briefly and kindly.\n"
                            "Ask the learner to correct the SAME original sentence again.\n"
                            "Do not ask whether the learner wants another sentence.\n"
                            "Do not offer to move to a different review.\n"
                            "Do not introduce a new review question.\n"
                            "The current review remains active.\n"
                        )

                    print(
                        "[DEBUG] Review result recorded:",
                        "correct" if result else "incorrect",
                    )

                else:
                    review_feedback += (
                        "\nREVIEW EVALUATION STATUS:\n"
                        "The evaluator could not validate the answer. Do not "
                        "claim it was recorded. Ask the learner to retry using "
                        "the exact review-answer prefix.\n"
                    )
                    print("[DEBUG] Review evaluation failed:", feedback)

            elif not start_requested:
                # An ordinary message while a review is pending pauses the
                # review session automatically, without scoring or reminders.
                set_review_session_active(False)
                review_session_active = False
                review_feedback += (
                    "\nREVIEW SESSION PAUSED AUTOMATICALLY:\n"
                    "The latest message is ordinary conversation, not a review "
                    "answer. Answer it naturally. Do not score, display, or "
                    "remind the learner about the pending review. Preserve it "
                    "for a later explicit resume request.\n"
                )
                print(
                    "[DEBUG] Ordinary message detected; review paused "
                    "without scoring."
                )

        # A review answer without an active pending review is not a normal
        # English practice sentence; tell the model not to pretend it was scored.
        elif review_answer is not None and not review_session_active:
            review_feedback += (
                "\nNO ACTIVE REVIEW:\n"
                "The learner submitted a review-answer prefix, but there is no "
                "active review session. Do not claim that an answer was scored. "
                "Explain briefly that they can ask to resume reviews first.\n"
            )

        save_message("user", message)

        history = get_chat_history(limit=30)
        mistake_memory, mistake_count = build_mistake_memory()
        recurring_memory = build_recurring_mistake_memory()
        review_context, due_mistakes = build_due_review_context(limit=2)
        stats = get_learning_stats()

        progress_context = (
            "\nLEARNING STATISTICS:\n"
            f"Saved mistakes: {stats['total_mistakes']}\n"
            f"Correct review answers: {stats['correct_answers']}\n"
            f"Incorrect review answers: {stats['wrong_answers']}\n"
            f"Reviews due: {stats['due_reviews']}\n"
            f"Review session active: {review_session_active}\n"
        )

        messages = [{
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + "\n\n" + mistake_memory
                + "\n\n" + recurring_memory
                # + "\n\n" + review_context
                + "\n\n" + progress_context
                + "\n\n" + semantic_vocabulary_context
                + "\n\n" + vocabulary_plan_context      # NEW
                + "\n\n" + review_feedback
                + "\n\nAPPLICATION RULE:\n"
                "Do not generate review markers, reminders, or scheduled quiz "
                "questions. Python alone manages reviews. Answer the user's "
                "latest message first. Never claim a review was scored unless "
                "the application explicitly provides that result."
            ),
        }]

        # Do not send old review conversations when starting/resuming.
        # Python will display the review question itself.
        if not start_requested:
            for role, content in history[-10:]:
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})

        print(
            f"\n[DEBUG] History messages: {len(history)} | "
            f"Unique mistakes: {mistake_count} | "
            f"Due reviews: {len(due_mistakes)} | "
            f"Review session active: {review_session_active}"
        )

        response = client.chat(model=MODEL, messages=messages)
        print("\n========== SEMANTIC CONTEXT SENT TO GEMMA ==========")
        print(semantic_vocabulary_context)
        print(vocabulary_plan_context)   # NEW
        print("====================================================\n")
        raw_answer = response.get("message", {}).get("content", "")

        # NEW: verify that the planned expression was actually used.
        # If not, ask Gemma once to rewrite the reply.
        if (
            vocabulary_plan
            and not answer_uses_expression(raw_answer, vocabulary_plan)
        ):
            print("[DEBUG] Planned expression missing. Retrying once.")
            retry_messages = messages + [
                {"role": "assistant", "content": raw_answer},
                {"role": "user", "content": (
                    "Rewrite your previous reply keeping the same three "
                    "headings. The Answer section MUST naturally include: "
                    f"\"{vocabulary_plan['adapted_form']}\". "
                    "Do not mention this instruction."
                )},
            ]
            try:
                retry = client.chat(model=MODEL, messages=retry_messages)
                retry_answer = retry.get("message", {}).get("content", "")
                if retry_answer.strip():
                    raw_answer = retry_answer
            except Exception as retry_error:
                print("[DEBUG] Vocabulary retry failed:", retry_error)

        # Select a due review only if the learner explicitly activated reviews.
        next_active_review_id = get_active_review_id()

        # When the learner explicitly resumes, show the same unfinished review.
        if (
            review_session_active
            and start_requested
            and next_active_review_id is not None
        ):
            pending_mistake = find_mistake_by_id(next_active_review_id)
            if pending_mistake is not None:
                raw_answer = raw_answer.rstrip() + (
                    "\n\nResuming your pending review: "
                    "How would you correct this sentence?\n"
                    f'“{pending_mistake[1]}”\n'
                    "When you are ready, begin your answer with: "
                    "'My answer to the review is:'"
                )

        # If there is no unfinished review, select one due mistake.
        elif (
            review_session_active
            and next_active_review_id is None
            # and not review_was_scored
            and due_mistakes
        ):
            selected_review = due_mistakes[0]
            next_active_review_id = selected_review[0]
            raw_answer = raw_answer.rstrip() + (
                "\n\nQuick review: How would you correct this sentence?\n"
                f'“{selected_review[1]}”\n'
                "When you are ready, begin your answer with: "
                "'My answer to the review is:'"
            )
            print("[DEBUG] Python selected due review ID:", next_active_review_id)

        set_active_review_id(next_active_review_id)
        print("[DEBUG] Active review ID:", get_active_review_id())

        answer = raw_answer.strip()
        extract_vocabulary(answer, "Tutor")

        print("\nTutor:", answer, "\n")
        save_message("assistant", answer)

        # Do not store review commands, review answers, or review-help requests
        # as ordinary learner mistakes.
        is_review_control_message = (
            start_requested or pause_requested or review_answer is not None
            or review_help_requested
        )

        if not is_review_control_message:
            mistake = detect_english_mistake(message)
            if mistake:
                save_mistake_if_new(mistake)

        # Phase 4.1 — Display vocabulary progress
        vocabulary_items = get_vocabulary()
        vocabulary_count = len(vocabulary_items)

        print("\n" + "=" * 45)
        print("VOCABULARY PROGRESS")
        print("=" * 45)

        print(
            f"You have learned {vocabulary_count} "
            "words and expressions so far."
        )

        print(
            "Would you like to practice remembering them?"
        )

        print("=" * 45)
    except Exception as error:
        print("An error occurred:", error)
        print("Check your Ollama Cloud connection, model, and database.")
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        memory
        
import sqlite3
import os
import json
import math
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai

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

        _gemini_client = genai.Client(api_key=api_key)

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


# NEW: added the optional `threshold` parameter. When it is None the
# behavior is exactly the same as before (SIMILARITY_THRESHOLD).
def search_semantic_vocabulary(query, limit=5, threshold=None):
    """
    Search vocabulary_items using semantic similarity.

    Generates an embedding for the query, compares it with
    stored vocabulary embeddings, and returns the closest items.
    """

    if not query or not query.strip():
        return []

    # NEW
    min_similarity = (
        SIMILARITY_THRESHOLD if threshold is None else threshold
    )

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

            # NEW: uses min_similarity instead of the fixed constant.
            if similarity >= min_similarity:
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


# NEW: return saved vocabulary items that share the same topic.
def get_vocabulary_by_topic(topic, limit=5, exclude_ids=()):
    """Return vocabulary items that share the same topic."""

    if not topic or not str(topic).strip():
        return []

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, term, topic, meaning_en, meaning_ar, example
            FROM vocabulary_items
            WHERE LOWER(TRIM(topic)) = LOWER(TRIM(?))
            ORDER BY occurrence_count DESC, id DESC
        """, (topic,)).fetchall()

    items = []

    for row in rows:
        if row[0] in exclude_ids:
            continue

        items.append({
            "id": row[0],
            "term": row[1],
            "topic": row[2],
            "meaning_en": row[3],
            "meaning_ar": row[4],
            "example": row[5],
            "similarity": None,
        })

        if len(items) >= limit:
            break

    return items


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