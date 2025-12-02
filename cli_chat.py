import os
import sys
import json
from pathlib import Path

import requests


class ChatCLI:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session_id = None
        self.assigned_agent_id = None
        self.user_id = None

    def start_session(self, user_id: str, message: str, stream: bool = True):
        url = f"{self.base_url}/api/chat/start"
        payload = {"user_id": user_id, "message": message, "stream": stream}
        
        if stream:
            resp = requests.post(url, json=payload, stream=True, timeout=30)
            resp.raise_for_status()
            
            # Process stream to find session info and print content
            print("Atanan agent: ", end="", flush=True) # Will be filled when session info arrives
            
            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        try:
                            data = json.loads(data_str)
                            
                            if data.get("type") == "session_info":
                                self.session_id = data["session_id"]
                                self.assigned_agent_id = data["assigned_agent_id"]
                                print(f"{data['assigned_agent_name']}\nCevap: ", end="", flush=True)
                                
                            elif "content" in data:
                                print(data["content"], end="", flush=True)
                                
                            elif data.get("type") == "end":
                                metrics = data.get("metrics", {})
                                print(f"\n[Gecikme] İlk Token: {metrics.get('first_token', 0):.2f}s, Toplam: {metrics.get('total', 0):.2f}s")
                                
                            elif "error" in data:
                                print(f"\nHata: {data['error']}")
                                
                        except json.JSONDecodeError:
                            pass
            print()
            return {"session_id": self.session_id, "assigned_agent_id": self.assigned_agent_id}
        else:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self.session_id = data["session_id"]
            self.assigned_agent_id = data["assigned_agent_id"]
            return data

    def send_message(self, message: str, stream: bool = True):
        if not self.session_id or not self.assigned_agent_id:
            raise RuntimeError("Önce oturumu başlatın")
        url = f"{self.base_url}/api/chat/agents/{self.assigned_agent_id}"
        payload = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "message": message,
            "stream": stream,
        }
        resp = requests.post(url, json=payload, stream=stream, timeout=30)
        resp.raise_for_status()
        return resp

    def conversation_log_path(self):
        if not self.session_id:
            return None
        logs_dir = os.getenv("CONVERSATION_LOGS_DIR", "data/conversations")
        return Path(logs_dir) / f"{self.session_id}.jsonl"


def main():
    base_url = os.getenv("CHAT_API_BASE_URL", "http://127.0.0.1:8000")
    cli = ChatCLI(base_url)
    print(f"API: {base_url}")
    user_id = input("User ID: ").strip()
    if not user_id:
        print("User ID boş olamaz")
        sys.exit(1)
    cli.user_id = user_id
    print("Çıkmak için ctrl+c veya boş mesaj")
    try:
        initial = input("İlk mesaj: ").strip()
        if not initial:
            print("İlk mesaj boş olamaz")
            return
        start_data = cli.start_session(user_id, initial)
        # print("Atanan agent:", start_data["assigned_agent_name"]) # Handled in start_session
        # print("Cevap:", start_data["reply"]) # Handled in start_session
        log_path = cli.conversation_log_path()
        if log_path:
            print(f"Log dosyası: {log_path}")
        while True:
            msg = input("Mesaj: ").strip()
            if not msg:
                print("Boş girdin, çıkış yapılıyor")
                break
            
            response = cli.send_message(msg)
            
            # Check content type to decide how to handle response
            content_type = response.headers.get("content-type", "")
            
            if "text/event-stream" in content_type:
                print("Agent: ", end="", flush=True)
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:]
                            try:
                                data = json.loads(data_str)
                                if "content" in data:
                                    print(data["content"], end="", flush=True)
                                elif data.get("type") == "end":
                                    metrics = data.get("metrics", {})
                                    print(f"\n[Gecikme] İlk Token: {metrics.get('first_token', 0):.2f}s, Toplam: {metrics.get('total', 0):.2f}s")
                                elif "error" in data:
                                    print(f"\nHata: {data['error']}")
                            except json.JSONDecodeError:
                                pass
                print()
            else:
                data = response.json()
                print("Agent:", data["reply"])
                if data.get("email_triggered"):
                    print("Email bilgisi:", json.dumps(data.get("email_info"), ensure_ascii=False))
    except KeyboardInterrupt:
        print("\nÇıkış yapıldı")
    except requests.HTTPError as http_err:
        print("HTTP Hatası:", http_err.response.status_code, http_err.response.text)
    except Exception as exc:
        print("Hata:", exc)


if __name__ == "__main__":
    main()

