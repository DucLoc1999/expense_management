import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.gemini import ask_advisor


class _FakeResponse:
    def __init__(self, json_payload=None, status=200):
        self._json = json_payload
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


@pytest.mark.asyncio
class TestAskAdvisor:
    @patch("services.gemini.httpx.AsyncClient")
    async def test_returns_answer(self, mock_client_cls):
        resp = _FakeResponse(
            {"candidates": [{"content": {"parts": [{"text": "Here is advice."}]}}]}
        )
        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = client

        answer, error = await ask_advisor("data...", [], "How can I save?")

        assert error is None
        assert answer == "Here is advice."
        call_kwargs = client.post.await_args.kwargs
        prompt = call_kwargs["json"]["contents"][0]["parts"][0]["text"]
        assert "data..." in prompt
        assert "How can I save?" in prompt

    @patch("services.gemini.httpx.AsyncClient")
    async def test_includes_memory(self, mock_client_cls):
        resp = _FakeResponse(
            {"candidates": [{"content": {"parts": [{"text": "OK."}]}}]}
        )
        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = client

        answer, error = await ask_advisor("data...", ["User: hi", "Assistant: hello"], "q")

        assert answer == "OK."
        call_kwargs = client.post.await_args.kwargs
        prompt = call_kwargs["json"]["contents"][0]["parts"][0]["text"]
        assert "User: hi" in prompt

    @patch("services.gemini.httpx.AsyncClient")
    async def test_handles_timeout(self, mock_client_cls):
        client = MagicMock()
        client.post = AsyncMock(side_effect=__import__("httpx").TimeoutException("boom"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = client

        answer, error = await ask_advisor("data...", [], "q")

        assert answer is None
        assert error is not None

    @patch("services.gemini.httpx.AsyncClient")
    async def test_handles_transport_error(self, mock_client_cls):
        client = MagicMock()
        client.post = AsyncMock(side_effect=__import__("httpx").ConnectError("boom"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = client

        answer, error = await ask_advisor("data...", [], "q")

        assert answer is None
        assert error is not None

    @patch("services.gemini.httpx.AsyncClient")
    async def test_handles_empty_response(self, mock_client_cls):
        resp = _FakeResponse({"candidates": []})
        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = client

        answer, error = await ask_advisor("data...", [], "q")

        assert answer is None
        assert error is not None
