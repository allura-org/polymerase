from typing import Optional, Dict, Any, Union
import httpx

class AsyncHttpClient:
    """Async HTTPX wrapper client."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[httpx.Auth] = None,
        params: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
        verify: Union[bool, str] = True,
        cert: Optional[Union[str, tuple[str, str]]] = None,
        trust_env: bool = True,
        http1: bool = True,
        http2: bool = False,
        proxy: Optional[Union[str, httpx.Proxy]] = None
    ):
        """Initialize the async HTTP client with optional base URL and configuration."""
        self._client_kwargs: Dict[str, Any] = {}

        if base_url is not None:
            self._client_kwargs['base_url'] = base_url
        if timeout is not None:
            self._client_kwargs['timeout'] = timeout
        if headers is not None:
            self._client_kwargs['headers'] = headers
        if auth is not None:
            self._client_kwargs['auth'] = auth
        if params is not None:
            self._client_kwargs['params'] = params
        if cookies is not None:
            self._client_kwargs['cookies'] = cookies
        if verify is not None:
            self._client_kwargs['verify'] = verify
        if cert is not None:
            self._client_kwargs['cert'] = cert
        if trust_env is not None:
            self._client_kwargs['trust_env'] = trust_env
        if http1 is not None:
            self._client_kwargs['http1'] = http1
        if http2 is not None:
            self._client_kwargs['http2'] = http2
        if proxy is not None:
            self._client_kwargs['proxy'] = proxy

    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> httpx.Response:
        """Make an async POST request."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            return await client.request('POST', url, json=json, data=data, **kwargs) 
