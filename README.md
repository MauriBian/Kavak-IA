# Kavak Chatbot

A microservices-based chatbot application using FastAPI, RabbitMQ, MongoDB, and Jina for web scraping.

## Prerequisites

- Docker
- Docker Compose
- Twilio Account (for WhatsApp integration)
- Jina Account (for web scraping)

## Getting Started

1. Clone the repository
```bash
git clone [repository-url]
cd kavak-chatbot
```

2. Configure environment variables:
   - Copy `.env.sample` to `.env` in both services:
   ```bash
   # For Agent service
   cd Agent
   cp .env.sample .env

   # For Message Handler service
   cd ../MessageHandler
   cp .env.sample .env
   ```

3. Start the application
```bash
docker-compose up --build
```

This will start the following services:
- Agent service (FastAPI) on port 3000
- Message Handler service on port 3001
- RabbitMQ on ports 5672 (AMQP) and 15672 (Management UI)
- MongoDB on port 27017

The application will automatically initialize a default Kavak Commercial Assistant agent if it doesn't exist in the database.

## Services

- **Agent Service**: Main chatbot service running on port 3000
- **Message Handler**: Message processing service on port 3001
- **RabbitMQ**: Message broker for inter-service communication
- **MongoDB**: Database for storing agent data

## Development

The application uses Docker volumes for development, so any changes to the code will be reflected immediately without rebuilding the containers.

## Environment Variables Configuration

### Agent Service (.env file in Agent/.env)
```env
ENVIRONMENT=development
MONGODB_URL=mongodb://mongodb:27017
DATABASE_NAME=agent_db
COLLECTION_NAME=agents
PORT=3000
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_INPUT_QUEUE=receive_message
RABBITMQ_OUTPUT_QUEUE=send_message
MONGODB_URI=mongodb://mongodb:27017/
MONGODB_DB_NAME=agent_db
JINA_API_KEY=your_jina_api_key
```

### Message Handler Service
```env
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_INPUT_QUEUE=receive_message
RABBITMQ_OUTPUT_QUEUE=send_message
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone
```

### RabbitMQ
```env
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest
```

### Important Notes
- All services are configured to use the default credentials for development
- In production, make sure to:
  - Use strong passwords
  - Enable authentication for MongoDB
  - Configure proper network security
  - Use environment-specific configuration
