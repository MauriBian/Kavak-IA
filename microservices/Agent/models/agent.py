from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from bson import ObjectId
from models.database import Database

class FileCounts(BaseModel):
    in_progress: int
    completed: int
    failed: int
    cancelled: int
    total: int

class KnowledgeBase(BaseModel):
    id: str
    account: str
    file_ids: List[str]
    object: str = "vector_store"
    name: str
    created_at: int

class Agent(BaseModel):
    name: str
    brand: str
    tone: str
    description: str
    knowledgeBase: KnowledgeBase
    instructions: str
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        collection = "agents"

    @classmethod
    async def create(cls, db: Database, agent_dict: dict) -> dict:
        await db.agents.insert_one(agent_dict)
        return agent_dict

    @classmethod
    async def find_by_id(cls, db: Database, agent_id: str) -> Optional[dict]:
        return await db.agents.find_one({"_id": ObjectId(agent_id)})

    @classmethod
    async def update(cls, db: Database, agent_id: str, update_data: dict) -> None:
        await db.agents.update_one(
            {"_id": ObjectId(agent_id)},
            {"$set": update_data}
        ) 