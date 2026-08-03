import json
import subprocess
import sys
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="YOUR_API_KEY_HERE"
)
MODEL_NAME = "llama-3.3-70b-versatile"

class MCPClientHarness:
    def __init__(self):
        # Determine the runtime executor platform automatically
        cmd = "python3" if sys.platform != "win32" else "py"
        
        # Launch server with text stream tracking enabled
        self.process = subprocess.Popen(
            [cmd, "server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, # Redirection: Throw away stray background errors
            text=True
        )
        self.request_id = 0

    def send_rpc(self, method: str, params: dict = None) -> dict:
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params or {}}
        
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()
        
        response_line = self.process.stdout.readline().strip()
        if not response_line:
            return {"error": "Server connection stream dropped."}
            
        try:
            return json.loads(response_line)
        except json.JSONDecodeError:
            # Shield client loop by passing the error text data cleanly
            return {"error": f"Data stream unaligned. Received text fragment: {response_line}"}

    def get_server_tools(self) -> list:
        res = self.send_rpc("tools/list")
        return res.get("result", {}).get("tools", [])

    def call_server_tool(self, name: str, arguments: dict) -> str:
        res = self.send_rpc("tools/call", {"name": name, "arguments": arguments})
        content_list = res.get("result", {}).get("content", [])
        if content_list and len(content_list) > 0:
            return content_list[0].get("text", "{}")
        return "{}"

    def run_loop(self, prompt: str):
        mcp_tools = self.get_server_tools()
        
        formatted_api_tools = []
        for tool in mcp_tools:
            formatted_api_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                }
            })

        messages = [
            {"role": "system", "content": "You are a helpful travel assistant. Find coordinates, check the weather, and then name 2 great local parks for the city. Reply conversational text only, do not output JSON blocks to the user."},
            {"role": "user", "content": prompt}
        ]

        print(f"📥 [User Query]: {prompt}\n")

        for step in range(1, 5):
            print(f"🔄 --- Loop Step {step} ---")
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                tools=formatted_api_tools
            )
            
            message = response.choices[0].message
            messages.append(message)

            if message.tool_calls:
                tool_call = message.tool_calls[0] # Focus tool target explicitly
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                print(f"⚙️  [Harness]: Executing MCP Tool '{name}' with args {args}...")
                tool_result = self.call_server_tool(name, args)
                print(f"📦 [Server Tool Output]: {tool_result}\n")
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": str(tool_result)
                })
            else:
                print("\n🏁 [Final Answer from MCP Agent]:")
                print("=" * 60)
                print(message.content)
                print("=" * 60)
                break
                
        self.process.terminate()

if __name__ == "__main__":
    harness = MCPClientHarness()
    harness.run_loop("I'm planning a visit to Lansing, MI. How's the weather, and are there good parks?")
