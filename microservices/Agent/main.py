from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.agent_controller import router as agent_router
import uvicorn
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Agent micro service",
    description="API for Agent micro service",
    version="1.0.0"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)

@app.get("/")
async def root():
    return {"message": "Agent micro service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Agent"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
