# API Kullanım Örnekleri

Bu dokümanda KUAgentOS API'sini kullanmak için örnek istekler bulunmaktadır.

## Base URL

```
http://localhost:8000
```

## 1. Health Check

API'nin çalışır durumda olup olmadığını kontrol edin.

### Request

```bash
curl -X GET http://localhost:8000/api/health
```

### Response

```json
{
  "status": "healthy",
  "available_agents": [
    "satinalma-pdf-agent"
  ]
}
```

---

## 2. Yeni Chat Session Başlatma

İlk mesajınızla yeni bir chat session'ı başlatın.

### Request

```bash
curl -X POST http://localhost:8000/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "ahmet.yilmaz",
    "message": "Satınalma talebi nasıl oluşturulur?"
  }'
```

### Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_agent_id": "satinalma-pdf-agent",
  "assigned_agent_name": "Satınalma Asistanı",
  "routing_reason": "Kullanıcı satınalma süreci hakkında soru sordu",
  "reply": "Satınalma talebi oluşturmak için şu adımları izleyebilirsiniz:\n\n1. Satınalma portalına giriş yapın\n2. 'Yeni Talep' butonuna tıklayın\n3. Talep formunu doldurun...\n\n(Politika XYZ, Madde 3.1)"
}
```

### Python Örneği

```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat/start",
    json={
        "user_id": "ahmet.yilmaz",
        "message": "Satınalma talebi nasıl oluşturulur?"
    }
)

data = response.json()
print(f"Session ID: {data['session_id']}")
print(f"Reply: {data['reply']}")
```

---

## 3. Mevcut Session'da Mesaj Gönderme (Normal)

Başlatılmış bir session'da konuşmaya devam edin.

### Request

```bash
curl -X POST http://localhost:8000/api/chat/agents/satinalma-pdf-agent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "ahmet.yilmaz",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Talep onay süreci ne kadar sürer?"
  }'
```

### Response

```json
{
  "reply": "Satınalma talep onay süreci genellikle 3-5 iş günü sürmektedir. Acil talepler için hızlandırılmış süreç uygulanabilir.",
  "email_triggered": false,
  "email_info": null
}
```

---

## 4. Mail Tetikleme

Kullanıcı mail göndermek istediğinde.

### Request

```bash
curl -X POST http://localhost:8000/api/chat/agents/satinalma-pdf-agent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "ahmet.yilmaz",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Bu konu hakkında satınalma müdürlüğüne mail gönder"
  }'
```

### Response

```json
{
  "reply": "Elbette, satınalma müdürlüğüne iletmek üzere bir mail hazırladım...\n\n---\nMailiniz Satınalma Müdürlüğü'ne başarıyla iletildi. En kısa sürede size dönüş yapılacaktır.",
  "email_triggered": true,
  "email_info": {
    "orchestrator_reply": "Mailiniz Satınalma Müdürlüğü'ne başarıyla iletildi.",
    "recipient_hint": "Satınalma Müdürlüğü",
    "subject_suggestion": "Satınalma Talebi Bilgi Talebi"
  }
}
```

### Python Örneği (Mail Tetikleme)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat/agents/satinalma-pdf-agent",
    json={
        "user_id": "ahmet.yilmaz",
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "message": "Bu konuda satınalma ekibine mail at"
    }
)

data = response.json()
if data['email_triggered']:
    print("✅ Mail gönderildi!")
    print(f"Alıcı: {data['email_info']['recipient_hint']}")
    print(f"Konu: {data['email_info']['subject_suggestion']}")
print(f"\nCevap: {data['reply']}")
```

---

## 5. Hata Durumları

### Geçersiz Agent ID

```bash
curl -X POST http://localhost:8000/api/chat/agents/invalid-agent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Test"
  }'
```

**Response (404):**

```json
{
  "detail": "Agent bulunamadı: invalid-agent"
}
```

### Eksik User ID

```bash
curl -X POST http://localhost:8000/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test"
  }'
```

**Response (422):**

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "user_id"],
      "msg": "Field required"
    }
  ]
}
```

### Geçersiz Session ID Formatı

```bash
curl -X POST http://localhost:8000/api/chat/agents/satinalma-pdf-agent \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "invalid-uuid",
    "message": "Test"
  }'
```

**Response (422):**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "session_id"],
      "msg": "Value error, session_id geçerli bir UUID formatında olmalıdır"
    }
  ]
}
```

---

## 6. Tam İş Akışı Örneği

### JavaScript/TypeScript

```typescript
class ChatClient {
  private baseUrl: string;
  private userId: string;
  private sessionId?: string;
  private agentId?: string;

  constructor(baseUrl: string, userId: string) {
    this.baseUrl = baseUrl;
    this.userId = userId;
  }

  async startChat(message: string) {
    const response = await fetch(`${this.baseUrl}/api/chat/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: this.userId,
        message: message,
      }),
    });

    const data = await response.json();
    this.sessionId = data.session_id;
    this.agentId = data.assigned_agent_id;
    
    return data;
  }

  async sendMessage(message: string) {
    if (!this.sessionId || !this.agentId) {
      throw new Error('Session not started');
    }

    const response = await fetch(
      `${this.baseUrl}/api/chat/agents/${this.agentId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: this.userId,
          session_id: this.sessionId,
          message: message,
        }),
      }
    );

    return await response.json();
  }
}

// Kullanım
const client = new ChatClient('http://localhost:8000', 'ahmet.yilmaz');

// Chat başlat
const startResponse = await client.startChat('Satınalma talebi nasıl oluşturulur?');
console.log('Agent:', startResponse.assigned_agent_name);
console.log('Cevap:', startResponse.reply);

// Devam et
const followUp = await client.sendMessage('Talep onay süreci ne kadar sürer?');
console.log('Cevap:', followUp.reply);

// Mail gönder
const emailResponse = await client.sendMessage('Bu konuda satınalma ekibine mail at');
if (emailResponse.email_triggered) {
  console.log('✅ Mail gönderildi!');
}
```

---

## Notlar

- **user_id**: Her istek için zorunludur, manuel olarak sağlanmalıdır
- **session_id**: `/chat/start` endpoint'i otomatik üretir, sonraki isteklerde kullanılmalıdır
- **agent_id**: Orchestrator otomatik seçer, yanıtta döndürülür
- **Mail**: Agent `email_intent=true` döndüğünde otomatik tetiklenir

## Swagger UI

Daha detaylı API dokümantasyonu için:
```
http://localhost:8000/docs
```
