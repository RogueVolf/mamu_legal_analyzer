import os
import time
import httpx
import random
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(".env")

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"] # Replace with your OpenRouter key



http_client = httpx.AsyncClient(
                http2=True,  # <- Enables HTTP/2
                timeout=httpx.Timeout(15.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
            )

client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY, 
    http_client=http_client,
    base_url="https://openrouter.ai/api/v1"
)

class OpenRouterClient:
    def __init__(self):
        self.client = None

    async def get_json_output(self, prompt: str) -> dict:
        messages = [
            {"role": "user", "content": prompt}
        ]

        response = await client.chat.completions.create(
            messages=messages,
            model="gpt-4.1-mini",
            response_format={"type":"json_object"}
        )
        return response.choices[0].message.content


async def ask_llm(message):
    client = OpenRouterClient()
    try:
        response = await client.get_json_output(message)
        print(response)
        
        return response
    
    except Exception as e:
        print(f"Error in LLM call {e}")


if __name__=="__main__":
    asyncio.run(ask_llm("Hello"))