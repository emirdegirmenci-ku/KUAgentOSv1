# app/api/services.py
"""
Business logic and helper functions for API.
"""
import asyncio
import logging
from copy import deepcopy
from typing import Any, Dict, Optional, Tuple, Union, AsyncGenerator

from agno.agent import RunOutput

from app.agents.orchestrator_agent import orchestrator_agent
from app.agents.satinalma_agent import SatinalmaReply
from app.api.schemas import ChatMessageRequest, ChatMessageResponse
from app.configs.agent_ids import AgentID
from app.configs.exceptions import ModelProviderError
from app.configs.settings import settings

# Logger ayarla
logger = logging.getLogger(__name__)

CONFIRMATION_KEYWORDS = (
    "gönder",
    "gonder",
    "gönderebilirsin",
    "gonderebilirsin",
    "gönderilebilir",
    "gonderilebilir",
    "onayla",
    "onayladım",
    "onayliyorum",
    "onay ver",
    "evet gönder",
    "maili gönder",
    "maili gonder",
)

CANCEL_KEYWORDS = (
    "gönderme",
    "gonderme",
    "iptal",
    "vazgeç",
    "vazgec",
    "gönderilmesin",
    "gonderilmesin",
)

CONFIRMATION_HINT = (
    "Mail taslağını göndermemi istiyorsan 'gönder' veya 'onaylıyorum' yazman yeterli. "
    "Revize etmek için talimat verebilirsin."
)


def _clone_agent(agent: Any) -> Any:
    """Create an isolated copy of an agent for per-request execution.

    The global agent instances keep shared configuration (DB, tools, instructions),
    but some attributes like ``output_schema`` are mutated for streaming calls. To
    avoid cross-request interference we run agents on a shallow copy. ``model_copy``
    (pydantic v2) is preferred when available; otherwise we fall back to
    ``deepcopy`` while preserving underlying shared resources.
    """

    if hasattr(agent, "model_copy"):
        try:
            return agent.model_copy(deep=True)
        except Exception:
            logger.debug("model_copy deep clone failed; falling back to deepcopy")

    try:
        return deepcopy(agent)
    except Exception:
        logger.warning("Agent copy failed; using shared instance (risk of shared state)")
        return agent


def _normalize_message(text: str) -> str:
    return text.strip().lower()


def is_cancel_message(message: str) -> bool:
    normalized = _normalize_message(message)
    return any(keyword in normalized for keyword in CANCEL_KEYWORDS)


def is_confirmation_message(message: str) -> bool:
    normalized = _normalize_message(message)
    if is_cancel_message(normalized):
        return False
    return any(keyword in normalized for keyword in CONFIRMATION_KEYWORDS)


def _build_email_prompt(
    user_id: str,
    session_id: str,
    source_message: str,
    agent_reply: str,
    suggestion: SatinalmaReply,
) -> str:
    return (
        "MODE: EMAIL\n\n"
        f"USER_ID: {user_id}\n"
        f"SESSION_ID: {session_id}\n\n"
        "Aşağıda kullanıcı ile satınalma agent arasındaki mail taslağı bilgisi yer alıyor. "
        "Taslağı profesyonel hale getir, gerekiyorsa düzelt ve `mail_tools.send_email` fonksiyonunu"
        " bir kez çağır.\n\n"
        f"KULLANICI ORİJİNAL MESAJI:\n{source_message}\n\n"
        f"AGENT TASLAK CEVABI:\n{agent_reply}\n\n"
        f"EMAIL_RECIPIENT_HINT: {suggestion.email_recipient_hint or '-'}\n"
        f"EMAIL_SUBJECT_SUGGESTION: {suggestion.email_subject_suggestion or '-'}\n"
        "EMAIL_BODY_SUGGESTION:\n"
        f"{suggestion.email_body_suggestion or '-'}\n\n"
        "ONAY DURUMU: Kullanıcı mailin gönderilmesini açıkça onayladı."
    )


async def run_agent(
    agent,
    message: str,
    user_id: str,
    session_id: str,
    stream: bool = False,
    timeout_seconds: Optional[float] = None,
) -> Union[RunOutput, AsyncGenerator]:
    """
    Agent'ı asenkron çalıştırır ve sonucu döndürür.
    
    Args:
        agent: Çalıştırılacak agent instance
        message: Gönderilecek mesaj
        user_id: Kullanıcı ID
        session_id: Session ID
        stream: Streaming yanıt istenip istenmediği
        timeout_seconds: Opsiyonel özel zaman aşımı (saniye). Belirtilmezse
            `settings.agent_run_timeout_seconds` kullanılır.
    
    Returns:
        RunOutput: Agent çıktısı
    
    Raises:
        ModelProviderError: Model sağlayıcı hatası durumunda
    """
    try:
        timeout = timeout_seconds or settings.agent_run_timeout_seconds
        agent_instance = _clone_agent(agent)

        logger.info(
            f"Running agent: {agent_instance.id} | user_id: {user_id} | session_id: {session_id}"
        )
        if stream:
            logger.info(f"Running agent in stream mode: {agent_instance.id}")

            if hasattr(agent_instance, "output_schema"):
                agent_instance.output_schema = None
            if hasattr(agent_instance, "response_model"):
                agent_instance.response_model = None

            raw_stream = agent_instance.arun(
                input=message,
                user_id=user_id,
                session_id=session_id,
                stream=True,
            )

            async def _stream_with_timeout():
                try:
                    async with asyncio.timeout(timeout):
                        async for chunk in raw_stream:
                            yield chunk
                except asyncio.TimeoutError as exc:
                    logger.error(
                        f"Agent stream timed out: {agent_instance.id} | session_id: {session_id}"
                    )
                    raise ModelProviderError(
                        message="Model zaman aşımına uğradı",
                        detail="Streaming cevabı belirtilen süre içinde tamamlanamadı",
                    ) from exc

            return _stream_with_timeout()

        async with asyncio.timeout(timeout):
            run: RunOutput = await agent_instance.arun(
                input=message,
                user_id=user_id,
                session_id=session_id,
            )
        logger.info(f"Agent run completed: {agent_instance.id}")
        return run
    except asyncio.TimeoutError as exc:
        logger.error(
            f"Agent run timed out: {getattr(agent_instance, 'id', 'unknown')} | "
            f"session_id: {session_id}"
        )
        raise ModelProviderError(
            message="Model zaman aşımına uğradı",
            detail="Cevap süresi belirlenen sınırı aştı",
        ) from exc
    except Exception as e:
        logger.error(
            f"Agent run failed: {getattr(agent, 'id', 'unknown')} | Error: {str(e)}",
            exc_info=True,
        )
        raise ModelProviderError(
            message="Model çalıştırılamadı",
            detail=str(e),
        )


def extract_agent_reply(run: RunOutput, agent_id: str) -> str:
    """
    Agent çıktısından reply string'ini çıkarır.
    
    Args:
        run: Agent run output
        agent_id: Agent ID
    
    Returns:
        str: Reply metni
    """
    if agent_id == AgentID.SATINALMA_PDF.value:
        out = getattr(run, "output", None) or getattr(run, "content", None)
        
        if isinstance(out, SatinalmaReply):
            return out.reply
        elif isinstance(out, str):
            return out
        else:
            return str(run.content) if run.content else ""
    else:
        return str(run.content) if run.content else ""


async def process_email_confirmation(
    req: ChatMessageRequest,
    pending_data: Dict[str, Any],
) -> Tuple[ChatMessageResponse, Optional[dict]]:
    suggestion: SatinalmaReply = pending_data["suggestion"]
    agent_reply: str = pending_data.get("agent_reply", suggestion.reply)
    source_message: str = pending_data.get("source_message", "")

    email_prompt = _build_email_prompt(
        user_id=req.user_id,
        session_id=req.session_id,
        source_message=source_message,
        agent_reply=agent_reply,
        suggestion=suggestion,
    )

    orchestrator_run = await run_agent(
        agent=orchestrator_agent,
        message=email_prompt,
        user_id=req.user_id,
        session_id=req.session_id,
    )

    orchestrator_reply = orchestrator_run.content

    email_info = {
        "orchestrator_reply": orchestrator_reply,
        "recipient_hint": suggestion.email_recipient_hint,
        "subject_suggestion": suggestion.email_subject_suggestion,
    }

    combined_reply = (
        "Onayınız için teşekkürler. Taslak mail aşağıdaki içerikle gönderildi:\n\n"
        f"{agent_reply}\n\n---\n{orchestrator_reply}"
    )

    response = ChatMessageResponse(
        reply=combined_reply,
        email_triggered=True,
        email_info=email_info,
    )

    structured_dump = suggestion.model_dump()
    return response, structured_dump


def process_email_cancellation(
    session_id: str, pending_data: Dict[str, Any]
) -> Tuple[ChatMessageResponse, Optional[dict]]:
    suggestion: Optional[SatinalmaReply] = pending_data.get("suggestion")
    reply_text = (
        "Mail taslağı gönderilmeden iptal edildi. "
        "İstersen yeni talimat vererek güncel bir taslak oluşturabilirsin."
    )
    response = ChatMessageResponse(reply=reply_text, email_triggered=False)
    structured_dump = suggestion.model_dump() if suggestion else None
    logger.info(f"Pending email cancelled | session_id: {session_id}")
    return response, structured_dump
