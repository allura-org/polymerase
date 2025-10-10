from msgspec import Struct
from msgspec import json as msgspec_json
from http_client import AsyncHttpClient
from typing import Self
from httpx import Response

class Message(Struct, omit_defaults=True):
    role: str
    content: str
    reasoning: str | None = None

class Request(Struct):
    messages: list[Message]
    temperature: float | None = None
    top_p: float | None = None

    _raw_response: Response | None = None

    async def req(self, http_client: AsyncHttpClient, model: str) -> Self:
        res = await http_client.post(
            url="/chat/completions",
            json={
                "model": model,
                "messages": msgspec_json.decode(msgspec_json.encode(self.messages).decode()), # TODO: what the fuck
                "temperature": self.temperature,
                "top_p": self.top_p
            },
        )
        self._raw_response = res
        json_response = res.json()
        messages = self.messages + [
            Message(
                role="assistant",
                content=json_response["choices"][0]["message"]["content"],
                reasoning=json_response["choices"][0]["message"].get("reasoning_content"),
            )
        ]
        return Request(messages=messages)
