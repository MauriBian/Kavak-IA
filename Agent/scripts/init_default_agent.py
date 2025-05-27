from models.agent import Agent, KnowledgeBase
from models.database import Database
from datetime import datetime, UTC
import logging
import asyncio

async def init_default_agent():
    db = Database()
    
    existing_agent = await Agent.find_by_phone(db, "14155238886")
    if existing_agent:
        logging.info("Default Kavak agent already exists")
        return
    
    default_agent = Agent(
        name="Asistente Comercial Kavak",
        brand="Kavak",
        tone="Friendly and professional, always using emojis. Short and concise answers",
        description="Asistente virtual especializado en la venta de autos seminuevos",
        phone_number="14155238886",
        knowledgeBase=KnowledgeBase(
            id="vs_682f72dc2ff88191961554a90d24f89d",
            account="kavak_account",
            file_ids=["file-W6VcDamRtoLnqPCVTnr6HJ"],
            object="vector_store",
            name="Knowledge Base - https://www.kavak.com/mx/blog/sedes-de-kavak-en-mexico",
            created_at=1747940071
        ),
        instructions="""Calculate car financing plans by: 
1) Get car price, down payment % (min 20%), and term (3-6 years). 
2) Calculate: down payment (price * %), amount to finance (price - down payment), 
   monthly payment using 10% annual interest, total payment (monthly * term months), 
   total interest (total - financed). 
3) Present: down payment, financed amount, monthly payment, total payment, 
   total interest, term. 
4) If requested, show alternatives with different down payments, terms, or prices. 
5) Use fixed 10% annual rate, terms 3-6 years, min 20% down payment, 2 decimal precision. 
Always yours anwers in plain text""",
        model="gpt-4o-mini",
        created_at=datetime.now(UTC)
    )
    
    try:
        await Agent.create(db, default_agent.model_dump())
        logging.info("Default Kavak agent created successfully")
    except Exception as e:
        logging.error(f"Error creating default agent: {str(e)}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_default_agent()) 