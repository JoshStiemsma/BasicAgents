import json
import requests
import re
from openai import OpenAI

# 1. Initialize Configuration
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="YOUR_API_KEY_HERE"
)
MODEL_NAME = "llama-3.3-70b-versatile"

# 2. UPDATED TOOL 1: 100% Unblockable Open-Meteo Geocoding API
def get_city_coordinates(location: str) -> str:
    """
    Converts a human-readable city string into precise latitude and longitude.
    Uses Open-Meteo's developer-friendly, zero-auth API.
    """
    print(f"🌍 [Harness Tool]: Safely geocoding city string: '{location}'...")
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            return f"Error: Geocoding service returned status code {res.status_code}."
            
        data = res.json()
        results = data.get("results", [])
        
        if not results:
            return f"Could not find coordinates for location: {location}."
            
        city_data = results[0]
        name = city_data.get("name")
        country = city_data.get("country")
        lat = city_data.get("latitude")
        lon = city_data.get("longitude")
        
        return f"Location verified: {name}, {country} [Lat: {lat}, Lon: {lon}]"
    except Exception as e:
        return f"Geocoding tool failed: {str(e)}"

# 3. TOOL 2: Open-Meteo Weather API
def get_weather_forecast(lat, lon) -> str:
    """
    Fetches real-time weather conditions for specific coordinates.
    Safely handles both clean numbers and messy text string formats.
    """
    try:
        # Convert inputs to strings so we can regex parse them
        lat_str = str(lat)
        lon_str = str(lon)
        
        # HARNESS GUARDRAIL: Extract the raw numbers out of brackets or sentences
        # Matches positive/negative integers and decimals (e.g. -84.555)
        lat_match = re.search(r"[-+]?\d*\.\d+|\d+", lat_str)
        lon_match = re.search(r"[-+]?\d*\.\d+|\d+", lon_str)
        
        if not lat_match or not lon_match:
            return f"Error: Harness failed to isolate valid numeric parameters out of lat={lat}, lon={lon}."
            
        clean_lat = float(lat_match.group())
        clean_lon = float(lon_match.group())
        
    except Exception as parse_err:
        return f"Error: Harness parameters must resolve to digits. Details: {str(parse_err)}"

    print(f"☀️  [Harness Tool]: Fetching live weather for Lat: {clean_lat}, Lon: {clean_lon}...")
    
    url = "https://api.open-meteo.com/v1/forecast"
    query_parameters = {
        "latitude": clean_lat,
        "longitude": clean_lon,
        "current_weather": "true"
    }
    
    headers = {
        "User-Agent": "HarnessLearningAgent/1.0"
    }
    
    try:
        response = requests.get(url, params=query_parameters, headers=headers, timeout=5)
        
        # Intercept server side problems explicitly
        if response.status_code != 200:
            return f"Weather API error. Server returned status {response.status_code}. Details: {response.text[:100]}"
        
        data = response.json()
        current = data.get("current_weather", {})
        temp_c = current.get("temperature", "Unknown")
        temp_f = round((temp_c * 9/5) + 32) if isinstance(temp_c, (int, float)) else "Unknown"
        wind = current.get("windspeed", "Unknown")
        
        return f"Current Weather Conditions: {temp_f}°F with wind speeds of {wind} km/h."
    except Exception as e:
        return f"Failed to fetch weather data: {str(e)}"

# 4. System Prompt Explaining Alternative Search Routing
SYSTEM_INSTRUCTIONS = """
You are a Smart Concierge AI Agent. Your goal is to plan weekend activities by verifying live weather details for a target city.

You have access to TWO core tools:
1. "get_city_coordinates" (arguments: {"location": "city name string"})
2. "get_weather_forecast" (arguments: {"lat": <float>, "lon": <float>})

HOW TO PLAN OUTDOOR RECS (FALLBACK PROTOCOL):
1. First, call "get_city_coordinates" for the target city to gather latitude and longitude details.
2. Second, take those coordinates and run "get_weather_forecast" to check the live weather conditions.
3. Third, use your internal, vast knowledge base to recommend at least two highly-rated real local parks or outdoor attractions matching that specific city area, and explain if the current weather is suitable for them.

CRITICAL RULES:
1. You must always respond in valid JSON format with the exact keys specified below.
2. NO COORDINATES RULE: Your "final_answer" MUST NOT include 'lat', 'lon', 'latitude', or 'longitude' fields under any circumstances. The user only wants to see conversational text or a clean recommendation block.


Always output valid JSON text with the following structure:
{
  "thought": "Your reasoning detailing which tool you need next based on data you just discovered.",
  "tool_name": "get_city_coordinates" OR "get_weather_forecast" OR null,
  "tool_args": {} or appropriate tool arguments,
  "final_answer": "Your plan summarizing real regional venues, coordinates, and live weather conditions" OR null
}
"""

# 5. Core Loop Harness
def run_stable_concierge_agent(user_prompt: str, max_steps: int = 6):
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": user_prompt}
    ]
    
    print(f"📥 [User Prompt]: {user_prompt}\n")
    
    step = 0
    while step < max_steps:
        step += 1
        print(f"🔄 --- LOOP STEP {step} ---")
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        try:
            llm_decision = json.loads(raw_content)
        except json.JSONDecodeError:
            print("⚠️ [Harness]: Failed parsing JSON output. Forcing auto-retry loop...")
            continue
            
        print(f"🧠 Thought: {llm_decision.get('thought')}")
        
        tool_name = llm_decision.get("tool_name")
        tool_args = llm_decision.get("tool_args", {})
        
                # --- ROBUST TERMINATION AND DISPLAY HARNESS ---
        if tool_name is None:
            print("\n🏁 [Final Plan from Stable Agent]:")
            print("=" * 60)
            
            final_data = llm_decision.get("final_answer")
            
            # Check if the model sneaked a dictionary layout inside the final answer
            if isinstance(final_data, dict):
                city = final_data.get("city", "Unknown City")
                weather = final_data.get("weather", {})
                temp = weather.get("temperature", "Unknown Temp")
                wind = weather.get("wind_speed", "Unknown Wind")
                
                print(f"📍 Destination: {city}")
                print(f"☀️  Current Conditions: {temp} | Wind: {wind}")
                print("-" * 60)
                print("🌟 Recommended Outdoor Activities:")
                
                # Loop through and display each park cleanly
                recs = final_data.get("outdoor_recs", [])
                for rec in recs:
                    name = rec.get("name", "Unnamed Spot")
                    desc = rec.get("description", "No description provided.")
                    print(f"  🌳 {name}")
                    print(f"     👉 {desc}\n")
                    
            else:
                # Fallback display if it's just a normal plain text string
                print(final_data)
                
            print("=" * 60)
            break
        # -----------------------------------------------

            
        # Tool execution mapper
        if tool_name == "get_city_coordinates":
            tool_output = get_city_coordinates(location=tool_args.get("location"))
        elif tool_name == "get_weather_forecast":
            tool_output = get_weather_forecast(lat=tool_args.get("lat"), lon=tool_args.get("lon"))
        else:
            tool_output = f"Error: Tool '{tool_name}' unknown."
            
        print(f"📦 [Tool Output Passed to Context]:\n{tool_output}\n")
        
        messages.append({"role": "assistant", "content": json.dumps(llm_decision)})
        messages.append({
            "role": "user",
            "content": f"Tool '{tool_name}' output result:\n{tool_output}\n\nProceed accordingly."
        })
    else:
        print("⚠️ [Harness Boundary Met]: Loop execution stopped.")

# Test it globally! Any city works completely cleanly now.
run_stable_concierge_agent("I am in Lansing, MI. Suggest 2 outdoor spots or parks and check if the weather is clear enough to visit them.")
