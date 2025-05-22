from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
        self.db = self.client[os.getenv("DATABASE_NAME", "agent_db")]
        self.agents = self.db["agents"]
        self.sessions = self.db["sessions"]