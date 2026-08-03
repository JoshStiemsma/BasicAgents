import json
import requests
import os
from openai import OpenAI

# 1. Initialize Clients & Configuration
client = OpenAI(
     base_url="https://api.groq.com/openai/v1",
    api_key="YOUR_API_KEY_HERE"  # <-- Replace with your free Groq API key
)
MODEL_NAME = "llama-3.3-70b-versatile"
MEMORY_FILE = "repo_memory.txt"

def save_memory(user: str, messages: str):
    """Saves the current state of conversation to a file."""
    with open(MEMORY_FILE, "a") as f:
        f.write('\n')
        f.write(user + '\n')
        f.write(messages + "\n")

# 2. Define the Real-World GitHub Tool Function
def search_github_repositories(query: str, language: str = None) -> str:
    """
    Queries the live GitHub REST API for public repositories matching a query string.
    Filters by coding language if specified.
    """
    url = "https://api.github.com/search/repositories"
    
    # Construct the query string (e.g., 'web scraper language:python')
    api_query = query
    if language:
        api_query += f" language:{language}"
        
    params = {
        "q": api_query,
        "sort": "stars",    # Sort by stars to get the highest quality projects first
        "order": "desc",
        "per_page": 5       # Limit to top 5 results to prevent cluttering LLM memory
    }
    
    # GitHub requires a User-Agent header for API requests
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HarnessLearningAgent/1.0"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            return f"GitHub API Error: {response.status_code} - {response.text}"
            
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            return "No repositories found for that query."
            
        # Format the repository data cleanly for the LLM to read
        formatted_results = []
        for item in items:
            repo_info = (
                f"• Name: {item['full_name']}\n"
                f"  Stars: ⭐ {item['stargazers_count']}\n"
                f"  Description: {item['description']}\n"
                f"  URL: {item['html_url']}\n"
            )
            formatted_results.append(repo_info)
            
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Failed to execute GitHub search tool: {str(e)}"

# 3. System Prompt explaining how the Agent functions
SYSTEM_INSTRUCTIONS = """
You are an expert GitHub Project Scout AI Agent. Your goal is to help users find awesome open-source projects.
You parse what the user needs, construct optimal keywords, look them up using your tool, and recommend the best ones.

You have access to exactly ONE tool:
- "search_github_repositories" (arguments: {"query": <string>, "language": <string_or_null>})

CRITICAL RULES:
1. You must always respond in JSON format with the exact keys specified below.
2. In your "final_answer", you MUST include the URL links provided in the tool output as readable by a human wiwth no extra coding or html surrounding them. 
3. QUOTA RULE: You must evaluate and include at least THREE (3) distinct repository choices from the tool output in your final answer. Do not summarize them into a single option. If the tool output contains fewer than 3 options, state that explicitly.

Format layout template:
{
  "thought": "Your step-by-step reasoning about why you are selecting this tool or summarizing results.",
  "tool_name": "search_github_repositories" OR null (if you are finished and providing the final answer),
  "tool_args": {"query": "keywords", "language": "python"} OR {},
  "final_answer": "Your formatted project recommendations including the URL links" OR null (if you are running a tool)
}
"""

# 4. Multi-Step Execution Loop (The Harness)
def run_github_agent(user_prompt: str, max_steps: int = 5):
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": user_prompt}
    ]
    
    print(f"[User Query]: {user_prompt}\n")
    
    step = 0
    while step < max_steps:
        step += 1
        print(f" --- LOOP STEP {step} ---")
        
        # Call the live LLM endpoint
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        # Harness Interception & JSON Validation Guardrail
        try:
            llm_decision = json.loads(raw_content)
        except json.JSONDecodeError as e:
            print(" [Harness Guardrail]: LLM failed valid JSON. Injecting correction rule...")
            messages.append({"role": "assistant", "content": raw_content})
            messages.append({"role": "user", "content": f"JSON parse error: {str(e)}. Please correct your format."})
            continue
            
        print(f"🧠 Thought: {llm_decision.get('thought')}")
        
        tool_name = llm_decision.get("tool_name")
        tool_args = llm_decision.get("tool_args", {})
        
        # Check if the agent is satisfied and ready to present the final answer
        if tool_name is None:
            print(f"\n🏁 [Final Answer from Agent]:\n{llm_decision.get('final_answer')}")
            llm_formated = llm_decision.get('final_answer')
            save_memory(user_prompt, llm_formated)
            break
            
        # Execute the live GitHub search tool
        if tool_name == "search_github_repositories":
            q = tool_args.get("query")
            lang = tool_args.get("language")
            print(f"⚙️  [Harness]: Fetching live data from GitHub for query='{q}', lang='{lang}'...")
            
            tool_output = search_github_repositories(query=q, language=lang)
            print(f" [Tool Output]: Successfully retrieved repository payload.\n")
            
            # Feed the API data back into the LLM's history window
            messages.append({"role": "assistant", "content": json.dumps(llm_decision)})
            messages.append({
                "role": "user", 
                "content": f"GitHub Search Tool Results:\n{tool_output}\n\nReview these results and provide your final selection or search again if needed."
            })
        else:
            print(f"⚠️ [Harness]: Unknown tool '{tool_name}' requested.")
            break
    else:
        print("⚠️ [Harness Notice]: Step limit reached.")

user_input = input("What would you like to find in github repos?")
# 5. Run the live Agent
run_github_agent(user_input)
