# Agente comercial Kavak

## Requisitos Previos

- Python 3.8 o superior
- Docker y Docker Compose
- Cuenta de OpenAI con API key
- Cuenta de Jina AI con API key
- Cuenta en twilio

## Configuración del Entorno

1. Clona el repositorio:
```bash
git clone [URL_DEL_REPOSITORIO]
cd [NOMBRE_DEL_DIRECTORIO]
```

2. Configura los archivos de entorno:
   - En cada microservicio, encontrarás un archivo `.env.sample`
   - Copia el archivo `.env.sample` a `.env` en cada microservicio:
```bash
# Por ejemplo
cd microservices/Agent
cp .env.sample .env
```

3. Edita los archivos `.env` en cada microservicio con tus credenciales:
```env
# microservices/Agent/.env
OPENAI_API_KEY=tu_api_key_de_openai
JINA_API_KEY=tu_api_key_de_jina
TWILIO_ACCOUNT_SID=tu_account_sid_de_twilio
TWILIO_AUTH_TOKEN=tu_auth_token_de_twilio
```

## Instalación

### Usando Docker (Recomendado)

1. Construye y ejecuta los contenedores:
```bash
docker-compose up --build
```
## Estructura del Proyecto

```
.
├── microservices/
│   └── Agent/
│       └── services/
│           └── agent_service.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

## Uso

El servicio estará disponible en `http://localhost:3000` por defecto.

### Endpoints del Microservicio Agent

#### Gestión de Agentes
- `POST /agents`: Crear un nuevo agente
  ```json
  {
    "name": "Nombre del Agente",
    "brand": "Kavak",
    "description": "Descripción del agente",
    "tone": "Profesional y amigable",
    "instructions": "Instrucciones específicas"
  }
  ```

#### Chat y Mensajería
- `POST /chat`: Iniciar una conversación con el chatbot
  ```json
  {
    "agent_id": "id_del_agente",
    "conversation_id": "id_de_conversacion",
    "message": "Mensaje del usuario",
    "channel": "whatsapp"
  }
  ```


### Sistema de Colas (Queues)

El sistema utiliza colas para manejar las comunicaciones asíncronas entre microservicios. Las principales colas son:

1. **Cola de Mensajes Entrantes**
   - Recibe mensajes de diferentes canales (WhatsApp)
   - Procesa y distribuye los mensajes a los agentes correspondientes
   - Maneja reintentos automáticos en caso de fallos

2. **Cola de Respuestas**
   - Gestiona las respuestas generadas por los agentes
   - Asegura la entrega de mensajes a los canales correspondientes


#### Configuración de Colas
Las colas se configuran automáticamente al iniciar los servicios con Docker Compose. No se requiere configuración adicional.