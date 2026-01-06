import requests
import json

PROMPT = """
You are a resume parser.

Extract information and return ONLY valid JSON.

Schema:
{
  "name": "",
  "email": "",
  "phone": "",
  "skills": [],
  "education": [
    {
      "degree": "",
      "institution": "",
      "year": ""
    }
  ],
  "experience": [
    {
      "company": "",
      "role": "",
      "duration": ""
    }
  ]
}
"""

def parse_with_llm(resume_text):
    payload = {
        "model": "llama3",
        "prompt": PROMPT + "\n\nRESUME:\n" + resume_text,
        "stream": False
    }

    res = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=120
    )

    output = res.json()["response"]
    return json.loads(output)
