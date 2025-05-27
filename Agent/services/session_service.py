from models.session import Session, Message
from models.database import Database
from bson import ObjectId
import logging

class SessionService:
    def __init__(self):
        self.db = Database()

    async def create_session(self, agent_id: str, conversation_id: str) -> Session:
        session = Session(
            agent_id=agent_id,
            conversation_id=conversation_id,
            messages=[]
        )
        session_dict = session.model_dump()
        created_session = await Session.create(self.db, session_dict)
        return Session(**created_session)

    async def get_or_create_session(self, agent_id: str, conversation_id: str) -> Session:
        session_data = await Session.find_by_conversation_id(self.db, conversation_id)
        if session_data:
            return Session(**session_data)
        
        return await self.create_session(agent_id, conversation_id) 