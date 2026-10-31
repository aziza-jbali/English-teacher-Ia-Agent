










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

# def wants_to_start_reviews(message):
#     text = normalize(message)
#     patterns = [
#         r"\b(start|begin|resume|continue)\s+(my\s+)?(english\s+)?reviews?\b",
#         r"\b(let us|let's)\s+(start|do|continue|resume)\s+(the\s+)?reviews?\b",
#         r"\b(can we|could we)\s+(start|do|continue|resume)\s+(the\s+)?reviews?\b",
#         r"\bi want to (start|do|continue|resume)\s+(my\s+)?reviews?\b",
#         r"\bquiz me on my mistakes\b",
#         r"\bpractice my saved mistakes\b",
#     ]
#     return any(re.search(pattern, text) for pattern in patterns)

def wants_to_start_reviews(message):
    text = normalize(message).strip()

    patterns = [
        # Explicit review commands
        r"\b(start|begin|resume|continue|return to)\s+(my\s+|the\s+|our\s+)?(english\s+)?reviews?\b",

        # Natural expressions
        r"\b(let us|lets)\s+(start|begin|do|continue|resume|return to|come back to|get back to|go back to)\s+(the\s+|my\s+|our\s+)?(english\s+)?reviews?\b",
        r"\b(can we|could we|shall we)\s+(start|begin|do|continue|resume|return to|come back to|get back to|go back to)\s+(the\s+|my\s+|our\s+)?(english\s+)?reviews?\b",
        r"\bi (want|would like|wanna)\s+to\s+(start|begin|do|continue|resume|return to|get back to|go back to)\s+(the\s+|my\s+|our\s+)?(english\s+)?reviews?\b",

        # Short or imperfect expressions
        r"^(let\s+s|lets?|let's|let us)\s+(go\s+)?back$",
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

# init_db()
# init_tutor_state()

# print("\nEnglish Tutor is ready!")
# print("Your conversation history and saved mistakes are available.")
# print("Review sessions start only when you ask to start or resume them.")
# print("Type 'exit' to close the tutor.\n")
init_db()
init_tutor_state()

print("\nEnglish Tutor is ready!")
print("Your conversation history and saved mistakes are available.")

# Remind the learner about an unfinished review without activating it.
startup_review_id = get_active_review_id()

if startup_review_id is not None:
    pending_review = find_mistake_by_id(startup_review_id)

    if pending_review:
        # print("\nYou have an unfinished English review:")
        # print(f'"{pending_review[1]}"')
        # print("Type 'g' to continue.")
        # print("You can also start a normal conversation.")
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

        print("\n👉 Type 'g' to continue your review.")
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
                    
            #     if result is not None:
            #         record_review_result(active_review_id, result)
            #         set_active_review_id(None)
            #         active_review_id = None
            #         review_was_scored = True

            #         review_feedback += (
            #             "\nRESULT OF THE JUST-ANSWERED REVIEW:\n"
            #             f"Recorded result: {'correct' if result else 'incorrect'}.\n"
            #             f"Evaluator feedback: {feedback or 'No extra feedback provided.'}\n"
            #             "Acknowledge this result accurately. Do not claim mastery "
            #             "from one correct answer.\n"
            #         )
            #         print(
            #             "[DEBUG] Review result recorded:",
            #             "correct" if result else "incorrect",
            #         )

            #     else:
            #         review_feedback += (
            #             "\nREVIEW EVALUATION STATUS:\n"
            #             "The evaluator could not validate the answer. Do not "
            #             "claim it was recorded. Ask the learner to retry using "
            #             "the exact review-answer prefix.\n"
            #         )
            #         print("[DEBUG] Review evaluation failed:", feedback)

            # elif looks_like_review_help_request(message):
            #     review_help_requested = True
            #     review_feedback += (
            #         "\nPENDING REVIEW — LEARNER REQUESTED HELP:\n"
            #         "Do not score this message. Repeat the exact sentence to "
            #         "correct and give a small hint without revealing the full "
            #         "correction. Keep the same review active.\n"
            #     )
            #     print("[DEBUG] Review help requested; no score recorded.")

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
                + "\n\n" + review_feedback
                + "\n\nAPPLICATION RULE:\n"
                "Do not generate review markers, reminders, or scheduled quiz "
                "questions. Python alone manages reviews. Answer the user's "
                "latest message first. Never claim a review was scored unless "
                "the application explicitly provides that result."
            ),
        }]

        # # Keep the original history behavior.
        # for role, content in history[-10:]:
        #     if role in ("user", "assistant"):
        #         messages.append({"role": role, "content": content})
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
        raw_answer = response.get("message", {}).get("content", "")

        # Select a due review only if the learner explicitly activated reviews.
        # Do not select another review in the same turn as a scored answer;
        # the feedback is shown first and the next review can appear next turn.
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

    except Exception as error:
        print("An error occurred:", error)
        print("Check your Ollama Cloud connection, model, and database.")
