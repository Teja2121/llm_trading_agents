import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    alphavantage_api_key: str
    openai_model: str = "gpt-4o-mini"
    db_path: str = "data/trading.db"


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to your .env file.")
    return value


def get_settings() -> Settings:
    return Settings(
        openai_api_key=_require("OPENAI_API_KEY"),
        alphavantage_api_key=_require("ALPHAVANTAGE_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        db_path=os.getenv("DB_PATH", "data/trading.db"),
    )


def _mask(secret: str) -> str:
    return "***" if len(secret) <= 8 else f"{secret[:4]}...{secret[-4:]}"


if __name__ == "__main__":
    s = get_settings()
    print("OpenAI key:", _mask(s.openai_api_key))
    print("Alpha Vantage key:", _mask(s.alphavantage_api_key))
    print("Model:", s.openai_model)
    print("DB path:", s.db_path)
