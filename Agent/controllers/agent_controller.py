from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from models import Agent, Session
from services.agent_service import AgentService
from services.session_service import SessionService
import logging
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/agents", tags=["agents"])
agent_service = AgentService()
session_service = SessionService()

class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    channel: Optional[str] = None

class TrainingUrlRequest(BaseModel):
    url: str

@router.post("/", response_model=Agent)
async def create_agent(agent: Agent):
    try:
        created_agent = await agent_service.create_agent(agent)
        return created_agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    try:
        agent = await agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/training")
async def train_agent(
    agent_id: str,
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None)
):
    try:
        if not filename:
            filename = file.filename
        
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="El archivo debe ser un CSV")
        
        agent = await agent_service.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agente no encontrado")
        
        file_content = await file.read()
        
        result = await agent_service.process_training_file(agent_id, file_content, filename)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/training/url")
async def train_agent_from_url(
    agent_id: str,
    request: TrainingUrlRequest
):
    try:
        result = await agent_service.process_training_url(agent_id, request.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/chat")
async def chat(agent_id: str, request: ChatRequest):
    try:
        result = await agent_service.chat(
            agent_id, 
            request.conversation_id, 
            request.message,
            request.channel
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 