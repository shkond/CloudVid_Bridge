"""Unit tests for HerokuClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.heroku_client import HerokuClient


class TestHerokuClient:
    """Tests for HerokuClient class."""

    @pytest.fixture
    def client(self) -> HerokuClient:
        """Create test client."""
        return HerokuClient(
            api_key="test-api-key",
            app_name="test-app"
        )

    def test_init(self, client: HerokuClient) -> None:
        """Test client initialization."""
        assert client.api_key == "test-api-key"
        assert client.app_name == "test-app"
        assert "Bearer test-api-key" in client._headers["Authorization"]
        assert "application/vnd.heroku+json" in client._headers["Accept"]

    @pytest.mark.asyncio
    async def test_get_dyno_quantity_success(self, client: HerokuClient) -> None:
        """Test getting dyno quantity successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"quantity": 2}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            quantity = await client.get_dyno_quantity("worker")

            assert quantity == 2
            mock_client.get.assert_called_once()
            call_url = mock_client.get.call_args[0][0]
            assert "worker" in call_url

    @pytest.mark.asyncio
    async def test_get_dyno_quantity_not_found(self, client: HerokuClient) -> None:
        """Test getting dyno quantity when process type doesn't exist."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            quantity = await client.get_dyno_quantity("worker")

            assert quantity == 0

    @pytest.mark.asyncio
    async def test_scale_dyno_success(self, client: HerokuClient) -> None:
        """Test scaling dyno successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.patch = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.scale_dyno("worker", 1)

            assert result is True
            mock_client.patch.assert_called_once()
            call_kwargs = mock_client.patch.call_args[1]
            assert call_kwargs["json"]["updates"][0]["quantity"] == 1

    @pytest.mark.asyncio
    async def test_scale_dyno_to_zero(self, client: HerokuClient) -> None:
        """Test scaling dyno to zero (stopping)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.patch = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.scale_dyno("worker", 0)

            assert result is True
            call_kwargs = mock_client.patch.call_args[1]
            assert call_kwargs["json"]["updates"][0]["quantity"] == 0

    @pytest.mark.asyncio
    async def test_ensure_worker_running_when_stopped(
        self, client: HerokuClient
    ) -> None:
        """Test ensuring worker is running when currently stopped."""
        # First call returns quantity 0, second call scales up
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {"quantity": 0}
        get_response.raise_for_status = MagicMock()

        patch_response = MagicMock()
        patch_response.status_code = 200
        patch_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=get_response)
            mock_client.patch = AsyncMock(return_value=patch_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.ensure_worker_running()

            assert result is True
            mock_client.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_worker_running_already_running(
        self, client: HerokuClient
    ) -> None:
        """Test ensuring worker is running when already running."""
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {"quantity": 1}
        get_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=get_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.ensure_worker_running()

            assert result is True
            # Should not call patch since worker is already running
            mock_client.patch.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_worker(self, client: HerokuClient) -> None:
        """Test stopping worker dyno."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.patch = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await client.stop_worker()

            assert result is True
            call_kwargs = mock_client.patch.call_args[1]
            assert call_kwargs["json"]["updates"][0]["quantity"] == 0
