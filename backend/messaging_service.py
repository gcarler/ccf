import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessagingService:
    @staticmethod
    def send_sms(phone: str, message: str):
        # Mock SMS sending (e.g., would use Twilio API here)
        logger.info(f"MOCK SMS SENT to {phone}: {message}")
        return True

    @staticmethod
    def send_whatsapp(phone: str, message: str):
        # Mock WhatsApp sending (e.g., would use Twilio/Meta API here)
        logger.info(f"MOCK WHATSAPP SENT to {phone}: {message}")
        return True

    @staticmethod
    def send_email(email: str, subject: str, body: str):
        # Mock Email sending (e.g., would use Resend or SendGrid API here)
        logger.info(f"MOCK EMAIL SENT to {email} - Subject: {subject}")
        return True


messaging_service = MessagingService()
