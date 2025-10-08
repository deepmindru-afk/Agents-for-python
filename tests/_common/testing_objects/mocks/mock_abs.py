from typing import Union, Callable, Optional
from dataclasses import dataclass

import aiohttp
import asyncio
from aioresponses import aioresponses

def auth_validation(request, allowed_tokens):
    pass

@dataclass
class MockRequest:

    method: str
    url: str
    response: Union[dict, str, Callable]

class MockWeb:

    def __init__(self):

        self._mappings = []
        self._mocker = None

    def _requires_bearer_token(self, func):
        async def wrapper(*args, **kwargs):
            headers = kwargs.get('headers', {})
            auth_header = headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                raise aiohttp.ClientResponseError(
                    request_info=None,
                    history=None,
                    status=401,
                    message="Unauthorized",
                    headers=None
                )
            return await func(*args, **kwargs)
        return wrapper

    def mock_get(self):
        self._mocks.append(('GET', self.mock_request))

    def mock_post(self):
        pass

    def mock_put(self):
        pass

    def mock_delete(self):
        pass

    def _mock_requests(self, mocker):
        methods = {
            "get": mocker.get,
            "post": mocker.post,
            "put": mocker.put,
            "delete": mocker.delete
        }

        for mock in self._mocks:
            method = mock.method.lower()
            if method:
                kwargs = {}
                if callable(mock.response):
                    kwargs["callback"] = mock.response
                elif isinstance(mock.response, dict):
                    kwargs["payload"] = mock.response
                elif isinstance(mock.response, str):
                    kwargs["body"] = mock.response
                else:
                    raise ValueError("Unsupported response type")

                method(mock.url, **kwargs)

    def __aenter__(self):
        if self._mocker is not None:
            raise RuntimeError("Mocker already active")
        self._mocker = aioresponses()
        self._mocker.__enter__()

        self._mock_requests(self._mocker)

        return self

    def __aexit__(self, exc_type, exc_val, exc_tb):
        self._mocker.__exit__(exc_type, exc_val, exc_tb)