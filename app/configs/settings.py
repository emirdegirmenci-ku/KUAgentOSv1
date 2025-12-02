# app/configs/settings.py
"""
Uygulama ayarları ve konfigürasyon yönetimi.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class GoogleSettings(BaseSettings):
    """Google Cloud ve Vertex AI ayarları."""
    google_application_credentials: str = Field(
        default="service_account.json",
        env="GOOGLE_APPLICATION_CREDENTIALS",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    project_id: str = Field(..., env="PROJECT_ID")
    location: str = Field(default="us-central1", env="LOCATION")
    gemini_model_name: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL_NAME")


class VertexAISearchSettings(BaseSettings):
    """Vertex AI Search (RAG) ayarları."""
    data_store_id: str = Field(..., env="DATA_STORE_ID")
    data_store_location: str = Field(default="global", env="DATA_STORE_LOCATION")
    gcs_bucket_name: str = Field(..., env="GCS_BUCKET_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class DatabaseSettings(BaseSettings):
    """Veritabanı ayarları."""
    sqlite_db_file: str = Field(default="data/agent_sessions.db", env="AGNO_SQLITE_DB_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class MailSettings(BaseSettings):
    """Mail servisi ayarları."""
    mail_sender_name: str = Field(default="Chatbot", env="MAIL_SENDER_NAME")
    mail_sender_email: str = Field(default="no-reply@example.com", env="MAIL_SENDER_EMAIL")
    mail_default_recipient: str = Field(default="satinalma@example.com", env="MAIL_DEFAULT_RECIPIENT")
    conversation_logs_dir: str = Field(default="data/conversations", env="CONVERSATION_LOGS_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class AgentSettings(BaseSettings):
    """Agent talimatları ve davranış ayarları."""
    satinalma_agent_instructions: str = Field(
        ...,
        env="SATINALMA_AGENT_INSTRUCTIONS",
    )
    orchestrator_agent_instructions: str = Field(
        ...,
        env="ORCHESTRATOR_AGENT_INSTRUCTIONS",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class Settings(BaseSettings):
    """Ana settings sınıfı - tüm alt ayarları toplar."""
    # Alt setting grupları
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    vertex_search: VertexAISearchSettings = Field(default_factory=VertexAISearchSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    mail: MailSettings = Field(default_factory=MailSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)

    # Genel ayarlar
    os_security_key: str = Field(..., env="OS_SECURITY_KEY")
    agent_run_timeout_seconds: int = Field(
        default=60,
        env="AGENT_RUN_TIMEOUT_SECONDS",
        description=(
            "Agent çağrılarının en fazla beklenmesine izin verilen süre (saniye). "
            "Yoğun trafik altında uzun süren isteklerin kuyruğu tıkamasını önler."
        ),
    )
    
    # Legacy properties (geriye uyumluluk için)
    @property
    def google_application_credentials(self) -> str:
        return self.google.google_application_credentials
    
    @property
    def project_id(self) -> str:
        return self.google.project_id
    
    @property
    def location(self) -> str:
        return self.google.location
    
    @property
    def gemini_model_name(self) -> str:
        return self.google.gemini_model_name
    
    @property
    def data_store_id(self) -> str:
        return self.vertex_search.data_store_id
    
    @property
    def data_store_location(self) -> str:
        return self.vertex_search.data_store_location
    
    @property
    def gcs_bucket_name(self) -> str:
        return self.vertex_search.gcs_bucket_name
    
    @property
    def sqlite_db_file(self) -> str:
        return self.database.sqlite_db_file
    
    @property
    def mail_sender_name(self) -> str:
        return self.mail.mail_sender_name
    
    @property
    def mail_sender_email(self) -> str:
        return self.mail.mail_sender_email
    
    @property
    def mail_default_recipient(self) -> str:
        return self.mail.mail_default_recipient
    
    @property
    def conversation_logs_dir(self) -> str:
        return self.mail.conversation_logs_dir
    
    @property
    def satinalma_agent_instructions(self) -> str:
        return self.agent.satinalma_agent_instructions
    
    @property
    def orchestrator_agent_instructions(self) -> str:
        return self.agent.orchestrator_agent_instructions

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        # Nested model'lar için env prefix kullanma
        env_nested_delimiter = "__"


# Global settings instance
settings = Settings()

# Google credentials path ayarlama
if settings.google_application_credentials:
    creds_path = Path(settings.google_application_credentials)
    if not creds_path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        creds_path = project_root / creds_path
    if not creds_path.exists():
        raise FileNotFoundError(
            f"Google kimlik dosyası bulunamadı: {creds_path}"
        )
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)
