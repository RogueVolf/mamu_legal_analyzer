import os
import time
import httpx
import random
import asyncio
from cerebras.cloud.sdk import AsyncCerebras

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

    async def get_json_output(self, prompt: str) -> dict:
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

    except Exception as e:
        print(f"Error in LLM Call: {e}")

if __name__=="__main__":
    asyncio.run(ask_llm("Hello"))