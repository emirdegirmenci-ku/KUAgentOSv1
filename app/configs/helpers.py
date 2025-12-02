# app/configs/helpers.py
"""
Yardımcı fonksiyonlar ve utility'ler.
"""
from typing import Optional


def sanitize_user_id(user_id: Optional[str]) -> str:
    """
    User ID'yi temizler ve doğrular.
    Eğer user_id boş ise "anonymous" döner.
    
    Args:
        user_id: Kullanıcıdan gelen user_id
    
    Returns:
        Temizlenmiş user_id
    """
    if not user_id or not user_id.strip():
        return "anonymous"
    
    # Tehlikeli karakterleri temizle
    sanitized = user_id.strip()
    # Gerekirse daha fazla sanitization eklenebilir
    
    return sanitized


def format_error_message(error: Exception, user_friendly: bool = True) -> str:
    """
    Hata mesajını formatlar.
    
    Args:
        error: Exception objesi
        user_friendly: True ise kullanıcı dostu mesaj, False ise teknik detay
    
    Returns:
        Formatlanmış hata mesajı
    """
    if user_friendly:
        # Kullanıcıya gösterilecek basit mesaj
        error_messages = {
            "JSONDecodeError": "Sistem cevabı işlenirken bir sorun oluştu. Lütfen tekrar deneyin.",
            "ValidationError": "Gönderilen bilgiler geçersiz. Lütfen kontrol edin.",
            "HTTPException": "İstek işlenirken bir hata oluştu.",
            "ConnectionError": "Bağlantı hatası. Lütfen internet bağlantınızı kontrol edin.",
        }
        
        error_type = type(error).__name__
        return error_messages.get(error_type, "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.")
    else:
        # Teknik detay (log için)
        return f"{type(error).__name__}: {str(error)}"
