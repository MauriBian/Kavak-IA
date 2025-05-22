from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, UTC
from bson import ObjectId
from models.database import Database

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class Session(BaseModel):
    id: Optional[str] = None
    agent_id: str
    conversation_id: str
    messages: List[Message]
    channel: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        collection = "sessions"

    @classmethod
    async def create(cls, db: Database, session_dict: dict) -> dict:
        result = await db.sessions.insert_one(session_dict)
        session_dict["id"] = str(result.inserted_id)
        return session_dict

    @classmethod
    async def find_by_conversation_id(cls, db: Database, conversation_id: str) -> Optional[dict]:
        session = await db.sessions.find_one({"conversation_id": conversation_id})
        if session:
            session["id"] = str(session["_id"])
        return session

    @classmethod
    async def add_message(cls, db: Database, session_id: str, message: dict) -> None:
        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$push": {"messages": message},
                "$set": {"updated_at": datetime.now(UTC)}
            }
        )

    @classmethod
    async def update(cls, db: Database, session_id: str, update_data: dict) -> None:
        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    **update_data,
                    "updated_at": datetime.now(UTC)
                }
            }
        ) 