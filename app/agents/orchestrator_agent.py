# app/agents/orchestrator_agent.py
"""
Orchestrator agent'ı.
Kullanıcı sorgularını uygun domain agent'larına yönlendirir ve mail işlemlerini yönetir.
"""
from typing import Optional

from agno.agent import Agent
from agno.models.google import Gemini
from pydantic import BaseModel, Field

from app.configs.agent_ids import AgentID
from app.configs.settings import settings
from app.db.sqlite import agent_db
from app.tools.mail_tools import MailTools


class RoutingResponse(BaseModel):
    """
    Orchestrator routing yanıtı için structured output modeli.
    """
    target_agent_id: str = Field(
        ...,
        description="Yönlendirilecek agent ID'si (örn. 'satinalma-pdf-agent').",
    )
    reason: str = Field(
        ...,
        description="Neden bu agent'a yönlendirildiğinin kısa açıklaması.",
    )


# Gemini model (Vertex AI)
orchestrator_model = Gemini(
    id=settings.gemini_model_name,
    vertexai=True,
    project_id=settings.project_id,
    location=settings.location,
)

# Mail tools instance
mail_tools = MailTools()

# Orchestrator agent tanımı
orchestrator_agent = Agent(
    id=AgentID.ORCHESTRATOR.value,
    name="Orchestrator Agent",
    model=orchestrator_model,
    db=agent_db,
    tools=[mail_tools],
    add_history_to_context=True,
    num_history_runs=10,
    markdown=True,
    instructions=settings.orchestrator_agent_instructions,
    output_schema=RoutingResponse,
)
