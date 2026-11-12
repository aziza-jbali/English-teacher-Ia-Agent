
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env")

client = Groq(api_key=api_key)

MODEL = "qwen/qwen3.8-27b"

try:
    print(f"Testing Groq with {MODEL}...")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "You are a friendly English teacher. Help learners improve their English."
            },
            {
                "role": "user",
                "content": "I sometimes face difficulties at work, but I try to overcome obstacles. Can you respond naturally?"
            }
        ],
        temperature=0.4,
        max_completion_tokens=500,
    )

    print("\n========== GROQ RESPONSE ==========")
    print(response.choices[0].message.content)

    print("\nModel:", response.model)
    print("Status: SUCCESS")

except Exception as e:
    print("\nGROQ ERROR:")
    print(type(e).__name__, str(e))
