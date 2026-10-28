
import os
import time
from dotenv import load_dotenv
from ollama import Client

load_dotenv()

api_key = os.getenv("OLLAMA_API_KEY")

if not api_key:
    raise RuntimeError(
        "OLLAMA_API_KEY was not found. Check your .env file."
    )

client = Client(
    host="https://ollama.com",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=120,
)

print("Testing Ollama Cloud...")

start = time.perf_counter()

try:
    response = client.chat(
        model="gemma4:31b",
        messages=[
            {
                "role": "user",
                "content": (
                    "Correct this English sentence briefly: "
                    "'I do agree with you.'"
                ),
            }
        ],
        stream=False,
    )

    print("\nCloud response:")
    print(response.message.content)
    print(f"\nResponse time: {time.perf_counter() - start:.2f} seconds")

except Exception as e:
    print(f"\nCloud API error: {e}")
