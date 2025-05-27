from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from services.message_handler_service import MessageHandlerService
import threading
import json
import os
import uvicorn

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = FastAPI(title="Message Handler Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

message_handler_service = MessageHandlerService()

def start_rabbitmq_consumer():
    try:
        message_handler_service.setup_connection()
        message_handler_service.start_consuming()
    except Exception as e:
        logging.error(f"Error in RabbitMQ consumer: {str(e)}")

@app.on_event("startup")
async def startup_event():
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer)
    consumer_thread.daemon = True
    consumer_thread.start()

@app.on_event("shutdown")
async def shutdown_event():
    message_handler_service.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        raw_body = await request.body()
        logging.info(f"Received raw body: {raw_body.decode('utf-8')}")
        
        try:
            body = await request.json()
            logging.info(f"WhatsApp message received (JSON): {json.dumps(body, indent=2)}")
        except json.JSONDecodeError:
            form_data = await request.form()
            body = dict(form_data)
            logging.info(f"WhatsApp message received (Form): {json.dumps(body, indent=2)}")
            

            message_data = {
                "channel": "whatsapp",
                "message": body.get("Body", ""),
                "from": body.get("From", ""),
                "to": body.get("To", ""),
                "profile_name": body.get("ProfileName", ""),
                "message_type": body.get("MessageType", "text"),
                "wa_id": body.get("WaId", ""),
                "timestamp": body.get("MessageSid", ""),  
                "status": body.get("SmsStatus", "")
            }
            
            await message_handler_service.send_to_queue(message_data)
            logging.info(f"Message sent to queue: {json.dumps(message_data, indent=2)}")
        
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error in WhatsApp webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)