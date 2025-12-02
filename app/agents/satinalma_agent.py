# app/agents/satinalma_agent.py
"""
Satınalma domain agent'ı.
PDF dokümanlarından bilgi çekerek satınalma süreçleri hakkında sorulara cevap verir.
"""
from typing import Optional

from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field

from app.configs.agent_ids import AgentID
from app.configs.settings import settings
from app.db.sqlite import agent_db


class SatinalmaReply(BaseModel):
    """
    Satınalma agent'ının structured output modeli.
    
    Attributes:
        reply: Kullanıcıya gösterilecek cevap (Türkçe)
        email_intent: Kullanıcı bu turda mail atılmasını istiyor mu?
        email_recipient_hint: Mail atılması gereken kişi/ekip tahmini
        email_subject_suggestion: Mail konusu önerisi
        email_body_suggestion: Mail gövdesi taslağı
    """
    reply: str = Field(
        ...,
        description="Kullanıcıya gösterilecek nihai cevap (Türkçe).",
    )
    email_intent: bool = Field(
        default=False,
        description="Kullanıcı bu turda bu konuyla ilgili mail atılmasını istiyor mu?",
    )
    email_recipient_hint: Optional[str] = Field(
        default=None,
        description="Mail atılması gereken kişi veya ekip tahmini (örn. 'satınalma birimi').",
    )
    email_subject_suggestion: Optional[str] = Field(
        default=None,
        description="Mail konusu için öneri.",
    )
    email_body_suggestion: Optional[str] = Field(
        default=None,
        description="Mail gövdesi için taslak/öneri.",
    )


# Gemini model (Vertex AI)
satinalma_model = Gemini(
    id=settings.gemini_model_name,
    vertexai=True,
    project_id=settings.project_id,
    location=settings.location,
)

# Satınalma agent tanımı
satinalma_agent = Agent(
    id=AgentID.SATINALMA_PDF.value,
    name="Satınalma PDF Agent",
    model=satinalma_model,
    db=agent_db,
    add_history_to_context=True,
    num_history_runs=10,
    markdown=True,
    instructions=settings.satinalma_agent_instructions,
    output_schema=SatinalmaReply,
)
