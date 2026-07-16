import os
import discord
from dotenv import load_dotenv
from ask_llm import get_llm_response, build_conversation_history, summarize_conversation
from collections import defaultdict, deque
import redis
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Redis init
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# Bot prompts
def get_personality_prompt(client):
    return f"""You are a friendly AI assistant, {client.user},  that engages in casual conversation with users.
            You are helpful, polite, and always try to provide useful information or assistance.
            You have a good sense of humor and enjoy making the conversation enjoyable for the user.
            Your goal is to create a short but engagin response to the user's message, keeping it as short as possible."""

@client.event
async def on_ready():
    print(f"Bot connected as : {client.user}")

@client.event
async def on_message(message):
    # Ignores if bot messages
    if message.author == client.user:
        return  
    
    personality = get_personality_prompt(client)
    chat_key = f"chat:friends"
    
    # Retrieve all messages related to this chat from Redis (history)
    raw_history = r.lrange(chat_key, 0, -1)
    messages = [json.loads(msg) for msg in raw_history]

    # Initialization if first message
    if not messages:
        system_msg = {"role": "system", "content": personality}
        r.rpush(chat_key, json.dumps(system_msg))

    # Add a new user message to the conversation
    user_msg = {"role": "user", "content": message.content}
    r.rpush(chat_key, json.dumps(user_msg))
    messages.append(user_msg)

    response = get_llm_response(
        backend_url="http://localhost:11434",
        model_name="llama3.2:latest",
        messages = messages,
        stream=False
    )

    if not response:
        await message.channel.send("Sorry, I couldn't generate a response at the moment. Please try again later.")
        return

    # Save bot response
    bot_msg = {"role": "assistant", "content": response}
    r.rpush(chat_key, json.dumps(bot_msg))
    await message.channel.send(response)

    # TO DO : Context window and summarization

client.run(TOKEN)