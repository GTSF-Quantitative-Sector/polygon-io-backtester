import pytest
from asyncmock import AsyncMock, MagicMock
import json

@pytest.fixture
def mock_aiohttp_financials_success():

    class MockResponse:

        def __init__(self) -> None:
            pass
        
        async def json(self):
            with open('tests/fixtures/sample_financials_response.json') as f:
                return json.load(f)        

    class MockContextManager:

        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self, *args, **kwargs) -> MockResponse:
            print("here")
            return MockResponse()

        async def __aexit__(self, *args, **kwargs):
            return

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = MockContextManager)
    return mock

@pytest.fixture
def mock_aiohttp_financials_timeout():

    class MockResponse:

        def __init__(self) -> None:
            pass
        
        async def json(self):
            raise TimeoutError()

    class MockContextManager:

        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self, *args, **kwargs) -> MockResponse:
            print("here")
            return MockResponse()

        async def __aexit__(self, *args, **kwargs):
            return

    mock = AsyncMock()
    mock.get = MagicMock(side_effect = MockContextManager)
    return mock