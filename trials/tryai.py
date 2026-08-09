import requests
import json
import dotenv
import os

dotenv.load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

print("sending request to OpenRouter API...")
response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {api_key}",
  },
  data=json.dumps({
    "model": "z-ai/glm-5.2",
    "messages": [{
        "role": "user",
        "content": "summarize the sequence in the churning of the ocean (samudra manthana) in short sentences"
    }]
  })
)
response.raise_for_status()
data = response.json()
print(data["choices"][0]["message"]["content"])
