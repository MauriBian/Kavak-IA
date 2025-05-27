# Kavak Chatbot

A microservices-based chatbot system for Kavak, built with Python, FastAPI, and Docker. The system integrates with WhatsApp for customer communication and uses OpenAI for natural language processing.

## Architecture

The system consists of three main microservices:

1. **Agent Service** (Port 3000)
   - Handles agent creation and management
   - Processes chat messages
   - Manages knowledge base
   - Integrates with OpenAI for NLP

2. **Message Handler Service** (Port 3001)
   - Manages WhatsApp communication
   - Handles message routing
   - Implements retry logic for failed messages

3. **RabbitMQ** (Ports 5672, 15672)
   - Message broker for inter-service communication
   - Manages message queues
   - Provides message persistence

## Prerequisites

- Docker and Docker Compose
- Python 3.8 or higher
- OpenAI API key
- Twilio account (for WhatsApp integration)
- Jina AI API key (for vector search)

## Environment Setup

1. Clone the repository:
```bash
git clone [REPOSITORY_URL]
cd [DIRECTORY_NAME]
```

2. Configure environment files:
   - In each microservice, you'll find a `.env.sample` file
   - Copy the `.env.sample` to `.env` in each microservice:
```bash
# For Agent service
cd microservices/Agent
cp .env.sample .env

# For Message Handler service
cd ../MessageHandler
cp .env.sample .env
```

3. Edit the `.env` files with your credentials:
```env
# microservices/Agent/.env
OPENAI_API_KEY=your_openai_api_key
JINA_API_KEY=your_jina_api_key
MONGODB_URI=mongodb://mongodb:27017/
MONGODB_DB_NAME=agent_db

# microservices/MessageHandler/.env
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
```

## Installation

1. Build and run the containers:
```bash
docker-compose up --build
```

The services will be available at:
- Agent Service: http://localhost:3000
- Message Handler: http://localhost:3001
- RabbitMQ Management: http://localhost:15672

## API Endpoints

### Agent Service

#### Agent Management
- `POST /agents`: Create a new agent
  ```json
  {
    "name": "Agent Name",
    "brand": "Kavak",
    "description": "Agent description",
    "tone": "Professional and friendly",
    "instructions": "Specific instructions"
  }
  ```

#### Chat
- `POST /chat`: Start a conversation
  ```json
  {
    "agent_id": "agent_id",
    "conversation_id": "conversation_id",
    "message": "User message",
    "channel": "whatsapp"
  }
  ```

## Queue System

The system uses RabbitMQ for message handling:

1. **Input Queue** (`receive_message`)
   - Receives incoming WhatsApp messages
   - Routes messages to appropriate agents

2. **Output Queue** (`send_message`)
   - Handles outgoing messages
   - Manages message delivery to WhatsApp

## Development

### Project Structure
```
.
├── microservices/
│   ├── Agent/
│   │   ├── services/
│   │   │   ├── agent_service.py
│   │   │   └── queue_service.py
│   │   ├── controllers/
│   │   │   └── agent_controller.py
│   │   └── models/
│   │       ├── agent.py
│   │       └── database.py
│   └── MessageHandler/
│       ├── services/
│       │   ├── whatsapp_service.py
│       │   └── message_handler_service.py
│       └── main.py
├── docker-compose.yml
└── requirements.txt
```
