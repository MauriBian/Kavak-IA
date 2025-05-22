import pika
import json
import os
import logging
import threading
from typing import Callable, Dict, Any
from dotenv import load_dotenv


load_dotenv()

class QueueService:
    def __init__(self):
        # Implementación recomendada https://github.com/pika/pika/blob/main/examples/asynchronous_consumer_example.py
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._consuming = False
        self._lock = threading.Lock()
        
        self.input_queue = os.getenv('RABBITMQ_INPUT_QUEUE', 'agent_input_queue')
        self.output_queue = os.getenv('RABBITMQ_OUTPUT_QUEUE', 'agent_output_queue')
        
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        
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
            logging.error(f"Error al conectar con RabbitMQ: {str(e)}")
            raise

    def start_consuming(self, callback: Callable[[Dict[str, Any]], None]):
        try:
            self.setup_connection()
            self._channel.basic_qos(prefetch_count=self._prefetch_count)
            self._consumer_tag = self._channel.basic_consume(
                queue=self.input_queue,
                on_message_callback=lambda ch, method, properties, body: self._process_message(ch, method, properties, body, callback),
                auto_ack=False
            )
            logging.info(f"Iniciando consumo de mensajes de la cola {self.input_queue}")
            self._consuming = True
            self._channel.start_consuming()
        except Exception as e:
            logging.error(f"Error al iniciar el consumo de mensajes: {str(e)}")
            self.reconnect()
            raise

    def _process_message(self, ch, method, properties, body, callback):
        try:
            message = json.loads(body)
            logging.info(f"Nuevo mensaje recibido en la cola {self.input_queue}")
            
            # Procesar el mensaje con el callback proporcionado
            callback(message)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logging.info(f"Mensaje procesado exitosamente")
        except Exception as e:
            logging.error(f"Error al procesar mensaje: {str(e)}")
            ch.basic_nack(delivery_tag=method.delivery_tag)

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