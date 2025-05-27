import amqpstorm
import json
import os
import logging
import threading
import asyncio
from typing import Callable, Dict, Any
from dotenv import load_dotenv
from services.agent_service import AgentService
from models.agent import Agent
from models.database import Database


load_dotenv()

class QueueService:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._closing = False
        self._consuming = False
        self._lock = threading.Lock()
        self._loop = None
        
        self.input_queue = os.getenv('RABBITMQ_INPUT_QUEUE', 'agent_input_queue')
        self.output_queue = os.getenv('RABBITMQ_OUTPUT_QUEUE', 'agent_output_queue')
        
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        
        self._prefetch_count = 1
        self.agent_service = AgentService()
        self.db = Database()

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
                    logging.info("Connection to RabbitMQ established successfully")
        except Exception as e:
            logging.error(f"Error connecting to RabbitMQ: {str(e)}")
            raise

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
                queue=self.input_queue,
                callback=on_message,
                no_ack=False
            )
            
            logging.info(f"Starting consumption of messages from queue {self.input_queue}")
            self._consuming = True
            self._channel.start_consuming()
        except Exception as e:
            logging.error(f"Error starting message consumption: {str(e)}")
            raise

    async def _process_message(self, message):
        try:
            body = message.body
            message_data = json.loads(body)
            logging.info(f"New message received in queue {self.input_queue}")
            logging.info(f"Message: {message_data}")
            
            to_number = message_data.get("to", "").replace("whatsapp:+", "")
            if not to_number:
                raise ValueError("No phone number found in message")
            
            agent_data = await Agent.find_by_phone(self.db, to_number)
            if not agent_data:
                raise ValueError(f"No agent found with phone number {to_number}")
            
            agent_id = str(agent_data["_id"])
            conversation_id = message_data.get("from", "").replace("whatsapp:+", "")
            
            response = await self.agent_service.chat(
                agent_id=agent_id,
                conversation_id=conversation_id,
                message=message_data.get("message", ""),
                channel=message_data.get("channel")
            )

            response["to_number"] = to_number

            self._channel.basic.publish(
                body=json.dumps(response),
                routing_key=self.output_queue,
                properties={
                    'delivery_mode': 2
                }
            )
            
            message.ack()
            logging.info(f"Message processed successfully")
            
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")
            message.reject(requeue=False)

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
