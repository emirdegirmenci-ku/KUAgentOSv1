# app/configs/agent_ids.py
"""
Merkezi Agent ID tanımları.
Manuel string ID kullanımı yerine enum benzeri yapı.
"""
from enum import Enum


class AgentID(str, Enum):
    """
    Tüm agent ID'leri burada tanımlanır.
    Bu sayede:
    - Yeni agent eklerken yanlış yazmayı engeller
    - IDE otomatik tamamlama desteği sağlar
    - Tüm agent ID'ler tek bir yerde yönetilir
    """
    ORCHESTRATOR = "orchestrator-agent"
    SATINALMA_PDF = "satinalma-pdf-agent"


# Type-safe agent ID doğrulama helper
def is_valid_agent_id(agent_id: str) -> bool:
    """Verilen agent_id geçerli mi kontrol eder."""
    return agent_id in [e.value for e in AgentID]


def get_agent_display_name(agent_id: str) -> str:
    """Agent ID'ye göre kullanıcı dostu isim döner."""
    display_names = {
        AgentID.ORCHESTRATOR: "Yönlendirme Asistanı",
        AgentID.SATINALMA_PDF: "Satınalma Asistanı",
    }
    return display_names.get(agent_id, agent_id)
