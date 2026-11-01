import os
import requests
from dotenv import load_dotenv

load_dotenv()

print("--- TESTING CONFIGURED API KEYS ---")

# 1. Test Gemini
gemini_key = os.environ.get("GEMINI_API_KEY")
if gemini_key:
    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        resp = client.models.generate_content(
            model="gemini-3.6-flash",
            contents="Say 'OK'"
        )
        print(f"  [Gemini]        -> SUCCESS: {resp.text.strip()}")
    except Exception as e:
        print(f"  [Gemini]        -> FAILED: {e}")
else:
  print("  [Gemini]        -> KEY NOT FOUND")

# 2. Test Groq (using verified active openai/gpt-oss-20b model)
groq_key = os.environ.get("GROQ_API_KEY")
if groq_key:
    try:
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": "Say 'OK'"}],
            "max_tokens": 10
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            print("  [Groq]          -> SUCCESS")
        else:
            print(f"  [Groq]          -> FAILED HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"  [Groq]          -> FAILED: {e}")
else:
  print("  [Groq]          -> KEY NOT FOUND")

# 3. Test NVIDIA NIM
nvidia_key = os.environ.get("NVIDIA_API_KEY")
if nvidia_key:
    try:
        headers = {
            "Authorization": f"Bearer {nvidia_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "messages": [{"role": "user", "content": "Say 'OK'"}],
            "max_tokens": 10
        }
        resp = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            print("  [NVIDIA NIM]    -> SUCCESS")
        else:
            print(f"  [NVIDIA NIM]    -> FAILED HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"  [NVIDIA NIM]    -> FAILED: {e}")
else:
  print("  [NVIDIA NIM]    -> KEY NOT FOUND")