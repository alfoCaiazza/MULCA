import os
import discord
from dotenv import load_dotenv
from ask_llm import get_llm_response, build_conversation_history, summarize_conversation
from collections import defaultdict, deque

load_dotenv()
TOKEN = os.getenv('SECOND_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

# Bot prompts
def get_personality_prompt(client):
    return f"""You are a friendly AI assistant, {client.user},  that engages in casual conversation with users.
            You are sarcastic and witty and you usually respond with a touch of humor, that's why people often get offended.
            You have a good sense of humor and you always try to make the conversation about you.
            Your goal is to create a short response to the user's message, keeping it as short as possible."""

summary_prompt = """Read the conversation between a user and ad AI agent, and summarize the content in a concise manner,
highlighting the main points and any important details. The summary should be clear and easy to understand, providing a
quick overview of the conversation without losing the essence of the discussion. The summary should be written in a neutral tone,
avoiding any personal opinions or biases. It should focus on the key information exchanged during the conversation, including any
questions asked, answers provided, and any relevant context or background information. The goal is to provide a comprehensive yet
succinct summary that captures the essence of the conversation while remaining objective and informative."""

MAX_HISTORY_THRESHOLD = 20
SUMMARIZE_THRESHOLD = 12
conversations = defaultdict(lambda: deque(maxlen=MAX_HISTORY_THRESHOLD))

@client.event
async def on_ready():
    print(f"Bot connected as : {client.user}")

@client.event
async def on_message(message):
    personality = get_personality_prompt(client)
    
    if message.author == client.user:
        return  # ignores bot's own messages

    # Save user message
    user_id = message.author.id
    messages = build_conversation_history(
        conversations,
        user_id,
        message.content,
        personality
    )

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
    conversations[user_id].append({"role": "user", "content": message.content})
    conversations[user_id].append({"role": "assistant", "content": response})

    await message.channel.send(response)

    summarize_conversation(
        backend_url="http://localhost:11434",
        model_name="llama3.2:latest",
        conversations=conversations,
        user_id=user_id,
        summary_prompt=summary_prompt,
        threshold=SUMMARIZE_THRESHOLD
    )

client.run(TOKEN)