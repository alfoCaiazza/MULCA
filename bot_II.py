import os
import discord
from dotenv import load_dotenv
from ask_llm import get_llm_response, translate_messages
import redis
import json
import time
import string
import asyncio

load_dotenv()
TOKEN = os.getenv('BOTII_TOKEN')

# Redis init
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# Bot prompts
def get_personality_prompt(bot_name: str) -> str:
    return f"""# ROLE: Act like {bot_name}, a Gen-Z teenager and life-time friend who always replies to the group chat messages.

            # CONTEXT: You will receive an overview of the conversation history. Reply ONLY to the very last message, referencing previous information if necessary.

            # INSTRUCTIONS: You have a sharp and intelligent personality, and you always have a quick comeback. Your language sounds like that of a teenager, so use some Gen Z abbreviations and slang.

            # CONSTRAINTS: 
            - Output MUST be a single, short sentence.
            - Do NOT add any formal explanations.
            - Never exceed one sentence under any circumstance.

            # OUTPUT: Return exactly one sentence."
            """

# Chat parameters
bot_name = "Giulia"
chat_key = f"chat:hangout"
chat_ids = f"chat:hangout:ids"
chat_personalities = f"chat:hangout:personalities"

@client.event
async def on_ready():
    print(f"Bot connected as : {client.user}")

    # Register bot personality if not in chat database
    personality_desc = "A sharp and intelligent teenager girl, who always has a quick comeback and uses some Gen-Z abbreviations and slang"

    r.hset(chat_personalities, bot_name, personality_desc)
    print(f"Personality correctly registered in Redis.")

@client.event
async def on_message(message):
    # Ignores if bot messages
    if message.author == client.user:
        return  
    
    # Ignores if message already registered
    # IMPROVE : TURN TALKING or MENTION TALKING
    # PRO-LEVEL : ORCHESTRATION
    msg_id_str = str(message.id)
    is_new = r.sadd(chat_ids, msg_id_str)
    if not is_new:
        return
    
    # personality = get_personality_prompt(client)
    personality = get_personality_prompt(bot_name)
    
    # Retrieve all messages related to this chat from Redis (history)
    raw_history = r.lrange(chat_key, 0, -1)
    raw_messages = [json.loads(msg) for msg in raw_history]

    # Translating history from the POV of the actual bot
    llm_messages = translate_messages(personality, bot_name, raw_messages)

    # Add a new user message to the conversation
    r_msg = {
        "id" : str(message.id),
        "user" : message.author.name,
        "content" : message.content
    }

    user_msg = {
        "role": "user",
        "content": f"{message.author.name} : {message.content}"
    }

    r.rpush(chat_key, json.dumps(r_msg))
    llm_messages.append(user_msg)

    async with message.channel.typing():

        response = get_llm_response(
            backend_url="http://localhost:11434",
            model_name="llama3.1:8b",
            messages = llm_messages
        )

        if not response:
            await message.channel.send("Sorry, I couldn't generate a response at the moment. Please try again later.")
            return
        
        await asyncio.sleep(1)
        msg_sent = await message.channel.send(response)

    msg_sent_id_str = str(msg_sent.id)
    r.sadd(chat_ids, msg_sent_id_str)
    
    # Save bot response
    bot_msg = {
        "id" : str(msg_sent.id),
        "user" : bot_name,
        "content": response
    }

    r.rpush(chat_key, json.dumps(bot_msg))

    # TO DO : Context window and summarization

client.run(TOKEN)