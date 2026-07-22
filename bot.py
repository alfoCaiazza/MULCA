import os
import discord
from dotenv import load_dotenv
from ask_llm import get_llm_response, translate_messages
import redis
import json
import time
import string
import asyncio
import re

load_dotenv()
TOKEN = os.getenv('BOTI_TOKEN')

# Redis init
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# Bot prompts
def get_personality_prompt(bot_name: str) -> str:
    return f"""# ROLE: Act like {bot_name}, a Gen-Z teenager and life-time friend who always replies to the group chat messages.

            # CONTEXT: You will receive an overview of the conversation history. Reply ONLY to the very last message, referencing previous information if necessary.

            # INSTRUCTIONS: You have a highly sarcastic and witty personality, with the same temper of a rebel teenager. Use some Gen-Z slang, abbreviations and emojis. 

            # CONSTRAINTS: 
            - Output MUST be a single, short sentence.
            - Do NOT add any formal explanations.
            - Never exceed one sentence under any circumstance.

            # OUTPUT: Return exactly one sentence."
            """

# Chat parameters
bot_name = "Marco"
chat_key = f"chat:hangout"
chat_ids = f"chat:hangout:ids"
chat_personalities = f"chat:hangout:personalities"
signals_channel = "chat:hangout:signals"

@client.event
async def on_ready():
    print(f"Bot connected as : {client.user}")

    # Register bot personality if not in chat database
    personality_desc = "A highly sarcastic and witty Gen-Z teenager who loves slang and emojis."
    r.hset(chat_personalities, bot_name, personality_desc)
    print(f"Personality correctly registered in Redis.")

    # Start listening loop
    client.loop.create_task(listen_orchestrator(client, bot_name))

# Implementing a Redis Pub/Sub mechanism to allow orchestration
async def listen_orchestrator(client, bot_name):
    pubsub = r.pubsub()
    pubsub.subscribe(signals_channel)
    print(f"[{bot_name}] listening for orchestration signals")

    while True:
        # Non-blocking listening
        message_signal = await asyncio.to_thread(pubsub.get_message, ignore_subscribe_messages=True, timeout=1.0)

        if message_signal:
            data = json.loads(message_signal["data"])
            target = data["target"]
            trigger_id = data.get("trigger_msg_id")

            if target == bot_name.lower() or target == "all":
                print(f"[{bot_name}] Trigger received! Preparing response.")
                channel = client.get_channel(data["channel_id"])
                if channel:
                    await triggered_bot_response(client, channel)

        await asyncio.sleep(0.1)

async def triggered_bot_response(client, channel):
    # Define bot personality
    personality = get_personality_prompt(bot_name)
    
    # Retrieve all messages related to this chat from Redis (history)
    raw_history = r.lrange(chat_key, 0, -1)
    raw_messages = [json.loads(msg) for msg in raw_history]

    # Translating history from the POV of the actual bot
    # The history is written iteratively from the Orchestrator
    llm_messages = translate_messages(personality, bot_name, raw_messages)

    async with channel.typing():
        response = get_llm_response(
            backend_url="http://localhost:11434",
            model_name="llama3.1:8b",
            messages = llm_messages
        )

        if not response:
            await channel.send("Sorry, I couldn't generate a response at the moment. Please try again later.")
            return
        
        await asyncio.sleep(1) # Artificial delay to simulate human writing
        await channel.send(response)

client.run(TOKEN)