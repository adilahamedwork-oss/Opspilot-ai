import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "OpsPilot AI")
    ai_provider: str = os.getenv("AI_PROVIDER", "gemini").lower()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    allow_demo_incidents: bool = os.getenv("ALLOW_DEMO_INCIDENTS", "true").lower() == "true"

settings = Settings()
