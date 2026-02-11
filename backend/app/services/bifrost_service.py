import requests
import json
from typing import Optional

BIFROST_API_URL = "http://103.86.176.184:3232/v1/chat/completions"


def bifrost_validate(raw_record: str, user_prompt: Optional[str] = "") -> dict:
    """
    Calls BiFrost (OpenAI-compatible) API to normalize and validate an address.
    Supports optional user prompt injection.
    """

    prompt_prefix = f"{user_prompt.strip()}\n\n" if user_prompt and user_prompt.strip() else ""

    payload = {
        "model": "openai/gpt-4o-mini",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict ADDRESS VALIDATION engine. "
                    "Output ONLY valid JSON. "
                    "No markdown. No explanations. "
                    "If a value is unknown, return empty string or empty array."
                )
            },
            {
                "role": "user",
                "content": f"""
{prompt_prefix}Normalize and validate the address below.

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
{raw_record}
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

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON returned from BiFrost: {content}") from e
