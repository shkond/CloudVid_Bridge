"""Unit tests for check_and_scale_worker task."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.check_and_scale_worker import check_queue_has_jobs, check_quota_available


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


class TestCheckQuotaAvailable:
    """Tests for check_quota_available function."""

    def test_quota_available(self) -> None:
        """Test when quota is available for video upload."""
        mock_tracker = MagicMock()
        mock_tracker.can_perform.return_value = True
        mock_tracker.get_remaining_quota.return_value = 8400

        with patch(
            "app.tasks.check_and_scale_worker.get_quota_tracker",
            return_value=mock_tracker
        ):
            result = check_quota_available()

            assert result is True
            mock_tracker.can_perform.assert_called_once_with("videos.insert")
            mock_tracker.get_remaining_quota.assert_called_once()

    def test_quota_exhausted(self) -> None:
        """Test when quota is exhausted."""
        mock_tracker = MagicMock()
        mock_tracker.can_perform.return_value = False
        mock_tracker.get_usage_summary.return_value = {
            "total_used": 9800,
            "daily_limit": 10000,
            "usage_percentage": 98.0,
        }

        with patch(
            "app.tasks.check_and_scale_worker.get_quota_tracker",
            return_value=mock_tracker
        ):
            result = check_quota_available()

            assert result is False
            mock_tracker.can_perform.assert_called_once_with("videos.insert")
            mock_tracker.get_usage_summary.assert_called_once()

