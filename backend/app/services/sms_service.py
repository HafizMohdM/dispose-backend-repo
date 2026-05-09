from twilio.rest import Client
import logging
from app.core.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

logger = logging.getLogger(__name__)

class SmsService:
    @staticmethod
    def send_otp(mobile: str, otp: str):
        """
        Sends an OTP to the specified mobile number using Twilio.
        """
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            logger.error("Twilio credentials not configured properly.")
            return None

        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=f"Your Dispose verification code is: {otp}. Valid for 5 minutes.",
                from_=TWILIO_PHONE_NUMBER,
                to=mobile
            )
            logger.info(f"OTP sent to {mobile}. Twilio SID: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send SMS to {mobile}: {str(e)}")
            return None
