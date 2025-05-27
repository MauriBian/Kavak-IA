# Kavak Chatbot

A microservices-based chatbot application using FastAPI, RabbitMQ, and MongoDB.

## Prerequisites

- Docker
- Docker Compose

## Getting Started

1. Clone the repository
```bash
git clone [repository-url]
cd kavak-chatbot
```

2. Start the application
```bash
docker-compose up --build
```

This will start the following services:
- Agent service (FastAPI) on port 3000
- Message Handler service on port 3001
- RabbitMQ on ports 5672 (AMQP) and 15672 (Management UI)
- MongoDB on port 27017

## Services

- **Agent Service**: Main chatbot service running on port 3000
- **Message Handler**: Message processing service on port 3001
- **RabbitMQ**: Message broker for inter-service communication
- **MongoDB**: Database for storing agent data

## Development

The application uses Docker volumes for development, so any changes to the code will be reflected immediately without rebuilding the containers.

## Environment Variables Configuration

### Agent Service (.env file in microservices/Agent/.env)
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
```

### Message Handler Service
```env
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_INPUT_QUEUE=receive_message
RABBITMQ_OUTPUT_QUEUE=send_message
```

### RabbitMQ
```env
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest
```

### Configuration Steps

1. Create a `.env` file in the `microservices/Agent` directory with the Agent Service variables
2. For production deployment:
   - Change all default passwords
   - Update the MongoDB connection strings with your production database
   - Use secure credentials for RabbitMQ
   - Consider using Docker secrets for sensitive information
3. Create a ''

### Important Notes
- All services are configured to use the default credentials for development
- In production, make sure to:
  - Use strong passwords
  - Enable authentication for MongoDB
  - Configure proper network security
  - Use environment-specific configuration
