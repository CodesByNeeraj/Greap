"""Environment-driven settings, loaded once so every module reads the same values."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from greap.constants import REAP_VERSION

DEFAULT_REAP_URL = "https://sandbox.api.reap.global"
DEFAULT_MODEL = "gpt-6.1-sol"
DEFAULT_DATA_DIR = "data"
DEFAULT_EMAIL = "orders@example.com"
# Reap requires a phone number on shipping addresses but the PRD never asks
# for one, so sandbox orders use a fixed placeholder.
DEFAULT_PHONE = "+6591234567"
TRUTHY_VALUES = ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    """Everything the app needs from the environment."""

    reapApiKey: str
    reapBaseUrl: str
    reapVersion: str
    reapCountry: str
    reapCurrency: str
    openaiApiKey: str
    model: str
    telegramToken: str
    opsTelegramId: str
    orderEmail: str
    defaultPhone: str
    dataDir: Path
    dryRun: bool


def requireEnv(name: str) -> str:
    """Fail fast with a clear message instead of a confusing 401 later."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is missing. Add it to your .env file.")
    return value


def loadSettings() -> Settings:
    """Read .env and build the settings object."""
    # override=False keeps real environment variables ahead of the file.
    load_dotenv(override=False)
    return Settings(
        reapApiKey=requireEnv("REAP_API_KEY"),
        reapBaseUrl=os.environ.get("REAP_BASE_URL", DEFAULT_REAP_URL),
        reapVersion=os.environ.get("REAP_VERSION", REAP_VERSION),
        # The PRD examples are priced in SGD, and the sandbox catalog has them.
        reapCountry=os.environ.get("REAP_COUNTRY", "SG"),
        reapCurrency=os.environ.get("REAP_CURRENCY", "SGD"),
        openaiApiKey=requireEnv("OPEN_API_KEY"),
        model=os.environ.get("GREAP_MODEL", DEFAULT_MODEL),
        telegramToken=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        opsTelegramId=os.environ.get("GREAP_OPS_TELEGRAM_ID", "").strip(),
        orderEmail=os.environ.get("GREAP_ORDER_EMAIL", DEFAULT_EMAIL),
        defaultPhone=os.environ.get("GREAP_DEFAULT_PHONE", DEFAULT_PHONE),
        dataDir=Path(os.environ.get("GREAP_DATA_DIR", DEFAULT_DATA_DIR)),
        dryRun=os.environ.get("GREAP_DRY_RUN", "").lower() in TRUTHY_VALUES,
    )
