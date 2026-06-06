"""User configurable application settings."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..services.settings_service import public_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["设置"])


class SettingsUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    default_quality: Optional[str] = None
    transparent_background: Optional[bool] = None
    openai_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    agnes_api_key: Optional[str] = None
    comfyui_base_url: Optional[str] = None
    comfyui_input_dir: Optional[str] = None


@router.get("")
def get_settings():
    return public_settings()


@router.put("")
def update_settings(data: SettingsUpdate):
    save_settings(data.model_dump(exclude_unset=True))
    return public_settings()
