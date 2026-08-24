"""Konfiguracja wyłącznie przez zmienne środowiskowe (reguła krytyczna nr 5)."""

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    ollama_url: str = field(default_factory=lambda: _env("OLLAMA_URL", "http://localhost:11434"))
    model: str = field(default_factory=lambda: _env("MODEL", "qwen2.5:3b"))
    smtp_host: str = field(default_factory=lambda: _env("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(_env("SMTP_PORT", "1025")))


def get_settings() -> Settings:
    return Settings()
