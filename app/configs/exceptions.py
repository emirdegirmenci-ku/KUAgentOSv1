# app/configs/exceptions.py
"""
Özel exception sınıfları ve hata yönetimi.
"""
from typing import Optional


class BaseAgentError(Exception):
    """Tüm agent hatalarının base sınıfı."""
    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class AgentNotFoundError(BaseAgentError):
    """İstenen agent bulunamadığında."""
    pass


class InvalidAgentIDError(BaseAgentError):
    """Geçersiz agent ID kullanıldığında."""
    pass


class SessionError(BaseAgentError):
    """Session ile ilgili hatalar."""
    pass


class RoutingError(BaseAgentError):
    """Orchestrator routing işleminde hata."""
    pass


class ModelProviderError(BaseAgentError):
    """Gemini/model sağlayıcı hataları."""
    pass


class MailServiceError(BaseAgentError):
    """Mail gönderimi sırasında hatalar."""
    pass
