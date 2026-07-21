from ask_llm import get_llm_response, translate_messages
import os
import redis
import discord
import json
from dotenv import load_dotenv
import re

# Define a Super Partes Bot which:
#  1 - read the messages just arrived in the channel
#  2 - decide whose bot should respond to it based on their prompt personality
#  3 - select the relative bot and send the messages to it

load_dotenv()
ORCHESTRATOR = os.getenv("ORCHESTRATOR")

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

chat_key = f"chat:hangout"
chat_personalities = f"chat:hangout:personalities"

def super_partes_prompt(users_dict : dict[str, str]) -> str:
    participants = "\n".join(
        [f"- **{name}**: {desc}" for name, desc in users_dict.items()]
    )
    return f""" # ROLE : You are a super partes chat moderator and orchestrator. Your goal is to choose the next participant who has to reply to the last message in a chat group.
    
    # CONTEXT: You will receive an overview of the chat message history. Focus primarily on the very last message and use previous context to understand the conversational flow.    # INSTRUCTION : You have to analize the semantic content of the message and decide which of the user should respond next in the chat.
    
    # PARTICIPANTS AND PROFILES:
    {participants}

    # INSTRUCTIONS: Analyze the semantic content of the last message, contextual relevance, and the specific personalities described above to decide which participant is best suited to respond next.

    # CONSTRAINTS : Follow these rules to choose correctly the user:
        - Choose ONLY ONE participant from the provided list, OR use [ALL] if the message is a general question directed at everyone or requires multiple reactions.
        - Do not invent names outside the provided participants list.
        - Output MUST be concise and strictly follow the output format.

    # OUTPUT: Return the name of the chosen user or [ALL] enclosed in brackets or a clear tag (e.g., <target>Marco</target> or [Marco])."""


@client.event
async def on_ready():
    print(f"Super Partes Orchestrator connected as : {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Retrieve all personalities
    personalities = r.hgetall(chat_personalities)
    avaiable_users = list(personalities.keys())

    # Check for connected bots
    if not avaiable_users:
        return
    
    # Retrieve all messages related to this chat from Redis (history)
    raw_history = r.lrange(chat_key, 0, -1)
    raw_messages = [json.loads(msg) for msg in raw_history]

    prompt = super_partes_prompt(personalities)

    llm_messages = translate_messages(prompt, None, raw_messages)

    # Obtain Super Partes LLM response
    response = get_llm_response(
            backend_url="http://localhost:11434",
            model_name="llama3.1:8b",
            messages = llm_messages
    )

    # Extracitng LLM response
    match = re.search(r"\[([A-Za-z0-9_]+)\]", response)
    if match:
        chosen_target = match.group(1)
        print(f"Target selected to reply: {chosen_target}")

    await  message.channel.send(f"Super Partes verdict:\nThe one who has to respond is {chosen_target}")

client.run(ORCHESTRATOR)
