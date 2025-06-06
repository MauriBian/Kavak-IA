import amqpstorm
import json
import os
import logging
import threading
import asyncio
from typing import Dict, Any
from dotenv import load_dotenv
from services.whatsapp_service import WhatsAppService

load_dotenv()

class MessageHandlerService:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._closing = False
        self._consuming = False
        self._lock = threading.Lock()
        self._loop = None
        
        self.input_queue = os.getenv("RABBITMQ_INPUT_QUEUE", "send_message")
        self.output_queue = os.getenv("RABBITMQ_OUTPUT_QUEUE", "receive_message")
        
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        
        self._prefetch_count = 1
        self.whatsapp_service = WhatsAppService()

    def connect(self):
        try:
            self._connection = amqpstorm.Connection(
                hostname=self.rabbitmq_host,
                port=self.rabbitmq_port,
                username=self.rabbitmq_user,
                password=self.rabbitmq_password,
                heartbeat=600,
                timeout=300
            )
            return self._connection
        except Exception as e:
            logging.error(f"Error connecting to RabbitMQ: {str(e)}")
            raise

    def setup_connection(self):
        try:
            with self._lock:
                if self._connection is None or self._connection.is_closed:
                    self._connection = self.connect()
                    self._channel = self._connection.channel()
                    self._channel.queue.declare(self.input_queue, durable=True)
                    self._channel.queue.declare(self.output_queue, durable=True)
                    logging.info("RabbitMQ connection established successfully")
        except Exception as e:
            logging.error(f"Error establishing connection to RabbitMQ: {str(e)}")
            raise

    async def _process_message(self, message):
        try:
            logging.info(f"New message received in queue {self.output_queue}")
            message_data = json.loads(message.body)
            logging.info(f"Message received: {message_data}")
            
            channel = message_data.get("channel")
            from_number = message_data.get("conversation_id")
            to_number = message_data.get("to_number")
            message_text = message_data.get("message", "")
            
            if not to_number or not message_text:
                raise ValueError("Phone number or message missing")
            
            if channel == "whatsapp":

                logging.info(f"Sending WhatsApp message from {from_number} to {to_number}")
                
                whatsapp_response = self.whatsapp_service.send_message(
                    from_number=from_number,
                    to_number=to_number,
                    message=message_text
                )
                
                if whatsapp_response["status"] == "error":
                    raise Exception(f"Error sending WhatsApp message: {whatsapp_response['error']}")
                
                logging.info(f"WhatsApp message sent successfully: {whatsapp_response['message_sid']}")
            
            message.ack()
            
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            message.reject(requeue=False)

    def start_consuming(self):
        try:
            self.setup_connection()
            self._channel.basic.qos(prefetch_count=self._prefetch_count)
            
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            def on_message(message):
                try:
                    self._loop.run_until_complete(
                        self._process_message(message)
                    )
                except Exception as e:
                    logging.error(f"Error processing message: {str(e)}")
                    message.reject(requeue=True)
            
            self._channel.basic.consume(
                queue=self.output_queue,
                callback=on_message,
                no_ack=False
            )
            
            logging.info(f"Starting consumption of messages from queue: {self.output_queue}")
            self._consuming = True
            self._channel.start_consuming()
        except Exception as e:
            logging.error(f"Error in RabbitMQ consumer: {str(e)}")
            raise

    def close(self):
        with self._lock:
            self._closing = True
            try:
                if self._channel and self._channel.is_open:
                    self._channel.close()
                if self._connection and self._connection.is_open:
                    self._connection.close()
                if self._loop and self._loop.is_running():
                    self._loop.stop()
            except Exception as e:
                logging.error(f"Error closing connection: {str(e)}")
            finally:
                logging.info("RabbitMQ connection closed")
                self._closing = False
                self._consuming = False

    async def send_to_queue(self, message: Dict[str, Any]):
        try:
            with self._lock:
                if self._connection is None or self._connection.is_closed:
                    self.setup_connection()
                
                self._channel.basic.publish(
                    body=json.dumps(message),
                    routing_key=self.input_queue,
                    properties={
                        'delivery_mode': 2
                    }
                )
                logging.info(f"Message sent to queue: {self.input_queue}")
        except Exception as e:
            logging.error(f"Error sending message to queue: {str(e)}")
            raise 