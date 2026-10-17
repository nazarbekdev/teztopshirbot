"""Muhit sozlamalari. Hamma narsa `.env` dan; maxfiy qiymat kodda yo'q."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local", override=True)


def _ids(raw: str) -> list[int]:
    return [int(x) for x in raw.replace(" ", "").split(",") if x.strip().lstrip("-").isdigit()]


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    api_key: str = field(default_factory=lambda: os.getenv("PARTNER_API_KEY", ""))
    api_base: str = field(default_factory=lambda: os.getenv(
        "PARTNER_API_BASE", "https://api.osontopshir.uz/partner/v1").rstrip("/"))
    admin_ids: list[int] = field(default_factory=lambda: _ids(os.getenv("ADMIN_IDS", "")))
    ops_channel: str = field(default_factory=lambda: os.getenv("OPS_CHANNEL_ID", ""))
    card_number: str = field(default_factory=lambda: os.getenv("CARD_NUMBER", ""))
    card_holder: str = field(default_factory=lambda: os.getenv("CARD_HOLDER", ""))
    click_merchant_id: str = field(default_factory=lambda: os.getenv("CLICK_MERCHANT_ID", ""))
    click_service_id: str = field(default_factory=lambda: os.getenv("CLICK_SERVICE_ID", ""))
    click_secret: str = field(default_factory=lambda: os.getenv("CLICK_SECRET_KEY", ""))
    click_port: int = field(default_factory=lambda: int(os.getenv("CLICK_PORT", "8081")))
    public_url: str = field(default_factory=lambda: os.getenv("PUBLIC_URL", "").rstrip("/"))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "teztopshir.db"))
    support_username: str = field(default_factory=lambda: os.getenv("SUPPORT_USERNAME", "").lstrip("@"))
    max_active: int = field(default_factory=lambda: int(os.getenv("MAX_ACTIVE_ORDERS", "8")))

    @property
    def click_enabled(self) -> bool:
        return bool(self.click_merchant_id and self.click_service_id and self.click_secret)

    @property
    def test_mode(self) -> bool:
        return self.api_key.startswith("ot_test_")


def load() -> Settings:
    return Settings()
