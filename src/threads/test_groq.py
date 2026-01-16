# Test script - save as test_groq.py and run
import os
from groq import Groq
import httpx

# Use environment variable for API key
api_key = os.getenv("GROQ_API_KEY", "")
if not api_key:
    print("Error: GROQ_API_KEY environment variable not set")
    exit(1)

client = Groq(
    api_key=api_key,
    http_client=httpx.Client(timeout=60.0, verify=False)
)

response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Say hello in one line"}],
    max_completion_tokens=50
)

print(response.choices[0].message.content)