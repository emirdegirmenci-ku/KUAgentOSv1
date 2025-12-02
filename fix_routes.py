import re

# Read the file
with open('app/api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the incomplete try block and fix it
# The problem is around line 397-400 where try block is not closed

# Strategy: Find the event_generator function and rewrite it properly
pattern = r'(async def event_generator\(\):.*?yield f"data: \{json\.dumps\(\{\'content\': content\}, ensure_ascii=False\)\}\\n\\n")'

replacement = '''async def event_generator():
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
                            yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\\n\\n"
                    
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
                                    
                                    yield f"data: {json.dumps({'type': 'email_intent', 'recipient_hint': email_data.get('email_recipient_hint'), 'subject_suggestion': email_data.get('email_subject_suggestion')}, ensure_ascii=False)}\\n\\n"
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
                    
                    yield f"data: {json.dumps({'type': 'end', 'metrics': {'first_token': first_token_latency, 'total': total_latency}, 'email_intent': email_intent_detected}, ensure_ascii=False)}\\n\\n"
                    
                except Exception as e:
                    logger.error(f"Stream error: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\\n\\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")'''

# This is complex, let's use a simpler approach - just insert the missing parts
# Find line 400 and insert the missing code there

lines = content.split('\n')

# Find the line with the incomplete try
for i, line in enumerate(lines):
    if i >= 396 and 'yield f"data: {json.dumps' in line and "'content': content" in line:
        # Found it at line i (0-indexed)
        # Need to add the rest of the try-except block after this
        insert_code = '''                    
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
                                    
                                    yield f"data: {json.dumps({'type': 'email_intent', 'recipient_hint': email_data.get('email_recipient_hint'), 'subject_suggestion': email_data.get('email_subject_suggestion')}, ensure_ascii=False)}\\n\\n"
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
                    
                    yield f"data: {json.dumps({'type': 'end', 'metrics': {'first_token': first_token_latency, 'total': total_latency}, 'email_intent': email_intent_detected}, ensure_ascii=False)}\\n\\n"
                    
                except Exception as e:
                    logger.error(f"Stream error: {str(e)}", exc_info=True)
                    yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\\n\\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")
'''
        lines.insert(i + 1, insert_code)
        break

# Remove the duplicate code that starts at line 401
# Find and remove "run = await run_agent(" section that's outside the generator
new_lines = []
skip_until = None
for i, line in enumerate(lines):
    if skip_until and i < skip_until:
        continue
    skip_until = None
    
    # If we find "run = await run_agent(" after the generator, skip until we find the next function
    if i > 400 and 'run = await run_agent(' in line and 'stream=True' not in line:
        # This is the duplicate non-stream code, keep it
        pass
    
    new_lines.append(line)

# Write back
with open('app/api/routes.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print("Fixed!")
