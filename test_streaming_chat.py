import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"
USER_ID = "test_user_123"

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def process_stream(response, label="Agent"):
    """Stream yanıtını işle ve metrikleri hesapla"""
    print(f"\n{label}: ", end="", flush=True)
    
    start_time = time.time()
    first_token_time = None
    full_content = ""
    email_intent_data = None
    server_metrics = {}
    
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode("utf-8")
            if decoded_line.startswith("data: "):
                data_str = decoded_line[6:]
                try:
                    data = json.loads(data_str)
                    
                    # 1. İçerik (Token)
                    if "content" in data:
                        if first_token_time is None:
                            first_token_time = time.time()
                        content = data["content"]
                        print(content, end="", flush=True)
                        full_content += content
                    
                    # 2. Session Info (Start Chat)
                    elif data.get("type") == "session_info":
                        # print(f"\n[Info] Session: {data.get('session_id')} | Agent: {data.get('assigned_agent_name')}")
                        pass
                        
                    # 3. Email Intent (Bizim eklediğimiz JSON parsing)
                    elif data.get("type") == "email_intent":
                        email_intent_data = data
                        print(f"\n\n[📧 EMAIL INTENT TESPİT EDİLDİ!]")
                        print(f"  • Alıcı: {data.get('recipient_hint')}")
                        print(f"  • Konu: {data.get('subject_suggestion')}")
                        
                    # 4. Bitiş ve Metrikler
                    elif data.get("type") == "end":
                        server_metrics = data.get("metrics", {})
                        
                    elif "error" in data:
                        print(f"\n[HATA] {data['error']}")
                        
                except json.JSONDecodeError:
                    pass
    
    end_time = time.time()
    print("\n" + "-"*60)
    
    # Client-side Metrikler
    ttft = (first_token_time - start_time) if first_token_time else 0
    total_time = end_time - start_time
    token_count = len(full_content.split()) # Yaklaşık kelime sayısı
    tokens_per_sec = token_count / total_time if total_time > 0 else 0
    
    print(f"📊 PERFORMANS ANALİZİ")
    print(f"  • İstemci TTFT (İlk Token): {ttft:.4f}s")
    print(f"  • Sunucu  TTFT            : {server_metrics.get('first_token', 0):.4f}s")
    print(f"  • Toplam Süre             : {total_time:.4f}s")
    print(f"  • Hız (yaklaşık)          : {tokens_per_sec:.1f} kelime/s")
    
    if email_intent_data:
        print(f"  • Email Intent            : ✅ BAŞARILI")
    else:
        print(f"  • Email Intent            : ❌ Yok (Normal)")
        
    return full_content, email_intent_data

def run_test():
    # 1. Health Check
    try:
        requests.get(f"{BASE_URL}/api/health")
    except requests.exceptions.ConnectionError:
        print("❌ HATA: Sunucu çalışmıyor! Lütfen ayrı bir terminalde 'python run.py' çalıştırın.")
        return

    print_header("TEST 1: NORMAL SORU (Start Chat + Stream)")
    msg1 = "Araç kiralama hizmet alımı için en az kaç teklif gereklidir ve bu hangi maddede yazar?"
    print(f"Soru: {msg1}")
    
    url_start = f"{BASE_URL}/api/chat/start"
    payload_start = {"user_id": USER_ID, "message": msg1, "stream": True}
    
    with requests.post(url_start, json=payload_start, stream=True) as r:
        # Session ID'yi stream içinden veya response header'dan alamıyoruz, 
        # ama start_chat stream modunda session_info event'i atıyor.
        # Basitlik için burada parse etmeyeceğiz, normal chat endpoint'ini test etmek için
        # önce non-stream bir start yapıp session alalım, sonra stream test edelim.
        pass

    # Daha sağlıklı test için: Önce session başlat (non-stream), sonra stream mesaj at
    print("\n...Session başlatılıyor (Setup)...")
    r = requests.post(url_start, json={"user_id": USER_ID, "message": "Merhaba", "stream": False})
    data = r.json()
    session_id = data["session_id"]
    agent_id = data["assigned_agent_id"]
    print(f"Session ID: {session_id} | Agent: {agent_id}")
    
    # TEST 1: Gerçek Soru
    print_header("TEST 1: MEVZUAT SORUSU (Streaming)")
    print(f"Soru: {msg1}")
    
    url_chat = f"{BASE_URL}/api/chat/agents/{agent_id}"
    payload_chat = {"user_id": USER_ID, "session_id": session_id, "message": msg1, "stream": True}
    
    with requests.post(url_chat, json=payload_chat, stream=True) as r:
        process_stream(r)
        
    # TEST 2: Email Intent
    print_header("TEST 2: EMAIL INTENT (Streaming + JSON Parsing)")
    msg2 = "Bu konuda satınalma birimine bir mail taslağı hazırlar mısın?"
    print(f"Soru: {msg2}")
    
    payload_chat["message"] = msg2
    
    with requests.post(url_chat, json=payload_chat, stream=True) as r:
        _, email_data = process_stream(r)
        
    if email_data:
        print("\n✅ TEST BAŞARILI: Hem streaming hem email intent çalışıyor!")
    else:
        print("\n⚠️ UYARI: Email intent tespit edilemedi.")

if __name__ == "__main__":
    run_test()
