import os
import json
from openai import OpenAI

# Initialize your client
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="YOUR_API_KEY_HERE"
)
MODEL_NAME = "llama-3.3-70b-versatile"
MEMORY_FILE = "agent_memory.json"

# Minimal system prompt for memory demonstration
SYSTEM_INSTRUCTIONS = "You are a helpful assistant. Keep answers brief."

# --- HARNESS UTILITIES: PERSISTENCE LAYER ---
def load_memory() -> list:
    """Loads past conversation from a file, or starts fresh if none exists."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            print("[Harness]: Found existing memory file. Resuming session...")
            return json.load(f)
    return [{"role": "system", "content": SYSTEM_INSTRUCTIONS}]

def save_memory(messages: list):
    """Saves the current state of conversation to a file."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f, indent=2)
    print("[Harness]: State successfully saved to local disk.")

# --- HARNESS UTILITIES: CONTEXT COMPACTION ---
def compact_context_if_needed(messages: list) -> list:
    """If history is too long, condenses old messages into a summary."""
    # We ignore the system prompt, so check if length is > 7 (System + 6 turns)
    if len(messages) <= 20:
        return messages
        
    print(" [Harness Guardrail]: Context window getting crowded! Compacting...")
    
    # Separate the system prompt from the actual conversation
    system_prompt = messages[0]
    conversation_to_shrink = messages[1:-2]  # Keep system prompt and the last 2 messages intact
    messages_to_keep = messages[-2:]          # The most recent back-and-forth
    
    # Call the LLM with a meta-instruction to summarize the old thread
    summary_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "Summarize the key facts from this conversation thread briefly into 4 lines."},
            {"role": "user", "content": json.dumps(conversation_to_shrink)}
        ]
    )
    summary_text = summary_response.choices[0].message.content.strip()
    print(f"[Harness Summary Generated]: {summary_text}")
    
    # Rebuild history: System Prompt + The Summary + The last 2 recent turns
    compacted_messages = [
        system_prompt,
        {"role": "system", "content": f"Summary of past conversation: {summary_text}"},
        *messages_to_keep
    ]
    return compacted_messages

# --- MAIN CONVERSATION LOOP ---
def chat_with_persistent_agent(user_input: str):
    # 1. Load historical state from disk
    messages = load_memory()
    
    # 2. Append new user query
    messages.append({"role": "user", "content": user_input})
    
    # 3. Apply harness guardrail: Check if we need to compact context
    messages = compact_context_if_needed(messages)
    
    print(f"\n [User]: {user_input}")
    
    # 4. Generate response
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages
    )
    
    reply = response.choices[0].message.content.strip()
    print(f"[Agent]: {reply}\n")
    
    # 5. Append assistant reply and save back to disk
    messages.append({"role": "assistant", "content": reply})
    save_memory(messages)

keepGoing=True
end_statements = ["end","End"]
while keepGoing:
    user_input = input("What would you like to say? Type end to stop talking.")
    if user_input in end_statements:
        keepGoing = False
    else:
        chat_with_persistent_agent(user_input)
        
# --- Test the session persistence ---
# Try running these lines one by one, or rerun the entire script multiple times!
#chat_with_persistent_agent("Hi, my name is Alex and I live in Michigan.")
#chat_with_persistent_agent("What is my name and where do I live?")
#chat_with_persistent_agent("I also have a dog named Sparky.")
#chat_with_persistent_agent("What pet do I have?")
#chat_with_persistent_agent("I am also learning how to build and use ai agents!")
#chat_with_persistent_agent("Awesome! Right now im testing your memory capabilities by saving them to a file.")
