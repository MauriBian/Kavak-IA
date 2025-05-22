import pika
import json
import os
import logging
import threading
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class MessageHandlerService:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._consuming = False
        self._lock = threading.Lock()
        
        # Configuración de colas
        self.input_queue = os.getenv("RABBITMQ_INPUT_QUEUE", "send_message")
        self.output_queue = os.getenv("RABBITMQ_OUTPUT_QUEUE", "receive_message")
        
        # Configuración de RabbitMQ
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        
        # Prefetch count para control de mensajes
        self._prefetch_count = 1

    def connect(self):
        credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
        parameters = pika.ConnectionParameters(
            host=self.rabbitmq_host,
            port=self.rabbitmq_port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        return pika.BlockingConnection(parameters)

    def setup_connection(self):
        try:
            with self._lock:
                if self._connection is None or self._connection.is_closed:
                    self._connection = self.connect()
                    self._channel = self._connection.channel()
                    self._channel.queue_declare(queue=self.input_queue, durable=True)
                    self._channel.queue_declare(queue=self.output_queue, durable=True)
                    logging.info("Conexión con RabbitMQ establecida exitosamente")
        except Exception as e:
            logging.error(f"Error al establecer conexión con RabbitMQ: {str(e)}")
            raise

    def _process_message(self, ch, method, properties, body):
        try:
            logging.info(f"Nuevo mensaje recibido en la cola {self.output_queue}")
            message = json.loads(body)
            channel = message.get("channel")
            
            logging.info(f"Procesando mensaje para el canal: {channel}")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logging.info(f"Mensaje procesado para el canal: {channel}")
            
        except Exception as e:
            logging.error(f"Error al procesar mensaje: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag)

    def start_consuming(self):
        try:
            self.setup_connection()
            self._channel.basic_qos(prefetch_count=self._prefetch_count)
            self._consumer_tag = self._channel.basic_consume(
                queue=self.output_queue,
                on_message_callback=self._process_message,
                auto_ack=False
            )
            logging.info(f"Iniciando consumo de mensajes de la cola: {self.output_queue}")
            self._consuming = True
            self._channel.start_consuming()
        except Exception as e:
            logging.error(f"Error en el consumidor de RabbitMQ: {str(e)}")
            self.reconnect()
            raise

    def reconnect(self):
        if not self._closing:
            logging.info("Intentando reconectar...")
            self.close()
            self.setup_connection()

    def close(self):
        with self._lock:
            self._closing = True
            if self._channel and self._channel.is_open:
                if self._consumer_tag:
                    self._channel.basic_cancel(self._consumer_tag)
                self._channel.close()
            if self._connection and self._connection.is_open:
                self._connection.close()
            logging.info("Conexión con RabbitMQ cerrada")
            self._closing = False
            self._consuming = False

    async def send_to_queue(self, message: Dict[str, Any]):
        try:
            with self._lock:
                if self._connection is None or self._connection.is_closed:
                    self.setup_connection()
                
                self._channel.basic_publish(
                    exchange='',
                    routing_key=self.input_queue,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # make message persistent
                    )
                )
                logging.info(f"Mensaje enviado a la cola: {self.input_queue}")
        except Exception as e:
            logging.error(f"Error al enviar mensaje a la cola: {str(e)}")
            self.reconnect()
            raise 