"""Pure helper functions for the tutor's review logic (no database, no model)."""
import re
from difflib import SequenceMatcher


def normalize(text):
    """Ignore case, repeated whitespace, and punctuation for comparison."""
    text = str(text or "").casefold()
    text = re.sub(r"[^\w\s']", "", text)
    return " ".join(text.split())


def looks_like_separate_question(message):
    """True when the message is clearly a new question."""
    stripped = (message or "").strip().lower()
    if "?" in stripped:
        return True
    return bool(re.match(
        r"^(what|why|when|where|who|whom|whose|which|how|can|could|would|"
        r"will|do|does|did|is|are|am|was|were|have|has|had)\b",
        stripped,
    ))


def is_skip_command(message):
    return normalize(message) in {"skip", "skip review", "skip it", "skip this"}


def is_review_attempt(message, mistake):
    """
    Decide whether the message is an attempt to answer the pending review.
    `mistake` is a database row: (id, original, correction, ...).

    A message counts as an attempt only if it resembles the review sentence
    or its correction. Anything else is a normal message and must NOT be
    scored.
    """
    if looks_like_separate_question(message):
        return False

    msg = normalize(message)
    msg_tokens = msg.split()
    if len(msg_tokens) < 2:
        return False

    targets = [normalize(mistake[1]), normalize(mistake[2])]
    target_tokens = set(" ".join(targets).split())

    overlap = sum(1 for t in msg_tokens if t in target_tokens) / len(msg_tokens)
    similarity = max(SequenceMatcher(None, msg, t).ratio() for t in targets)

    return overlap >= 0.6 or similarity >= 0.6


def is_trivial_change(original, correction):
    """True when the 'mistake' is only case, spacing or punctuation."""
    return normalize(original) == normalize(correction)


def pick_review(due_mistakes, user_message):
    """
    Pick the first due mistake that is not the sentence the user just typed.
    Returns a database row or None.
    """
    typed = normalize(user_message)
    for row in due_mistakes:
        candidate = normalize(row[1])
        if not candidate:
            continue
        if candidate == typed:
            continue
        if SequenceMatcher(None, candidate, typed).ratio() >= 0.9:
            continue
        return row
    return None
