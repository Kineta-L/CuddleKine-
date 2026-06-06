"""Local user settings for provider configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import (
    COMFYUI_BASE_URL,
    COMFYUI_INPUT_DIR,
    DATA_DIR,
    GENERATION_PROVIDER,
    AGNES_API_KEY,
    OPENAI_API_KEY,
    REPLICATE_API_TOKEN,
)

SETTINGS_PATH = DATA_DIR / "provider_settings.json"


DEFAULT_SETTINGS: dict[str, Any] = {
    "default_provider": "openai" if OPENAI_API_KEY else GENERATION_PROVIDER,
    "default_model": "gpt-image-1.5" if OPENAI_API_KEY else "",
    "default_quality": "final" if OPENAI_API_KEY else "sample",
    "transparent_background": False,
    "openai_api_key": OPENAI_API_KEY,
    "replicate_api_token": REPLICATE_API_TOKEN,
    "agnes_api_key": AGNES_API_KEY,
    "comfyui_base_url": COMFYUI_BASE_URL,
    "comfyui_input_dir": str(COMFYUI_INPUT_DIR),
}


def load_settings() -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_PATH.exists():
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                settings.update({k: v for k, v in raw.items() if k in settings})
        except Exception:
            pass
    return settings


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    for key, value in patch.items():
        if key not in current or value is None:
            continue
        if key in ("openai_api_key", "replicate_api_token", "agnes_api_key"):
            current[key] = _normalize_secret(str(value))
        elif key in ("transparent_background",):
            current[key] = bool(value)
        else:
            current[key] = str(value).strip()

    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def public_settings() -> dict[str, Any]:
    settings = load_settings()
    return {
        "default_provider": settings["default_provider"],
        "default_model": settings["default_model"],
        "default_quality": settings["default_quality"],
        "transparent_background": settings["transparent_background"],
        "openai_configured": bool(settings["openai_api_key"]),
        "replicate_configured": bool(settings["replicate_api_token"]),
        "agnes_configured": bool(settings["agnes_api_key"]),
        "comfyui_base_url": settings["comfyui_base_url"],
        "comfyui_input_dir": settings["comfyui_input_dir"],
        "settings_path": str(SETTINGS_PATH),
    }


def get_openai_api_key() -> str:
    return _normalize_secret(str(load_settings().get("openai_api_key") or ""))


def get_replicate_api_token() -> str:
    return _normalize_secret(str(load_settings().get("replicate_api_token") or ""))


def get_agnes_api_key() -> str:
    return _normalize_secret(str(load_settings().get("agnes_api_key") or ""))


def _normalize_secret(value: str) -> str:
    value = value.strip().strip('"').strip("'")
    if "=" in value:
        value = value.split("=", 1)[1].strip().strip('"').strip("'")
    if value.lower().startswith("bearer "):
        value = value[7:].strip().strip('"').strip("'")
    match = re.search(r"(cpk-[A-Za-z0-9_\-]+|r8_[A-Za-z0-9]+|sk-[A-Za-z0-9_\-]+)", value)
    return match.group(1) if match else value


def get_default_provider() -> str:
    provider = str(load_settings().get("default_provider") or GENERATION_PROVIDER)
    return provider if provider in {"comfyui", "openai", "replicate", "agnes", "mock"} else GENERATION_PROVIDER


def get_default_quality() -> str:
    quality = str(load_settings().get("default_quality") or "sample")
    return quality if quality in {"draft", "sample", "final"} else "sample"


def get_comfyui_base_url() -> str:
    return str(load_settings().get("comfyui_base_url") or COMFYUI_BASE_URL)


def get_comfyui_input_dir() -> Path:
    return Path(str(load_settings().get("comfyui_input_dir") or COMFYUI_INPUT_DIR))
