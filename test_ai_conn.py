
import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def test_conn():
    api_key = os.getenv("AI_API_KEY")
    base_url = os.getenv("AI_BASE_URL")
    print(f"Testing connection to {base_url} with key {api_key[:6]}...")
    
    if not api_key:
        print("Error: AI_API_KEY not found in environment.")
        return

    try:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model="deepseek-chat", # Trying default model
            messages=[{"role": "user", "content": "Hello, are you working?"}],
            max_tokens=20
        )
        print(f"Success! Response type: {type(response)}")
        print(f"Response content: {response}")
        # print(response.choices[0].message.content)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
