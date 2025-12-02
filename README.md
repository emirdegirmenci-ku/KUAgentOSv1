# KUAgentOS - Enterprise PDF Chatbot System

Enterprise-grade multi-agent chatbot sistemi. Google Vertex AI ve Gemini kullanarak kullanıcı sorgularını ilgili domain agent'larına yönlendirir ve otomatik mail gönderimi sağlar.

## 🏗️ Mimari

### Temel Bileşenler

1. **Orchestrator Agent**: Kullanıcı sorgularını analiz eder ve uygun domain agent'ına yönlendirir
2. **Domain Agent'lar**: Spesifik alanlarda uzmanlaşmış agent'lar (örn: Satınalma)
3. **Mail Tools**: Email gönderimi için toolkit (şu an mock/logging modu)
4. **Session Yönetimi**: SQLite tabanlı conversation history

### Agent Yapısı

```
┌─────────────────┐
│   Kullanıcı     │
└────────┬────────┘
         │
         v
┌────────────────────┐
│  Orchestrator      │  (ROUTING modu)
│  Agent             │
└────────┬───────────┘
         │
         v
┌────────────────────┐
│  Domain Agent      │  (Satınalma, HR, IT...)
│  (structured out)  │
└────────┬───────────┘
         │
         v (email_intent = true)
┌────────────────────┐
│  Orchestrator      │  (EMAIL modu)
│  + Mail Tools      │
└────────────────────┘
```

## 🚀 Kurulum

### Gereksinimler

- Python 3.9+
- Google Cloud hesabı
- Vertex AI API erişimi
- Service Account JSON key

### Adımlar

1. **Repository'yi klonlayın**
   ```bash
   git clone <repository-url>
   cd KUAgentOS
   ```

2. **Virtual environment oluşturun**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Bağımlılıkları yükleyin**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment dosyasını ayarlayın**
   
   `.env` dosyasını düzenleyin:
   ```env
   # Google Cloud Ayarları
   GOOGLE_APPLICATION_CREDENTIALS=service_account.json
   PROJECT_ID=your-project-id
   LOCATION=us-central1
   
   # Vertex AI Search
   DATA_STORE_ID=your-datastore-id
   DATA_STORE_LOCATION=global
   GCS_BUCKET_NAME=your-bucket-name
   
   # Model Ayarları
   GEMINI_MODEL_NAME=gemini-2.5-flash
   
   # Database
   AGNO_SQLITE_DB_FILE=data/agent_sessions.db
   
   # Security
   OS_SECURITY_KEY=your-random-secure-key
   
   # Mail Ayarları
   MAIL_SENDER_NAME=Chatbot Assistant
   MAIL_SENDER_EMAIL=no-reply@example.com
   MAIL_DEFAULT_RECIPIENT=support@example.com

    # Prompt talimatları (tek satırlık string; \n ile satır sonu ekleyebilirsiniz)
    SATINALMA_AGENT_INSTRUCTIONS="Sen bir kurumsal satınalma chatbotusun.\nSadece satınalma süreçleri, tedarik, teklif ve onay akışları hakkında konuş.\nKurallar:\n- Cevapları mutlaka TÜRKÇE ver.\n- Politika ve prosedür isimlerini ve mümkünse madde numaralarını belirt.\n- Mail talebinde konu ve gövdeyi kullanıcıya açıkça göster, sonunda 'gönder' yazarak onay verebileceğini belirt.\n- Onay gelmeden mail gönderme; revize isteğini uygula ve tekrar onay iste.\nNormal sorularda email_intent=false olmalı."
    ORCHESTRATOR_AGENT_INSTRUCTIONS="Sen bir orkestratör agentsın.\nROUTING modunda ilk mesajı analiz et ve sadece {\"mode\":\"ROUTING\",\"target_agent_id\":\"...\",\"reason\":\"...\"} formatında JSON döndür.\nEMAIL modunda domain agent'ın verdiği taslağı profesyonel hale getir, mail_tools.send_email fonksiyonunu bir kez çağır ve ardından kullanıcıya Türkçe bir onay mesajı yaz.\nROUTING modunda markdown veya ek açıklama kullanma.\nEMAIL modunda tool çağrısından sonra kısa bir özet ver."
   ```

5. **Service Account JSON'u yerleştirin**
   
   Google Cloud service account key'inizi proje root'una `service_account.json` olarak kaydedin.

## 🎯 Kullanım

### Sunucuyu Başlatma

```bash
# Development modu
python run.py

# Veya doğrudan uvicorn ile
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### 1. Health Check
```bash
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "available_agents": ["satinalma-pdf-agent"]
}
```

#### 2. Yeni Chat Session Başlat
```bash
POST /api/chat/start
```

**Request:**
```json
{
  "user_id": "ahmet.yilmaz",
  "message": "Satınalma talebi nasıl oluşturulur?"
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_agent_id": "satinalma-pdf-agent",
  "assigned_agent_name": "Satınalma Asistanı",
  "routing_reason": "Kullanıcı satınalma süreci hakkında soru sordu",
  "reply": "Satınalma talebi oluşturmak için..."
}
```

#### 3. Mevcut Session'da Mesaj Gönder
```bash
POST /api/chat/agents/{agent_id}
```

**Request:**
```json
{
  "user_id": "ahmet.yilmaz",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Bu konu hakkında satınalma müdürlüğüne mail gönder"
}
```

**Response:**
```json
{
  "reply": "Elbette, mailiniz hazırlandı...\n\n---\nMailiniz Satınalma Müdürlüğü'ne iletildi.",
  "email_triggered": true,
  "email_info": {
    "orchestrator_reply": "Mailiniz başarıyla gönderildi.",
    "recipient_hint": "Satınalma Müdürlüğü",
    "subject_suggestion": "Satınalma Talebi Hk."
  }
}
```

### CLI Test Aracı

Yerel geliştirmede sohbet akışını hızlıca denemek için CLI'ı kullanabilirsiniz:

```bash
python cli_chat.py
```

İlk çalıştırmada `user_id` ve ilk mesaj sorulur, aynı `session_id` ile konuşma devam eder. Pending mail onayları için CLI üzerinden "gönder", "revize" vb. komutları deneyebilirsiniz. Varsayılan API adresini `CHAT_API_BASE_URL` ortam değişkeniyle değiştirebilirsiniz.

Detaylı cURL/Python örnekleri için `docs/API_EXAMPLES.md` dosyasına bakabilirsiniz.

├── run.py                   # Uvicorn runner
└── README.md
```

## 🔧 Yeni Agent Ekleme

### 1. Agent ID Tanımlayın

`app/configs/agent_ids.py`:
```python
class AgentID(str, Enum):
    ORCHESTRATOR = "orchestrator-agent"
    SATINALMA_PDF = "satinalma-pdf-agent"
    HR_PDF = "hr-pdf-agent"  # Yeni!
```

### 2. Prompt Talimatını Environment'a Ekleyin

`.env` dosyasına yeni agent talimatını ekleyin:
```env
HR_AGENT_INSTRUCTIONS="Sen bir insan kaynakları chatbotusun...\nKurallar..."
```

### 3. Agent Dosyası Oluşturun

`app/agents/hr_agent.py`:
```python
from app.configs.agent_ids import AgentID
from app.configs.settings import settings
...

hr_agent = Agent(
    id=AgentID.HR_PDF.value,
    name="HR Agent",
    ...
)
```

### 4. Routes'a Ekleyin

`app/api/routes.py`:
```python
from app.agents.hr_agent import hr_agent

DOMAIN_AGENTS: Dict[str, object] = {
    AgentID.SATINALMA_PDF.value: satinalma_agent,
    AgentID.HR_PDF.value: hr_agent,  # Yeni!
}
```

## 🧪 Testler

Otomatik test senaryoları henüz eklenmedi; entegrasyon testleri planlandığında bu bölüm güncellenecek.

## 📊 Logging

Loglar console'a yazdırılır. Production'da log aggregation servisine (Stackdriver, CloudWatch, vb.) yönlendirilebilir.

### Log Seviyeleri

```python
import logging
logging.basicConfig(level=logging.INFO)
```

- `DEBUG`: Detaylı debug bilgisi
- `INFO`: Genel bilgi mesajları
- `WARNING`: Uyarılar
- `ERROR`: Hatalar

## 🔒 Güvenlik

### Mevcut Özellikler

- ✅ User ID validasyonu
- ✅ Input sanitization
- ✅ Environment-based configuration
- ✅ Session-based conversation tracking

### Production İçin Öneriler

- [ ] Authentication/Authorization (JWT, OAuth2)
- [ ] Rate limiting
- [ ] HTTPS enforcement
- [ ] Input length limits (DoS koruması)
- [ ] SQL injection koruması (SQLite için parametrized queries)
- [ ] CORS policy güncelleme

## 🚀 Production Deployment

### Önerilen Stack

- **Web Server**: Gunicorn + Uvicorn workers
- **Proxy**: Nginx
- **Container**: Docker
- **Orchestration**: Kubernetes / Cloud Run
- **Monitoring**: Google Cloud Monitoring
- **Logging**: Cloud Logging

### Örnek Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## 📝 Yapılacaklar (Roadmap)

- [x] Temel agent yapısı
- [x] Orchestrator routing
- [x] Mail intent detection
- [x] Logging sistemi
- [x] Error handling
- [x] Temel testler
- [ ] PDF upload/indexing API
- [ ] Gerçek mail servisi entegrasyonu (SMTP/SendGrid)
- [ ] Authentication sistemi
- [ ] Admin paneli
- [ ] Metrik ve monitoring dashboard
- [ ] Daha fazla domain agent (HR, IT, Finans, vs.)
- [ ] Multi-language support

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje [Koç University] için geliştirilmiştir.

## 📞 İletişim

Sorularınız için: [email]

---

**Not**: Bu sistem şu an development aşamasındadır. Production kullanımı öncesinde yukarıda belirtilen güvenlik ve deployment önerilerinin uygulanması gerekmektedir.
