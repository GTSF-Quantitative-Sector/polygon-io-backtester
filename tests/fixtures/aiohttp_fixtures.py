import pytest
from asyncmock import AsyncMock, MagicMock
import json

class MockContextManager:

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __aenter__(self, *args, **kwargs):
        raise NotImplementedError

    async def __aexit__(self, *args, **kwargs):
        return

@pytest.fixture
def mock_aiohttp_timeout():

    class MockResponse:

        async def json(self):
            raise TimeoutError()

    class GetContextManager(MockContextManager):
        async def __aenter__(self, *args, **kwargs):
            return MockResponse()

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = GetContextManager)
    return mock

@pytest.fixture
def mock_aiohttp_financials_success():

    class MockResponse:
        
        async def json(self):
            with open('tests/fixtures/data/sample_financials_response.json') as f:
                return json.load(f)        

    class GetContextManager(MockContextManager):

        async def __aenter__(self, *args, **kwargs):
            return MockResponse()

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = GetContextManager)
    return mock

@pytest.fixture
def mock_aiohttp_financials_failed():

    class MockResponse:
        
        async def json(self):
            return {"status": "Not ok"}

    class GetContextManager(MockContextManager):

        async def __aenter__(self, *args, **kwargs):
            return MockResponse()

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = GetContextManager)
    return mock

@pytest.fixture
def mock_aiohttp_get_price_today():

    class MockResponse:

        async def json(self):
            with open("tests/fixtures/data/sample_price_today_response.json") as f:
                return json.load(f)

    class GetContextManager(MockContextManager):
        async def __aenter__(self, *args, **kwargs):
            return MockResponse()

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = GetContextManager)
    return mock

@pytest.fixture
def mock_aiohttp_get_price_past():
    
    class MockResponse:

        async def json(self):
            with open("tests/fixtures/data/sample_price_past_response.json") as f:
                return json.load(f)

    class GetContextManager(MockContextManager):
        async def __aenter__(self, *args, **kwargs):
            return MockResponse()
    
    mock = AsyncMock()
    mock.get = MagicMock(side_effect = GetContextManager)
    return mock

@pytest.fixture
def mock_aiohttp_get_price_value_error():

    class MockResponse:

        async def json(self):
            with open("tests/fixtures/data/sample_price_not_found.json") as f:
                return json.load(f)

    class GetContextManager(MockContextManager):
        async def __aenter__(self, *args, **kwargs):
            return MockResponse()

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = GetContextManager)
    return mock