import os
from memory import save_mistake, get_mistakes
# from memory tells Python to look in memory.py.
# - import save_mistake, get_mistakes makes those two functions available in chatbot.py.
import json
# json is a Python module that helps us read and write JSON data.
response_text = '{"has_mistake": true, "original": "I am agree with you", "correction": "I agree with you"}'

data = json.loads(response_text)

from pyexpat.errors import messages #lahna hadhi tasla7 bach najem nsta3mel  7ajet mil operating system, 
# os is a Python built-in module that lets us interact with things from the operating system.
import ollama

# Here we're going to use it to read an environment variable
from dotenv import load_dotenv
from google import genai
# We installed python-dotenv.

# This gives us load_dotenv(), which reads the .env file. dotenv y3wna bach nakro les variables  w el contenu eli mawjoud fi .env
load_dotenv()
"Go look for the .env file and load its variables."
api_key = os.getenv("GEMINI_API_KEY")
# "Python, give me the value stored under GEMINI_API_KEY."
#
# print(api_key)
# if api_key:
#     # "Did we actually get a value?"
#     print("✅ Gemini API key loaded successfully!")
# else:
#     print("❌ Gemini API key not found!")
client = genai.Client(api_key=api_key)

# Send a message to Gemini
# interaction = client.interactions.create(
#     model="gemini-3.8-flash",
#     input="""
#     You are my personal English tutor.

#     Correct my English sentences.
#     Explain my mistakes in simple English.
#     Give me a more natural expression.
#     Encourage me to try again.

#     Correct this sentence:
#     She go to school every day.
#     """
# )

# while True:
#     sentence = input("You: ")

#     if sentence.lower() == "exit":
#         print("Goodbye! Keep practicing your English!")
#         break

#     interaction = client.interactions.create(
#         model="YOUR_SUPPORTED_MODEL",
#         input=f"""
#         You are my personal English tutor.

#         Correct my English sentence:
#         {sentence}

#         Explain my mistakes simply and give me a natural version.
#         """
#     )

#    print("Tutor:", interaction.output_text)

SYSTEM_PROMPT = """
You are an expert English teacher.

Your job is to correct English mistakes accurately.

When the user sends a sentence:
1. Write the grammatically correct sentence.
2. Explain the mistake in simple English.
3. Give a natural, commonly used version.
4. Do not change the intended meaning.
5. If the sentence is already correct, say so.

Be careful with English grammar and natural expressions.
"""



# Initialize the conversation history once
messages = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

while True:
    message = input("You: ").strip()

    if message.lower() == "exit":
        print("Goodbye!")
        break

    if not message:
        continue

    # Add the user's message to the history
    messages.append({
        "role": "user",
        "content": message
    })

    # Send the conversation history to the model
    response = ollama.chat(
        model="gemma4:latest",
        messages=messages
    )

    answer = response["message"]["content"]

    print("Tutor:", answer)

    # Add the tutor's answer to the history
    messages.append({
        "role": "assistant",
        "content": answer
    })


# while True:
#     message = input("You: ")

#     if message.lower() == "exit":
#         print("Goodbye!")
#         break

#     response = ollama.chat(
#         model="gemma4:latest",
#         # messages=[
#         #     {
#         #         "role": "user",
#         #         "content": message
#         #     }
#         # ]
#         messages = [
#      {"role": "system", "content": SYSTEM_PROMPT},
#      {"role": "user", "content": message}
#  ]
#     )

print("Llama:", response["message"]["content"])
#The goal is simple: connect your Python program to Gemini, send it a message, and receive an AI-generated response.
#to communicate with gemini and recieve a response we need a client 
#client: a variable that stores the object you will use to communicate with Gemini.
#genai: the Google Gen AI library that you imported into Python.
#Client(...): creates a client that manages communication with Google's AI service.
#I understand that genai is an object and client is an method of that object it expect an argument named api_key 
#the role of this argument is The role of this argument is to give the client the API key it needs to authenticate your requests  لمصادقة طلباتكto Google's AI service.
#بالتونسي: بالضبط، كيف مفتاح دخول يعطي للبرنامج متاعك إمكانية الوصول لخدمة Gemini.
# print(interaction.output_text)
# interaction → the variable that stores the result of your request to Gemini.

#.output_text → accesses the text output contained in that result.

#print() → displays that text in your terminal.
# Print Gemini's answer
# A while True loop that lets you keep chatting.

# hhhhhhhhhhh

# A conversation history stored in messages.
print("Tutor")
print(data["has_mistake"])
print(data["original"])
print(data["correction"])