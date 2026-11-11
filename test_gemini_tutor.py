
import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-3.1-flash-lite"


def test_model(title, prompt):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    start = time.time()

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        print(response.text)
        print(f"\nTime: {time.time() - start:.2f}s")

    except Exception as e:
        print(f"ERROR: {e}")


# TEST 1: Grammar correction
test_model(
    "TEST 1 - GRAMMAR CORRECTION",
    """
    You are a friendly English teacher.
    Correct genuine English mistakes only.
    Use these headings:
    English correction:
    Why / More natural English:
    Answer:

    User: Yesterday I go to work by bus.
    """
)


# TEST 2: Natural conversation
test_model(
    "TEST 2 - NATURAL CONVERSATION",
    """
    You are a friendly English teacher.
    Correct genuine mistakes only.
    Use these headings:
    English correction:
    Why / More natural English:
    Answer:

    User: I think learning English is important
    for my career because I want to improve my skills.
    """
)


# TEST 3: Vocabulary extraction
test_model(
    "TEST 3 - VOCABULARY EXTRACTION",
    """
    Extract up to 5 useful English vocabulary expressions
    from this sentence.

    Return ONLY valid JSON.

    Format:
    {
      "vocabulary": [
        {
          "term": "expression",
          "item_type": "collocation",
          "meaning_en": "English meaning",
          "meaning_ar": "Arabic meaning",
          "example": "Example sentence"
        }
      ]
    }

    Sentence:
    I want to improve my communication skills
    and overcome obstacles in my career.
    """
)
