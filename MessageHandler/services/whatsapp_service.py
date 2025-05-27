import os
from twilio.rest import Client
from dotenv import load_dotenv
import logging
import time

load_dotenv()

class WhatsAppService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.client = Client(self.account_sid, self.auth_token)
        self.max_retries = 3
        self.retry_delay = 2

    def send_message(self, from_number: str, to_number: str, message: str):
        retries = 0
        while retries < self.max_retries:
            try:
                message = self.client.messages.create(
                    from_=f'whatsapp:+{to_number}',
                    body=message,
                    to=f'whatsapp:+{from_number}'
                )
                logging.info(f"Message sent successfully with SID: {message.sid}")
                return {
                    'status': 'success',
                    'message_sid': message.sid,
                    'error': None
                }

            except Exception as e:
                retries += 1
                if retries == self.max_retries:
                    logging.error(f"Error sending message after {self.max_retries} attempts: {str(e)}")
                    return {
                        'status': 'error',
                        'message_sid': None,
                        'error': str(e)
                    }
                logging.warning(f"Attempt {retries} failed, retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay) 