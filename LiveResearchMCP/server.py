import sys
import json
import requests

# PREVENT LOG POLLUTION: Explicitly redirect all environment warnings away from stdout
import warnings
warnings.filterwarnings("ignore")

def get_city_coordinates(location: str) -> dict:
    url = "https://open-meteo.com"
    params = {"name": location, "count": 1, "language": "en", "format": "json"}
    headers = {"User-Agent": "McpLearningSandboxApp/1.0"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        
        # Intercept connection failures cleanly instead of throwing a hard exception
        if res.status_code != 200:
            return {"error": f"Geocoding server returned HTTP status code {res.status_code}."}
            
        data = res.json()
        results = data.get("results", [])
        if not results:
            return {"error": f"Could not find coordinates for city: {location}."}
            
        city = results[0] # Grab first result array element
        return {"name": city["name"], "lat": city["latitude"], "lon": city["longitude"]}
    except Exception as e:
        # Pass the message text back safely as string data so the protocol doesn't snap
        return {"error": f"Geocoding tool network exception: {str(e)}"}

def get_weather_forecast(lat: float, lon: float) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": float(lat), "longitude": float(lon), "current_weather": "true"}
    headers = {"User-Agent": "McpLearningSandboxApp/1.0"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code != 200:
            return {"error": f"Weather satellite returned HTTP status code {res.status_code}."}
            
        current = res.json().get("current_weather", {})
        temp_c = current.get("temperature", 0)
        temp_f = round((temp_c * 9/5) + 32)
        return {"temperature": f"{temp_f}°F", "wind_speed": f"{current.get('windspeed')} km/h"}
    except Exception as e:
        return {"error": f"Weather tool network exception: {str(e)}"}

def main():
    TOOLS = [
        {
            "name": "get_city_coordinates",
            "description": "Converts a city name into precise latitude and longitude coordinates.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The name of the city"}
                },
                "required": ["location"]
            }
        },
        {
            "name": "get_weather_forecast",
            "description": "Fetches current weather details for a specific latitude and longitude.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "The numeric latitude coordinate"},
                    "lon": {"type": "number", "description": "The numeric longitude coordinate"}
                },
                "required": ["lat", "lon"]
            }
        }
    ]

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            method = request.get("method")
            req_id = request.get("id")

            if method == "tools/list":
                response = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
            
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name == "get_city_coordinates":
                    data = get_city_coordinates(arguments.get("location"))
                elif tool_name == "get_weather_forecast":
                    data = get_weather_forecast(arguments.get("lat"), arguments.get("lon"))
                else:
                    data = {"error": f"Tool {tool_name} not found"}

                response = {
                    "jsonrpc": "2.0", 
                    "id": req_id, 
                    "result": {"content": [{"type": "text", "text": json.dumps(data)}]}
                }
            else:
                response = {"jsonrpc": "2.0", "id": req_id, "error": {"message": "Unknown method"}}

            # Flatten output to exactly one line to avoid splitting across stdout streams
            clean_payload = json.dumps(response, separators=(',', ':')).strip()
            sys.stdout.write(clean_payload + "\n")
            sys.stdout.flush()

        except Exception as e:
            sys.stderr.write(f"Background Handler Warning: {str(e)}\n")
            sys.stderr.flush()

if __name__ == "__main__":
    main()
