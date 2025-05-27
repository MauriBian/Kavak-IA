from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.agent_controller import router as agent_router
import uvicorn
import os
from dotenv import load_dotenv
import logging
from services.queue_service import QueueService
from services.agent_service import AgentService
import threading

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Agent micro service",
    description="API for Agent micro service",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)

rabbitmq_service = QueueService()
agent_service = AgentService()

def start_rabbitmq_consumer():
    try:
        rabbitmq_service.start_consuming()
    except Exception as e:
        logging.error(f"Error en el consumidor de RabbitMQ: {str(e)}")

@app.on_event("startup")
async def startup_event():
    rabbitmq_thread = threading.Thread(target=start_rabbitmq_consumer)
    rabbitmq_thread.daemon = True
    rabbitmq_thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    rabbitmq_service.close()

@app.get("/")
async def root():
    return {"message": "Agent micro service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Agent"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
