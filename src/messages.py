from msgspec import Struct
from msgspec import json as msgspec_json
from result import Result, Ok, Err, is_ok
from http_client import AsyncHttpClient
from typing import Self
from httpx import Response

class Message(Struct):
    role: str
    content: str
    reasoning: str | None = None

class Request(Struct):
    messages: list[Message]
    temperature: float | None = None
    top_p: float | None = None

    _raw_response: Result[Response] | None = None
    
    async def req(self, http_client: AsyncHttpClient, model: str) -> Result[Self]:
        res = await http_client.post(
            url="/chat/completions",
            json={
                "model": model,
                "messages": msgspec_json.decode(msgspec_json.encode(self.messages).decode()), # TODO: what the fuck
                "temperature": self.temperature,
                "top_p": self.top_p,
            },
        )
        self._raw_response = res
        res = res.map_ok(lambda res: res.json())
        if is_ok(res):
            res = res.unwrap()
            messages = self.messages + [
                Message(
                    role="assistant",
                    content=res["choices"][0]["message"]["content"],
                    reasoning=res["choices"][0]["message"].get("reasoning_content"),
                )
            ]
            return Ok(Request(messages=messages))
        else:
            return Err(res.unwrap_err())