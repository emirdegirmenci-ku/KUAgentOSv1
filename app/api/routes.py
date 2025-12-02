# app/api/routes.py
"""
Chat API endpoints.
Kullanıcı-agent etkileşimi için REST API endpoint'leri.
"""
import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import time
import json

from app.agents.orchestrator_agent import orchestrator_agent, RoutingResponse
from app.agents.satinalma_agent import satinalma_agent, SatinalmaReply
from app.api.schemas import (
    StartChatRequest,
    StartChatResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.api.services import (
    run_agent,
    extract_agent_reply,
    process_email_confirmation,
    process_email_cancellation,
    is_cancel_message,
    is_confirmation_message,
    CONFIRMATION_HINT,
)
from app.configs.agent_ids import AgentID, get_agent_display_name
from app.configs.exceptions import (
    AgentNotFoundError,
    InvalidAgentIDError,
    RoutingError,
    ModelProviderError,
)
from app.utils.conversation_logger import log_event

# Logger ayarla
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


# ==== Domain Agent Registry ====
# Centralized agent registry - yeni agent eklerken buraya ekle
DOMAIN_AGENTS: Dict[str, object] = {
    AgentID.SATINALMA_PDF.value: satinalma_agent,
    # İleride eklenecekler:
    # AgentID.HR_PDF.value: hr_agent,
    # AgentID.IT_PDF.value: it_agent,
}

# Pending email confirmations: session_id -> data
PENDING_EMAILS: Dict[str, Dict[str, Any]] = {}


# ==== API Endpoints ====

@router.post(
    "/chat/start",
    response_model=StartChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni chat session başlat",
    description=(
        "Kullanıcının ilk mesajı ile yeni bir chat session başlatır. "
        "Orchestrator mesajı analiz eder ve uygun domain agent'ına yönlendirir. "
        "Seçilen agent ile ilk cevap da bu endpoint'te üretilir."
    ),
)
async def start_chat(req: StartChatRequest) -> Any:
    """
    Yeni chat session başlatır.
    
    İş Akışı:
    1. Orchestrator'a ROUTING modunda gönder
    2. Orchestrator uygun agent_id'yi JSON olarak döner
    3. Seçilen agent ile ilk cevap üretilir
    4. Session ID ve cevap döndürülür
    
    Raises:
        HTTPException: Routing hatası veya agent bulunamadığında
    """
    try:
        # Yeni session ID oluştur
        session_id = str(uuid.uuid4())
        logger.info(
            f"Starting new chat session | user_id: {req.user_id} | session_id: {session_id}"
        )
        await log_event(
            session_id=session_id,
            event="start_chat_request",
            payload={"user_id": req.user_id, "message": req.message},
        )
        
        # Orchestrator'a ROUTING modunda prompt
        routing_prompt = (
            "MODE: ROUTING\n\n"
            f"USER_ID: {req.user_id}\n\n"
            "Kullanıcıdan gelen mesaj aşağıdadır. "
            "JSON formatında hangi agent'ın cevaplaması gerektiğini döndür.\n\n"
            f"USER_MESSAGE:\n{req.message}"
        )
        
        # Orchestrator run
        routing_run = await run_agent(
            agent=orchestrator_agent,
            message=routing_prompt,
            user_id=req.user_id,
            session_id=session_id,
        )
        
        # Parse routing response (Structured Output)
        routing_output = getattr(routing_run, "output", None) or getattr(routing_run, "content", None)
        
        target_agent_id = ""
        reason = ""
        
        if isinstance(routing_output, RoutingResponse):
            target_agent_id = routing_output.target_agent_id
            reason = routing_output.reason
        elif isinstance(routing_output, dict):
             target_agent_id = routing_output.get("target_agent_id")
             reason = routing_output.get("reason")
        else:
            # Fallback for unexpected types (though output_schema should prevent this)
            logger.error(f"Unexpected routing output type: {type(routing_output)}")
            raise RoutingError(message="Yönlendirme yanıtı anlaşılamadı")
        
        # Agent validation
        if not target_agent_id or target_agent_id not in DOMAIN_AGENTS:
            logger.error(f"Invalid agent ID from routing: {target_agent_id}")
            raise AgentNotFoundError(
                message=f"Geçersiz agent ID: {target_agent_id}",
                detail="Orchestrator geçersiz bir agent ID döndürdü",
            )
        
        logger.info(f"Routed to agent: {target_agent_id} | reason: {reason}")
        
        # Seçilen agent ile ilk cevap
        domain_agent = DOMAIN_AGENTS[target_agent_id]
        
        if req.stream:
            async def event_generator():
                # Send session info first
                yield f"data: {json.dumps({'type': 'session_info', 'session_id': session_id, 'assigned_agent_id': target_agent_id, 'assigned_agent_name': get_agent_display_name(target_agent_id), 'routing_reason': reason}, ensure_ascii=False)}\n\n"
                
                start_time = time.time()
                first_token_time = None
                full_response = ""
                
                try:
                    gen = await run_agent(
                        agent=domain_agent,
                        message=req.message,
                        user_id=req.user_id,
                        session_id=session_id,
                        stream=True,
                    )
                    
                    async for chunk in gen:
                        if first_token_time is None:
                            first_token_time = time.time()
                        
                        content = ""
                        if hasattr(chunk, "content"):
                            content = chunk.content
                        elif isinstance(chunk, str):
                            content = chunk
                        
                        if content:
                            full_response += content
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                    
                    end_time = time.time()
                    first_token_latency = (first_token_time - start_time) if first_token_time else (end_time - start_time)
                    total_latency = end_time - start_time
                    
                    # Log metrics
                    await log_event(
                        session_id=session_id,
                        event="start_chat_stream_metrics",
                        payload={
                            "agent_id": target_agent_id,
                            "first_token_latency": first_token_latency,
                            "total_latency": total_latency,
                            "full_response": full_response
                        },
                    )
                    
                    # Send end event with metrics
                    yield f"data: {json.dumps({'type': 'end', 'metrics': {'first_token': first_token_latency, 'total': total_latency}}, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    logger.error(f"Stream error: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        start_time = time.time()
        domain_run = await run_agent(
            agent=domain_agent,
            message=req.message,
            user_id=req.user_id,
            session_id=session_id,
        )
        end_time = time.time()
        total_latency = end_time - start_time
        
        # Extract reply
        reply_text = extract_agent_reply(domain_run, target_agent_id)
        if target_agent_id == AgentID.SATINALMA_PDF.value:
            domain_output = getattr(domain_run, "output", None) or getattr(
                domain_run, "content", None
            )
            if isinstance(domain_output, SatinalmaReply) and domain_output.email_intent:
                PENDING_EMAILS[session_id] = {
                    "suggestion": domain_output,
                    "agent_reply": domain_output.reply,
                    "source_message": req.message,
                }
                if CONFIRMATION_HINT.lower() not in reply_text.lower():
                    reply_text = f"{reply_text}\n\n---\n{CONFIRMATION_HINT}"
                logger.info(
                    "Email intent detected during start_chat; awaiting confirmation"
                )
        
        logger.info(f"Chat session started successfully | session_id: {session_id}")
        response = StartChatResponse(
            session_id=session_id,
            assigned_agent_id=target_agent_id,
            assigned_agent_name=get_agent_display_name(target_agent_id),
            routing_reason=reason,
            reply=reply_text,
            latency_seconds=total_latency,
        )
        await log_event(
            session_id=session_id,
            event="start_chat_response",
            payload={
                "assigned_agent_id": target_agent_id,
                "assigned_agent_name": response.assigned_agent_name,
                "routing_reason": reason,
                "reply": reply_text,
            },
        )
        return response
        
    except (AgentNotFoundError, InvalidAgentIDError, RoutingError) as e:
        logger.error(f"Chat start failed: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except ModelProviderError as e:
        logger.error(f"Model provider error: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI servisi şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in start_chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.",
        )


@router.post(
    "/chat/agents/{agent_id}",
    response_model=ChatMessageResponse,
    summary="Mevcut session'da mesaj gönder",
    description=(
        "Kullanıcı seçilen domain agent ile konuşmaya devam eder. "
        "Eğer agent email_intent=True dönerse önce taslak kullanıcıya sunulur, "
        "açık onay alındığında orchestrator EMAIL modunda çağrılarak mail gönderilir."
    ),
)
async def chat_with_agent(agent_id: str, req: ChatMessageRequest) -> Any:
    """
    Mevcut session'da domain agent ile konuşma.
    
    İş Akışı:
    1. Agent ID validasyonu
    2. Domain agent'a mesaj gönder
    3. Structured output kontrol et
    4. Eğer email_intent=True ise:
       - Orchestrator EMAIL modunda çağır
       - Mail tool'u çağır
       - Kullanıcıya bilgi ver
    
    Args:
        agent_id: Domain agent ID (URL path'den)
        req: Chat message request
    
    Returns:
        ChatMessageResponse: Agent cevabı ve mail bilgisi
    
    Raises:
        HTTPException: Agent bulunamadığında veya hata durumunda
    """
    try:
        logger.info(
            f"Chat message | agent_id: {agent_id} | user_id: {req.user_id} | "
            f"session_id: {req.session_id}"
        )
        await log_event(
            session_id=req.session_id,
            event="chat_message_request",
            payload={
                "agent_id": agent_id,
                "user_id": req.user_id,
                "message": req.message,
            },
        )
        
        # Agent validation
        if agent_id not in DOMAIN_AGENTS:
            logger.warning(f"Agent not found: {agent_id}")
            raise AgentNotFoundError(
                message=f"Agent bulunamadı: {agent_id}",
                detail=f"Mevcut agent'lar: {', '.join(DOMAIN_AGENTS.keys())}",
            )
        
        agent = DOMAIN_AGENTS[agent_id]

        pending_email = PENDING_EMAILS.get(req.session_id)
        if pending_email:
            if is_cancel_message(req.message):
                PENDING_EMAILS.pop(req.session_id, None)
                response, structured_dump = process_email_cancellation(
                    session_id=req.session_id,
                    pending_data=pending_email,
                )
                await log_event(
                    session_id=req.session_id,
                    event="chat_message_response",
                    payload={
                        "agent_id": agent_id,
                        "reply": response.reply,
                        "email_triggered": response.email_triggered,
                        "email_info": response.email_info,
                        "structured_output": structured_dump,
                    },
                )
                return response

            if is_confirmation_message(req.message):
                PENDING_EMAILS.pop(req.session_id, None)
                response, structured_dump = await process_email_confirmation(
                    req=req,
                    pending_data=pending_email,
                )
                logger.info(
                    f"Email confirmation received | session_id: {req.session_id}"
                )
                await log_event(
                    session_id=req.session_id,
                    event="chat_message_response",
                    payload={
                        "agent_id": agent_id,
                        "reply": response.reply,
                        "email_triggered": response.email_triggered,
                        "email_info": response.email_info,
                        "structured_output": structured_dump,
                    },
                )
                return response

            # Yeni talimat geldi, eski pending taslağı temizle
            PENDING_EMAILS.pop(req.session_id, None)

        # Agent run
        if req.stream:
            async def event_generator():
                start_time = time.time()
                first_token_time = None
                full_response = ""
                
                try:
                    gen = await run_agent(
                        agent=agent,
                        message=req.message,
                        user_id=req.user_id,
                        session_id=req.session_id,
                        stream=True,
                    )
                    
                    async for chunk in gen:
                        if first_token_time is None:
                            first_token_time = time.time()
                        
                        content = ""
                        if hasattr(chunk, "content"):
                            content = chunk.content
                        elif isinstance(chunk, str):
                            content = chunk
                        
                        if content:
                            full_response += content
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                    
                    end_time = time.time()
                    first_token_latency = (first_token_time - start_time) if first_token_time else (end_time - start_time)
                    total_latency = end_time - start_time
                    
                    # Parse JSON for email intent
                    email_intent_detected = False
                    if agent_id == AgentID.SATINALMA_PDF.value and full_response:
                        try:
                            if "---JSON---" in full_response and "---END---" in full_response:
                                json_start = full_response.find("---JSON---") + len("---JSON---")
                                json_end = full_response.find("---END---")
                                json_str = full_response[json_start:json_end].strip()
                                
                                email_data = json.loads(json_str)
                                
                                if email_data.get("email_intent"):
                                    email_intent_detected = True
                                    PENDING_EMAILS[req.session_id] = {
                                        "suggestion": email_data,
                                        "agent_reply": full_response[:json_start - len("---JSON---")].strip(),
                                        "source_message": req.message,
                                    }
                                    logger.info("Email intent detected from stream JSON")
                                    
                                    yield f"data: {json.dumps({'type': 'email_intent', 'recipient_hint': email_data.get('email_recipient_hint'), 'subject_suggestion': email_data.get('email_subject_suggestion')}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.error(f"JSON parsing error: {str(e)}")
                    
                    # Log metrics
                    await log_event(
                        session_id=req.session_id,
                        event="chat_message_stream_metrics",
                        payload={
                            "agent_id": agent_id,
                            "first_token_latency": first_token_latency,
                            "total_latency": total_latency,
                            "full_response": full_response,
                            "email_intent_detected": email_intent_detected
                        },
                    )
                    
                    yield f"data: {json.dumps({'type': 'end', 'metrics': {'first_token': first_token_latency, 'total': total_latency}, 'email_intent': email_intent_detected}, ensure_ascii=False)}\n\n"
                    
                except Exception as e:
                    logger.error(f"Stream error: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")


        run = await run_agent(
            agent=agent,
            message=req.message,
            user_id=req.user_id,
            session_id=req.session_id,
        )
        
        # Response variables
        reply_text: str = ""
        email_triggered = False
        email_info: Optional[dict] = None
        
        # Structured output handling - satınalma agent için
        structured_dump: Optional[dict] = None
        if agent_id == AgentID.SATINALMA_PDF.value:
            out = getattr(run, "output", None) or getattr(run, "content", None)
            
            if isinstance(out, SatinalmaReply):
                reply_text = out.reply
                structured_dump = out.model_dump()
                
                # Email intent check
                if out.email_intent:
                    PENDING_EMAILS[req.session_id] = {
                        "suggestion": out,
                        "agent_reply": out.reply,
                        "source_message": req.message,
                    }
                    if CONFIRMATION_HINT.lower() not in out.reply.lower():
                        reply_text = f"{out.reply}\n\n---\n{CONFIRMATION_HINT}"
                    email_info = {
                        "pending_confirmation": True,
                        "recipient_hint": out.email_recipient_hint,
                        "subject_suggestion": out.email_subject_suggestion,
                    }
                    logger.info(
                        "Email intent detected, awaiting user confirmation before sending"
                    )
                    
            elif isinstance(out, str):
                reply_text = out
            else:
                reply_text = str(run.content) if run.content else ""
        else:
            # Diğer agent'lar için normal string content
            reply_text = str(run.content) if run.content else ""
        
        # Calculate latency (approximate for non-stream)
        # We don't have exact first token time here, but we can log total time if we measured it.
        # But run_agent doesn't return time.
        # I'll skip latency logging for non-stream for now as user emphasized "stream chat ekle... ilk token gelene kadar gecikme sayılsın"
        
        logger.info(
            f"Chat message completed | agent_id: {agent_id} | email_triggered: {email_triggered}"
        )
        
        response = ChatMessageResponse(
            reply=reply_text,
            email_triggered=email_triggered,
            email_info=email_info,
        )
        await log_event(
            session_id=req.session_id,
            event="chat_message_response",
            payload={
                "agent_id": agent_id,
                "reply": reply_text,
                "email_triggered": email_triggered,
                "email_info": email_info,
                "structured_output": structured_dump,
            },
        )
        return response
        
    except AgentNotFoundError as e:
        logger.error(f"Agent not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except ModelProviderError as e:
        logger.error(f"Model provider error: {e.message}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI servisi şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat_with_agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.",
        )


@router.get(
    "/health",
    summary="API health check",
    description="API'nin çalışır durumda olup olmadığını kontrol eder",
)
def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "available_agents": list(DOMAIN_AGENTS.keys()),
    }
