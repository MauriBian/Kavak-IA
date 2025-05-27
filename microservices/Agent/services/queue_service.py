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
import pika


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
            logging.error(f"Error al conectar con RabbitMQ: {str(e)}")
            raise

    def setup_connection(self):
        try:
            with self._lock:
                if self._connection is None or self._connection.is_closed:
                    self._connection = self.connect()
                    self._channel = self._connection.channel()
                    self._channel.queue.declare(self.input_queue, durable=True)
                    self._channel.queue.declare(self.output_queue, durable=True)
                    logging.info("Conexión con RabbitMQ establecida exitosamente")
        except Exception as e:
            logging.error(f"Error al conectar con RabbitMQ: {str(e)}")
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
                    logging.error(f"Error en el procesamiento del mensaje: {str(e)}")
                    message.reject(requeue=True)
            
            self._channel.basic.consume(
                queue=self.input_queue,
                callback=on_message,
                no_ack=False
            )
            
            logging.info(f"Iniciando consumo de mensajes de la cola {self.input_queue}")
            self._consuming = True
            self._channel.start_consuming()
        except Exception as e:
            logging.error(f"Error al iniciar el consumo de mensajes: {str(e)}")
            raise

    async def _process_message(self, message):
        try:
            body = message.body
            message_data = json.loads(body)
            logging.info(f"Nuevo mensaje recibido en la cola {self.input_queue}")
            logging.info(f"Mensaje: {message_data}")
            
            to_number = message_data.get("to", "").replace("whatsapp:+", "")
            if not to_number:
                raise ValueError("No se encontró el número de teléfono en el mensaje")
            
            agent_data = await Agent.find_by_phone(self.db, to_number)
            if not agent_data:
                raise ValueError(f"No se encontró un agente con el número {to_number}")
            
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
            logging.info(f"Mensaje procesado exitosamente")
            
        except Exception as e:
            logging.error(f"Error al procesar mensaje: {str(e)}")
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
                logging.error(f"Error al cerrar la conexión: {str(e)}")
            finally:
                logging.info("Conexión con RabbitMQ cerrada")
                self._closing = False
                self._consuming = False 

    def _ensure_connection(self):
        if not self._connection or self._connection.is_closed:
            try:
                self._connection = self.connect()
                self._channel = self._connection.channel()
                self._channel.queue.declare(self.input_queue, durable=True)
                self._channel.queue.declare(self.output_queue, durable=True)
                logging.info("Successfully reconnected to RabbitMQ")
            except Exception as e:
                logging.error(f"Error connecting to RabbitMQ: {str(e)}")
                raise

    def process_message(self, ch, method, properties, body):
        try:
            message_data = json.loads(body)
            logging.info(f"New message received in queue {self.input_queue}")
            logging.info(f"Message: {message_data}")

            if not message_data.get('to_number'):
                raise ValueError("Phone number not found in message")

            to_number = message_data['to_number']
            agent = self.agent_service.get_agent_by_phone(to_number)
            if not agent:
                raise ValueError(f"No agent found with number {to_number}")

            response = self.agent_service.process_message({
                'agent_id': str(agent.id),
                'conversation_id': message_data.get('conversation_id'),
                'message': message_data['message']
            })

            if response['status'] == 'success':
                self._channel.basic.publish(
                    body=json.dumps(response),
                    routing_key=self.output_queue,
                    properties={
                        'delivery_mode': 2
                    }
                )
                logging.info(f"Message processed successfully")
            else:
                logging.error(f"Error processing message: {response['message']}")

        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")

    def start_consuming(self):
        try:
            self._ensure_connection()
            logging.info(f"Starting message consumption from queue {self.input_queue}")
            self._channel.basic.consume(
                queue=self.input_queue,
                on_message_callback=self.process_message,
                auto_ack=True
            )
            self._channel.start_consuming()
        except Exception as e:
            logging.error(f"Error starting message consumption: {str(e)}")
            raise

    def close(self):
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
                logging.info("Connection closed successfully")
        except Exception as e:
            logging.error(f"Error closing connection: {str(e)}") 