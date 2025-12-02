# app/api/schemas.py
"""
API Request and Response Models.
"""
import uuid
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.configs.helpers import sanitize_user_id

class StartChatRequest(BaseModel):
    """
    Yeni chat session başlatma isteği.
    
    Attributes:
        user_id: Kullanıcı ID (zorunlu, manuel girilecek)
        message: İlk mesaj
    """
    user_id: str = Field(
        ...,
        description="Benzersiz kullanıcı ID",
        min_length=1,
        max_length=100,
    )
    message: str = Field(
        ...,
        description="Kullanıcının ilk mesajı",
        min_length=1,
        max_length=10000,
    )
    stream: bool = Field(
        False,
        description="Stream yanıt isteği",
    )
    
    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """User ID'yi temizle ve doğrula."""
        cleaned = sanitize_user_id(v)
        if cleaned == "anonymous":
            raise ValueError("user_id boş olamaz veya geçersiz karakterler içeremez")
        return cleaned


class StartChatResponse(BaseModel):
    """
    Chat session başlatma yanıtı.
    """
    session_id: str
    assigned_agent_id: str
    assigned_agent_name: str
    routing_reason: str
    reply: str
    latency_seconds: Optional[float] = None


class ChatMessageRequest(BaseModel):
    """
    Mevcut session'da mesaj gönderme isteği.
    
    Attributes:
        user_id: Kullanıcı ID (zorunlu)
        session_id: Session ID (zorunlu)
        message: Mesaj içeriği
    """
    user_id: str = Field(
        ...,
        description="Kullanıcı ID",
        min_length=1,
        max_length=100,
    )
    session_id: str = Field(
        ...,
        description="Session ID (UUID formatında)",
        min_length=1,
    )
    message: str = Field(
        ...,
        description="Mesaj içeriği",
        min_length=1,
        max_length=10000,
    )
    stream: bool = Field(
        False,
        description="Stream yanıt isteği",
    )
    
    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """User ID'yi temizle ve doğrula."""
        cleaned = sanitize_user_id(v)
        if cleaned == "anonymous":
            raise ValueError("user_id boş olamaz veya geçersiz karakterler içeremez")
        return cleaned
    
    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Session ID formatını doğrula."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("session_id geçerli bir UUID formatında olmalıdır")
        return v


class ChatMessageResponse(BaseModel):
    """
    Mesaj yanıtı.
    
    Attributes:
        reply: Agent'ın cevabı
        email_triggered: Mail gönderildi mi?
        email_info: Mail bilgileri (varsa)
    """
    reply: str
    email_triggered: bool = False
    email_info: Optional[dict] = None
