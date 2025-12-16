"""Unit tests for check_and_scale_worker task."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.check_and_scale_worker import check_queue_has_jobs


class TestCheckQueueHasJobs:
    """Tests for check_queue_has_jobs function."""

    @pytest.mark.asyncio
    async def test_has_pending_jobs(self) -> None:
        """Test detection of pending jobs in queue."""
        mock_job = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pending_jobs = AsyncMock(return_value=[mock_job])
        mock_repo.get_active_jobs = AsyncMock(return_value=[])

        with patch(
            "app.tasks.check_and_scale_worker.get_db_context"
        ) as mock_db_context:
            mock_db = AsyncMock()
            mock_db_context.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db_context.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "app.tasks.check_and_scale_worker.QueueRepository",
                return_value=mock_repo
            ):
                result = await check_queue_has_jobs()

                assert result is True
                mock_repo.get_pending_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_active_jobs(self) -> None:
        """Test detection of active jobs in queue."""
        mock_job = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pending_jobs = AsyncMock(return_value=[])
        mock_repo.get_active_jobs = AsyncMock(return_value=[mock_job])

        with patch(
            "app.tasks.check_and_scale_worker.get_db_context"
        ) as mock_db_context:
            mock_db = AsyncMock()
            mock_db_context.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db_context.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "app.tasks.check_and_scale_worker.QueueRepository",
                return_value=mock_repo
            ):
                result = await check_queue_has_jobs()

                assert result is True
                mock_repo.get_active_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_jobs(self) -> None:
        """Test when queue is empty."""
        mock_repo = MagicMock()
        mock_repo.get_pending_jobs = AsyncMock(return_value=[])
        mock_repo.get_active_jobs = AsyncMock(return_value=[])

        with patch(
            "app.tasks.check_and_scale_worker.get_db_context"
        ) as mock_db_context:
            mock_db = AsyncMock()
            mock_db_context.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db_context.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch(
                "app.tasks.check_and_scale_worker.QueueRepository",
                return_value=mock_repo
            ):
                result = await check_queue_has_jobs()

                assert result is False
