import requests
import json

BIFROST_API_URL = "http://103.86.176.184:3232/v1/chat/completions"

class BiFrostValidator:
    name = "bifrost"

    def validate(self, record: str) -> dict:
        payload = {
            "model": "openai/gpt-4o-mini",
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a strict ADDRESS VALIDATION engine. "
                        "Output ONLY valid JSON. "
                        "If a value is unknown, return empty string."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
Normalize and validate the address below.

Return ONLY JSON using this schema:
{{
  "normalized_address": "string",
  "city": "string",
  "state": "string",
  "postal_code": "string",
  "country": "string",
  "confidence_score": 0.0,
  "data_quality_flags": []
}}

Input:
{record}
"""
                }
            ]
        }

        response = requests.post(
            BIFROST_API_URL,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
