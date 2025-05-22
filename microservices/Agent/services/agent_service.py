from typing import Optional, Dict, Any
from models.agent import Agent, KnowledgeBase
from models.database import Database
from models.session import Session, Message
from openai import OpenAI
from bson import ObjectId
import os
from dotenv import load_dotenv
import tempfile
import logging
import time
import csv
import io
from pathlib import Path
from agents import Runner
from agents import Agent as OpenAIAgent
from agents import FileSearchTool
import requests
import json

load_dotenv()

class AgentService:
    def __init__(self):
        self.db = Database()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.process_prompt = self._load_prompt()
        self.agent_prompt = self._load_agent_prompt()
        self.jina_api_key = os.getenv("JINA_API_KEY")

    def _load_prompt(self) -> str:
        prompt_path = Path("prompts/process_content.txt")
        if not prompt_path.exists():
            raise Exception("Prompt file not found. Please ensure 'prompts/process_content.txt' exists.")
        return prompt_path.read_text(encoding='utf-8')

    def _load_agent_prompt(self) -> str:
        prompt_path = Path("prompts/agent.txt")
        if not prompt_path.exists():
            raise Exception("Prompt file not found. Please ensure 'prompts/agent.txt' exists.")
        return prompt_path.read_text(encoding='utf-8')

    def _format_agent_instructions(self, agent_data: Agent) -> str:
        return self.agent_prompt.format(
            name=agent_data.name,
            brand=agent_data.brand,
            description=agent_data.description,
            tone=agent_data.tone or "Professional, friendly, and helpful",
            instructions=agent_data.instructions or "Follow the standard guidelines for customer service and sales support."
        )

    async def create_agent(self, agent: Agent) -> Agent:
        agent_dict = agent.model_dump()
        created_agent = await Agent.create(self.db, agent_dict)
        return Agent(**created_agent)

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        agent_data = await Agent.find_by_id(self.db, agent_id)
        if agent_data:
            return Agent(**agent_data)
        return None

    async def chat(self, agent_id: str, conversation_id: str, message: str, channel: str = None) -> dict:
        try:
            session_data = await Session.find_by_conversation_id(self.db, conversation_id)
            if not session_data:
                session = Session(
                    agent_id=agent_id,
                    conversation_id=conversation_id,
                    messages=[],
                    channel=channel
                )
                session_dict = session.model_dump()
                created_session = await Session.create(self.db, session_dict)
                session = Session(**created_session)
            else:
                session = Session(**session_data)
                if channel and not session.channel:
                    await Session.update(
                        self.db,
                        str(session.id),
                        {"channel": channel}
                    )
            
            agent_data = await self.get_agent(agent_id)
            if not agent_data:
                raise Exception("Agente no encontrado")

            tools = []
            if agent_data.knowledgeBase and agent_data.knowledgeBase.file_ids:
                tools.append(
                    FileSearchTool(
                        max_num_results=3,
                        vector_store_ids=[agent_data.knowledgeBase.id]
                    )
                )

            conversation_history = session.messages[-6:] if session.messages else []
            history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in conversation_history])

            formatted_instructions = self._format_agent_instructions(agent_data)
            if history_text:
                formatted_instructions += f"\n\nConversation history:\n{history_text}"

            openai_agent = OpenAIAgent(
                name=agent_data.name,
                instructions=formatted_instructions,
                model=agent_data.model,
                tools=tools
            )

            user_message = Message(role="user", content=message)
            await Session.add_message(self.db, str(session.id), user_message.model_dump())

            result = await Runner.run(openai_agent, message)
            assistant_message = result.final_output

            agent_message = Message(role="assistant", content=assistant_message)
            await Session.add_message(self.db, str(session.id), agent_message.model_dump())

            return {
                "message": assistant_message,
                "conversation_id": conversation_id,
                "channel": session.channel
            }

        except Exception as e:
            logging.error(f"Error en chat: {str(e)}")
            raise Exception(f"Error en chat: {str(e)}")

    def _csv_to_json(self, csv_content: bytes) -> str:
        try:
            csv_text = csv_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            rows = list(csv_reader)
            return json.dumps(rows, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Error converting CSV to JSON: {str(e)}")

    async def process_training_file(self, agent_id: str, file_content: bytes, filename: str) -> dict:
        temp_file_path = None
        try:
            json_content = self._csv_to_json(file_content)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(json_content)
                temp_file_path = temp_file.name

            try:
                with open(temp_file_path, 'rb') as file:
                    openai_file = self.client.files.create(
                        file=file,
                        purpose="assistants"
                    )

                vector_store = self.client.vector_stores.create(
                    name=f"Knowledge Base - {filename}",
                    file_ids=[openai_file.id]
                )

                knowledge_base = KnowledgeBase(
                    id=str(vector_store.id),
                    account="kavak_account",
                    file_ids=[openai_file.id],
                    object="vector_store",
                    name=f"Knowledge Base - {filename}",
                    created_at=int(time.time())
                )

                await Agent.update(
                    self.db,
                    agent_id,
                    {"knowledgeBase": knowledge_base.model_dump()}
                )

                return {
                    "message": "File processed successfully",
                    "file_id": openai_file.id,
                    "vector_store_id": vector_store.id,
                    "knowledge_base": knowledge_base.model_dump()
                }

            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise Exception(f"Error processing file: {str(e)}")

    async def process_training_url(self, agent_id: str, url: str) -> dict:
        temp_file_path = None
        try:
            headers = {"Authorization": f"Bearer {self.jina_api_key}"}
            response = requests.get(f"https://r.jina.ai/{url}", headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Error al obtener contenido de la URL: {response.text}")
            
            text_content = response.text
            
            if not text_content:
                raise Exception("No se pudo obtener contenido de la URL")
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(text_content)
                temp_file_path = temp_file.name

            try:
                with open(temp_file_path, 'rb') as file:
                    openai_file = self.client.files.create(
                        file=file,
                        purpose="assistants"
                    )

                agent_data = await self.get_agent(agent_id)
                if not agent_data:
                    raise Exception("Agente no encontrado")

                if agent_data.knowledgeBase and agent_data.knowledgeBase.id:
                    file_batch = self.client.vector_stores.file_batches.create(
                        vector_store_id=agent_data.knowledgeBase.id,
                        file_ids=[openai_file.id]
                    )
                    vector_store_id = agent_data.knowledgeBase.id
                else:
                    vector_store = self.client.vector_stores.create(
                        name=f"Knowledge Base - {url}",
                        file_ids=[openai_file.id]
                    )
                    vector_store_id = vector_store.id

                knowledge_base = KnowledgeBase(
                    id=str(vector_store_id),
                    account="kavak_account",
                    file_ids=[openai_file.id],
                    object="vector_store",
                    name=f"Knowledge Base - {url}",
                    created_at=int(time.time())
                )

                await Agent.update(
                    self.db,
                    agent_id,
                    {"knowledgeBase": knowledge_base.model_dump()}
                )

                return {
                    "message": "URL processed successfully",
                    "file_id": openai_file.id,
                    "vector_store_id": vector_store_id,
                    "knowledge_base": knowledge_base.model_dump()
                }

            finally:
                if temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            raise Exception(f"Error processing URL: {str(e)}")

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not all(key in message for key in ["agent_id", "conversation_id", "message"]):
                raise ValueError("El mensaje debe contener agent_id, conversation_id y message")

            response = await self.chat(
                message["agent_id"],
                message["conversation_id"],
                message["message"]
            )

            return {
                "conversation_id": response["conversation_id"],
                "message": response["message"],
                "status": "success"
            }

        except Exception as e:
            logging.error(f"Error al procesar mensaje: {str(e)}")
            return {
                "conversation_id": message.get("conversation_id", "unknown"),
                "message": f"Error: {str(e)}",
                "status": "error"
            }