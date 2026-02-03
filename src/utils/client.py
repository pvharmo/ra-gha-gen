import asyncio
from time import sleep

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

import env

i = 0


class Client:
    def __init__(self, api_key: str, base_url: str, max_requests: int = 190):
        self.client: AsyncOpenAI = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.requests_count: int = 0
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_requests)

    async def chat(
        self, model: str, messages: list[ChatCompletionMessageParam]
    ) -> str | None:
        """Send an async chat completion request with semaphore limiting."""
        sleep(0.1)
        global i

        async with self.semaphore:
            i += 1
            print(f"Request {i} sent")
            res = await self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return res.choices[0].message.content


client = Client(
    api_key=env.endpoints["openrouter"]["api_key"],
    base_url=env.endpoints["openrouter"]["base_url"],
)
