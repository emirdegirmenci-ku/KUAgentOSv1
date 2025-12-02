# Örnek: Streaming sırasında JSON parsing

# Agent instructions'ı güncelle
SATINALMA_AGENT_INSTRUCTIONS = """
Sen bir kurumsal satınalma chatbotusun.
...

ÖNEMLI: Yanıtının SONUNDA şu formatta JSON ekle:
---JSON---
{"email_intent": true/false, "email_recipient_hint": "...", "email_subject": "...", "email_body": "..."}
---END---
"""

# Stream işleme
async def event_generator():
    full_response = ""
    
    async for chunk in gen:
        content = chunk.content
        full_response += content
        yield f"data: {json.dumps({'content': content})}\\n\\n"
    
    # Stream bitti, JSON'ı parse et
    if "---JSON---" in full_response:
        # JSON kısmını ayıkla
        json_start = full_response.find("---JSON---") + len("---JSON---")
        json_end = full_response.find("---END---")
        json_str = full_response[json_start:json_end].strip()
        
        try:
            email_data = json.loads(json_str)
            
            if email_data.get("email_intent"):
                # Email intent var!
                PENDING_EMAILS[session_id] = {
                    "suggestion": email_data,
                    "agent_reply": full_response,
                    "source_message": req.message,
                }
                
                # Client'a bildir
                yield f"data: {json.dumps({'type': 'email_intent', 'data': email_data})}\\n\\n"
        except json.JSONDecodeError:
            logger.error("JSON parse hatası")
    
    yield f"data: {json.dumps({'type': 'end', 'metrics': {...}})}\\n\\n"
