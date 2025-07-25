import os
import time
import httpx
import random
import asyncio
from dotenv import load_dotenv
from cerebras.cloud.sdk import AsyncCerebras

load_dotenv(".env")

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"] # Replace with your OpenRouter key

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

payload_template = {
    "model": "gpt-4.1-mini",
    "messages": [],
    "temperature": 0.2,
    "max_tokens": 1000,
}

http_client = httpx.AsyncClient(
                http2=True,  # <- Enables HTTP/2
                timeout=httpx.Timeout(15.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
            )

client = AsyncCerebras(
    api_key=os.environ.get("CEREBRAS_API_KEY"),  # This is the default and can be omitted
    http_client=http_client
)

class OpenRouterClient:
    def __init__(self):
        self.client = None

    async def init_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers=headers,
                http2=True,  # <- Enables HTTP/2
                timeout=httpx.Timeout(15.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
            )

    async def close_client(self):
        if self.client:
            await self.client.aclose()

    async def get_json_output(self, prompt: str) -> dict:
        await self.init_client()
        time.sleep(random.randint(0,3))

        messages = [
            {"role": "user", "content": prompt}
        ]

        response = await client.chat.completions.create(
            messages=messages,
            model="llama-4-scout-17b-16e-instruct",
            response_format={"type":"json_object"}
        )
        return response.choices[0].message.content


async def ask_llm(message):
    client = OpenRouterClient()
    try:
        response = await client.get_json_output(message)
        print(response)
        
        return response
    
    finally:
        await client.close_client()


if __name__=="__main__":
    asyncio.run(ask_llm("Hello"))