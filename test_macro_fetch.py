import sys
import os
import asyncio
import time
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

# Mock fastAPI things if needed
os.environ["NO_PROXY"] = "*"

from app.api.endpoints.market import api_market_weekly

async def test_endpoint():
    print("Starting Weekly API Endpoint test...")
    start_time = time.time()
    try:
        response = await api_market_weekly()
        elapsed = time.time() - start_time
        print(f"API called successfully in {elapsed:.2f} seconds.")
        
        # Parse JSON body
        body = json.loads(response.body)
        print("Response Keys:", body.keys())
        print("Macro Brief:", body.get("macro_brief"))
        print("Items Count:", len(body.get("items", [])))
        if body.get("items"):
            print("First Item:", body["items"][0])
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"API call failed after {elapsed:.2f} seconds.")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint())
