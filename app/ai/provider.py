import json
import re
import httpx

from app.config import settings


SYSTEM_PROMPT = """You are OpsPilot AI, an SRE incident investigation assistant.
Use only the supplied incident evidence. Never invent logs, metrics, events, or actions.
Separate observed evidence from hypotheses.
Do not claim a remediation was executed.
Recommend safe, reversible steps first.
Return ONLY valid JSON with these keys:
summary (string),
probable_root_cause (string),
confidence (number between 0 and 1),
evidence (array of strings),
remediation (array of strings).
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    start = text.find("{")
    end = text.rfind("}")

    if start < 0 or end < start:
        raise ValueError("AI response did not contain JSON")

    result = json.loads(text[start:end + 1])

    required = {
        "summary",
        "probable_root_cause",
        "confidence",
        "evidence",
        "remediation",
    }

    if not required.issubset(result):
        raise ValueError("AI response is missing required fields")

    if not isinstance(result["confidence"], (int, float)):
        raise ValueError("Invalid confidence value")

    if not isinstance(result["evidence"], list):
        raise ValueError("Invalid evidence format")

    if not isinstance(result["remediation"], list):
        raise ValueError("Invalid remediation format")

    return result


async def _call_gemini(client, model, prompt):
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    response = await client.post(
        url,
        params={"key": settings.gemini_api_key},
        json={
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        },
    )

    response.raise_for_status()

    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    return _extract_json(text)


async def _call_openai(client, prompt):
    response = await client.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
    )

    response.raise_for_status()

    text = response.json()["choices"][0]["message"]["content"]

    return _extract_json(text)


async def investigate_with_ai(context: dict) -> tuple[dict | None, str]:
    prompt = json.dumps(context, ensure_ascii=False)

    timeout = httpx.Timeout(25.0, connect=10.0)

    preferred = settings.ai_provider.lower()

    async with httpx.AsyncClient(timeout=timeout) as client:

        providers = (
            ["gemini", "openai"]
            if preferred == "gemini"
            else ["openai", "gemini"]
        )

        for provider in providers:

            if provider == "gemini" and settings.gemini_api_key:
                models = list(dict.fromkeys([
                    settings.gemini_model,
                    "gemini-3.6-flash",
                    "gemini-3.5-flash",
                ]))

                for model in models:
                    try:
                        result = await _call_gemini(
                            client, model, prompt
                        )
                        print(
                            f"[OpsPilot AI] Gemini success: {model}"
                        )
                        return result, "gemini"

                    except Exception as exc:
                        print(
                            f"[OpsPilot AI] Gemini failed "
                            f"({model}): {type(exc).__name__}"
                        )

            elif provider == "openai" and settings.openai_api_key:
                try:
                    result = await _call_openai(client, prompt)

                    print(
                        "[OpsPilot AI] OpenAI success: "
                        f"{settings.openai_model}"
                    )

                    return result, "openai"

                except Exception as exc:
                    print(
                        "[OpsPilot AI] OpenAI failed: "
                        f"{type(exc).__name__}"
                    )

    print(
        "[OpsPilot AI] All AI providers unavailable; "
        "using local rules."
    )

    return None, "rules"
