import os, time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=20_000),
)

# 1. List the models your key can use for chat
names = []
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "generateContent" in actions and "flash" in m.name:
        names.append(m.name.replace("models/", ""))
print("Flash models available:", names)

# 2. Test each one with a short timeout
for name in names:
    t = time.time()
    try:
        r = client.models.generate_content(model=name, contents="Say hi")
        print(f"OK   {name}: {time.time()-t:.1f}s -> {r.text.strip()[:40]}")
    except Exception as e:
        print(f"FAIL {name}: {time.time()-t:.1f}s -> {str(e)[:80]}")