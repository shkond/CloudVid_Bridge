"""Integration tests for cancel job functionality.

Tests the cancel_job endpoint with actual database operations
to reproduce the "Internal Server Error" issue when cancelling
downloading jobs.
"""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models import QueueJobModel
from app.queue.schemas import JobStatus


@pytest.fixture
async def authenticated_client(test_session: AsyncSession):
    """Create an authenticated async client with database session."""
    from app.core.dependencies import get_queue_repository, get_user_id_from_session
    from app.queue.repositories import QueueRepository

    async def override_queue_repo():
        return QueueRepository(test_session)

    async def override_user_id():
        return "test_user_123"

    app.dependency_overrides[get_queue_repository] = override_queue_repo
    app.dependency_overrides[get_user_id_from_session] = override_user_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def pending_job(test_session: AsyncSession) -> QueueJobModel:
    """Create a pending job in the database."""
    import json
    metadata = {"title": "Test Video", "description": "Test", "privacy_status": "private"}
    job = QueueJobModel(
        id=str(uuid4()),
        drive_file_id="test_file_id",
        drive_file_name="test_video.mp4",
        metadata_json=json.dumps(metadata),
        status=JobStatus.PENDING.value,
        progress=0.0,
        message="Queued for upload",
        user_id="test_user_123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)
    return job


@pytest.fixture
async def downloading_job(test_session: AsyncSession) -> QueueJobModel:
    """Create a downloading job in the database."""
    import json
    metadata = {"title": "Downloading Video", "description": "Test", "privacy_status": "private"}
    job = QueueJobModel(
        id=str(uuid4()),
        drive_file_id="test_file_download",
        drive_file_name="downloading_video.mp4",
        metadata_json=json.dumps(metadata),
        status=JobStatus.DOWNLOADING.value,
        progress=25.0,
        message="Starting download from Google Drive...",
        user_id="test_user_123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)
    return job


@pytest.fixture
async def uploading_job(test_session: AsyncSession) -> QueueJobModel:
    """Create an uploading job in the database."""
    import json
    metadata = {"title": "Uploading Video", "description": "Test", "privacy_status": "private"}
    job = QueueJobModel(
        id=str(uuid4()),
        drive_file_id="test_file_upload",
        drive_file_name="uploading_video.mp4",
        metadata_json=json.dumps(metadata),
        status=JobStatus.UPLOADING.value,
        progress=50.0,
        message="Uploading to YouTube...",
        user_id="test_user_123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)
    return job


@pytest.mark.integration
class TestCancelJobIntegration:
    """Integration tests for cancel job endpoint with real database."""

    @pytest.mark.asyncio
    async def test_cancel_pending_job_success(
        self, authenticated_client: AsyncClient, pending_job: QueueJobModel
    ):
        """Test cancelling a pending job with real database."""
        response = await authenticated_client.post(
            f"/queue/jobs/{pending_job.id}/cancel"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job"]["status"] == "cancelled"
        assert data["job"]["id"] == pending_job.id
        assert data["message"] == "Job cancelled"

    @pytest.mark.asyncio
    async def test_cancel_downloading_job_success(
        self, authenticated_client: AsyncClient, downloading_job: QueueJobModel
    ):
        """Test cancelling a downloading job with real database.
        
        This test targets the scenario where user clicks cancel on
        a job showing "ダウンロード中: Starting download from Google Drive...".
        """
        response = await authenticated_client.post(
            f"/queue/jobs/{downloading_job.id}/cancel"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job"]["status"] == "cancelled"
        assert data["job"]["id"] == downloading_job.id
        assert data["message"] == "Job cancelled"

    @pytest.mark.asyncio
    async def test_cancel_uploading_job_fails(
        self, authenticated_client: AsyncClient, uploading_job: QueueJobModel
    ):
        """Test that uploading jobs cannot be cancelled."""
        response = await authenticated_client.post(
            f"/queue/jobs/{uploading_job.id}/cancel"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Job cannot be cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, authenticated_client: AsyncClient):
        """Test cancelling a job that doesn't exist."""
        fake_id = str(uuid4())
        response = await authenticated_client.post(f"/queue/jobs/{fake_id}/cancel")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Job not found"

    @pytest.mark.asyncio
    async def test_cancel_other_user_job(
        self, authenticated_client: AsyncClient, test_session: AsyncSession
    ):
        """Test that users cannot cancel other users' jobs."""
        import json
        # Create a job belonging to different user
        metadata = {"title": "Other Video", "description": "Test", "privacy_status": "private"}
        other_user_job = QueueJobModel(
            id=str(uuid4()),
            drive_file_id="other_user_file",
            drive_file_name="other_video.mp4",
            metadata_json=json.dumps(metadata),
            status=JobStatus.PENDING.value,
            progress=0.0,
            message="Queued",
            user_id="other_user",  # Different user
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        test_session.add(other_user_job)
        await test_session.commit()
        await test_session.refresh(other_user_job)

        response = await authenticated_client.post(
            f"/queue/jobs/{other_user_job.id}/cancel"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["detail"] == "Access denied"

