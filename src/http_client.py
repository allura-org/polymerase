from typing import Optional, Dict, Any, Union
from result import Result
import httpx

class HttpClient:
    """HTTPX wrapper client that returns Result objects instead of raising exceptions."""
    
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
        """Initialize the HTTP client with optional base URL and configuration."""
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
    
    def _make_request(self, method: str, url: str, **kwargs) -> Result[httpx.Response]:
        """Internal method to make HTTP requests and wrap them in Result."""
        try:
            with httpx.Client(**self._client_kwargs) as client:
                response = client.request(method, url, **kwargs)
                return Result(response, None)
        except Exception as e:
            return Result(None, e)  # type: ignore
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Result[httpx.Response]:
        """Make a GET request."""
        return self._make_request('GET', url, params=params, **kwargs)
    
    def post(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> Result[httpx.Response]:
        """Make a POST request."""
        return self._make_request('POST', url, json=json, data=data, **kwargs)
    
    def put(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> Result[httpx.Response]:
        """Make a PUT request."""
        return self._make_request('PUT', url, json=json, data=data, **kwargs)
    
    def patch(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> Result[httpx.Response]:
        """Make a PATCH request."""
        return self._make_request('PATCH', url, json=json, data=data, **kwargs)
    
    def delete(self, url: str, **kwargs) -> Result[httpx.Response]:
        """Make a DELETE request."""
        return self._make_request('DELETE', url, **kwargs)
    
    def head(self, url: str, **kwargs) -> Result[httpx.Response]:
        """Make a HEAD request."""
        return self._make_request('HEAD', url, **kwargs)
    
    def options(self, url: str, **kwargs) -> Result[httpx.Response]:
        """Make an OPTIONS request."""
        return self._make_request('OPTIONS', url, **kwargs)


class AsyncHttpClient:
    """Async HTTPX wrapper client that returns Result objects instead of raising exceptions."""
    
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
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Result[httpx.Response]:
        """Internal method to make async HTTP requests and wrap them in Result."""
        try:
            async with httpx.AsyncClient(**self._client_kwargs) as client:
                response = await client.request(method, url, **kwargs)
                return Result(response, None)
        except Exception as e:
            return Result(None, e)  # type: ignore
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Result[httpx.Response]:
        """Make an async GET request."""
        return await self._make_request('GET', url, params=params, **kwargs)
    
    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> Result[httpx.Response]:
        """Make an async POST request."""
        return await self._make_request('POST', url, json=json, data=data, **kwargs)
    
    async def put(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> Result[httpx.Response]:
        """Make an async PUT request."""
        return await self._make_request('PUT', url, json=json, data=data, **kwargs)
    
    async def patch(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Union[str, bytes, Dict[str, Any]]] = None, **kwargs) -> Result[httpx.Response]:
        """Make an async PATCH request."""
        return await self._make_request('PATCH', url, json=json, data=data, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> Result[httpx.Response]:
        """Make an async DELETE request."""
        return await self._make_request('DELETE', url, **kwargs)
    
    async def head(self, url: str, **kwargs) -> Result[httpx.Response]:
        """Make an async HEAD request."""
        return await self._make_request('HEAD', url, **kwargs)
    
    async def options(self, url: str, **kwargs) -> Result[httpx.Response]:
        """Make an async OPTIONS request."""
        return await self._make_request('OPTIONS', url, **kwargs)


# Convenience functions for quick HTTP operations
def get(url: str, **kwargs) -> Result[httpx.Response]:
    """Quick GET request using a temporary client."""
    client = HttpClient()
    return client.get(url, **kwargs)

def post(url: str, **kwargs) -> Result[httpx.Response]:
    """Quick POST request using a temporary client."""
    client = HttpClient()
    return client.post(url, **kwargs)

def put(url: str, **kwargs) -> Result[httpx.Response]:
    """Quick PUT request using a temporary client."""
    client = HttpClient()
    return client.put(url, **kwargs)

def delete(url: str, **kwargs) -> Result[httpx.Response]:
    """Quick DELETE request using a temporary client."""
    client = HttpClient()
    return client.delete(url, **kwargs) 
