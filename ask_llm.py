import requests
from collections import deque

def get_llm_response(backend_url: str, model_name: str, messages: list, stream: bool = False) -> str:
    try:
        response = requests.post(
            f"{backend_url}/api/chat",
            json={
                "model": model_name,
                "messages": messages,
                "stream": stream
            }
        )
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            print(f"Error: Received status code {response.status_code} from LLM backend.")
            return ""
    except requests.exceptions.RequestException as e:
        print(f"Error while requesting LLM response: {e}")
        return ""


def build_conversation_history(conversations: dict, user_id: int, new_message: str, system_prompt: str) -> list:
    history = list(conversations[user_id])

    messages = [{"role": "system", "content": system_prompt}] + history
    messages.append({"role": "user", "content": new_message})
    return messages


def summarize_conversation(backend_url: str, model_name: str, conversations: dict, user_id: int, summary_prompt: str, threshold: int = 10) -> None:
    history = list(conversations[user_id])
    if len(history) < threshold:
        return 

    # Conversation text to summarize
    convo_text = "\n".join(f'{m["role"]}: {m["content"]}' for m in history)

    messages = [
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": convo_text}
    ]

    summary = get_llm_response(backend_url, model_name, messages)

    # Replace history with a single summary message
    conversations[user_id] = deque( [{"role": "system", "content": f"Past conversation summary: {summary}"}],maxlen=conversations[user_id].maxlen)

def translate_messages(bot_personality: str, bot_name: str, history: list) -> list:
    llm_messages =[{
        "role": "system",
        "content": bot_personality # Injecting bot personality
    }]

    for msg in history:
        user = msg["user"]
        content = msg["content"]

        if user == bot_name:
            llm_messages.append({
                "role" : "assistant",
                "content" : content
            })
        else:
            llm_messages.append({
                "role" : "user",
                "content" : f"[{user.upper()} : {content}]"
            })

    return llm_messages