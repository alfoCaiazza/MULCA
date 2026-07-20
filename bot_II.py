import os
import discord
from dotenv import load_dotenv
from ask_llm import get_llm_response
import redis
import json
import time

load_dotenv()
TOKEN = os.getenv('BOTII_TOKEN')

# Redis init
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, max_connections=3)

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# Bot prompts
def get_personality_prompt(bot_name: str) -> str:
    return f"""# ROLE: Act like {bot_name}, a Gen-Z teenager and life-time friend who always replies to chat messages.

            # CONTEXT: You will receive an overview of the conversation history. Reply ONLY to the very last message, referencing previous information if necessary.

            # INSTRUCTIONS: Your personality is intelligent, with a unique sense of humor. You usually don't use any slang or emoji.

            # CONSTRAINTS: 
            - Output MUST be a single, short sentence.
            - Do NOT add any formal explanations.
            - Never exceed one sentence under any circumstance.

            # OUTPUT: Return exactly one sentence."
            """
# Chat parameters
bot_name = "Giulia"
chat_key = f"chat:hangout"

@client.event
async def on_ready():
    print(f"Bot connected as : {client.user}")

@client.event
async def on_message(message):
    # Ignores if bot messages
    if message.author == client.user:
        return  
    
    # personality = get_personality_prompt(client)
    personality = get_personality_prompt(bot_name)
    
    # Retrieve all messages related to this chat from Redis (history)
    raw_history = r.lrange(chat_key, 0, -1)
    messages = [json.loads(msg) for msg in raw_history]

    # Initialization if first message
    if not messages:
        system_msg = {"role": "system", "content": personality}
        messages.append(system_msg)
        r.rpush(chat_key, json.dumps(system_msg))

    # Add a new user message to the conversation
    user_msg = {
        "role": "user",
        "content": message.content
    }

    r.rpush(chat_key, json.dumps(user_msg))
    messages.append(user_msg)

    response = get_llm_response(
        backend_url="http://localhost:11434",
        model_name="llama3.1:8b",
        messages = messages,
        stream=False
    )

    if not response:
        await message.channel.send("Sorry, I couldn't generate a response at the moment. Please try again later.")
        return

    # Save bot response
    bot_msg = {
        "role": "assistant",
        "content": response
    }
    r.rpush(chat_key, json.dumps(bot_msg))
    
    # time.sleep(1) Add a small delay to ensure readability during the conversation
    await message.channel.send(response)

    # TO DO : Context window and summarization

client.run(TOKEN)