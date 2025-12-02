# app/tools/mail_tools.py
"""
Mail gönderimi için toolkit.
Şu an logging yapıyor, production için SMTP/SendGrid/Gmail API entegrasyonu eklenebilir.
"""
import logging
from typing import Optional
from datetime import datetime

from agno.tools.toolkit import Toolkit

from app.configs.settings import settings

# Logger ayarla
logger = logging.getLogger(__name__)


class MailTools(Toolkit):
    """
    Mail gönderimi için toolkit.
    
    Şu an sadece mail bilgilerini logluyor (mock).
    Production ortamı için:
    - SMTP entegrasyonu
    - SendGrid/Mailgun gibi servisler
    - Gmail/Outlook API
    eklenebilir.
    
    Mail settings'den alınan bilgiler:
    - mail_sender_name: Gönderen adı
    - mail_sender_email: Gönderen mail adresi
    - mail_default_recipient: Varsayılan alıcı
    """

    def __init__(self, *args, **kwargs):
        """Mail tools initializer."""
        tools = [self.send_email]
        super().__init__(name="mail_tools", tools=tools, *args, **kwargs)
        logger.info("MailTools initialized (mock mode)")

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
    ) -> str:
        """
        Mail gönderir (şu an mock - sadece loglar).
        
        Args:
            to: Alıcı mail adresi
            subject: Mail konusu
            body: Mail içeriği
            cc: Kopya alıcılar (opsiyonel)
        
        Returns:
            str: İşlem durumu mesajı
        
        Example:
            >>> mail_tools.send_email(
            ...     to="procurement@example.com",
            ...     subject="Satınalma Talebi",
            ...     body="Merhaba, ..."
            ... )
            "EMAIL_LOGGED"
        """
        # Mail bilgilerini logluyoruz
        logger.info("=" * 60)
        logger.info("📧 EMAIL SEND REQUEST")
        logger.info("=" * 60)
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"From: {settings.mail_sender_name} <{settings.mail_sender_email}>")
        logger.info(f"To: {to}")
        if cc:
            logger.info(f"CC: {cc}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 60)
        logger.info(f"Body:\n{body}")
        logger.info("=" * 60)
        
        # TODO: Gerçek mail servisi entegrasyonu
        # Örnek implementasyon:
        # try:
        #     smtp_client.send(
        #         from_email=settings.mail_sender_email,
        #         to_email=to,
        #         subject=subject,
        #         body=body,
        #         cc=cc
        #     )
        #     logger.info(f"Email successfully sent to {to}")
        #     return "EMAIL_SENT"
        # except Exception as e:
        #     logger.error(f"Failed to send email: {e}")
        #     raise MailServiceError(f"Mail gönderilemedi: {str(e)}")
        
        return "EMAIL_LOGGED"
