"""Unit tests for queue management routes.

Tests for:
- Get queue status endpoint
- List jobs endpoint
- Add job endpoint
- Get job endpoint
- Cancel job endpoint
- Delete job endpoint
- Clear completed endpoint
- Worker control endpoints
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.queue.schemas import JobStatus, QueueJob, QueueStatus
from app.youtube.schemas import VideoMetadata


@pytest.fixture
def mock_queue_repo():
    """Mock queue repository for tests."""
    repo = MagicMock()
    repo.get_status = AsyncMock(return_value=QueueStatus(
        total_jobs=20,
        pending_jobs=5,
        active_jobs=2,
        completed_jobs=10,
        failed_jobs=2,
        is_processing=True,
    ))
    repo.get_jobs_by_user = AsyncMock(return_value=[])
    repo.get_job = AsyncMock(return_value=None)
    repo.add_job = AsyncMock()
    repo.cancel_job = AsyncMock()
    repo.delete_job = AsyncMock()
    repo.clear_completed = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def test_client_with_mocks(mock_queue_repo):
    """Create test client with mocked dependencies."""
    from app.core.dependencies import get_queue_repository, get_user_id_from_session
    from app.main import app

    # Override dependencies
    async def override_queue_repo():
        return mock_queue_repo

    async def override_user_id():
        return "test_user_123"

    app.dependency_overrides[get_queue_repository] = override_queue_repo
    app.dependency_overrides[get_user_id_from_session] = override_user_id

    client = TestClient(app)
    yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def test_client():
    """Create test client for the FastAPI app."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def sample_job_id():
    """Generate a sample job ID."""
    return str(uuid4())


@pytest.fixture
def sample_job():
    """Create a sample QueueJob."""
    return QueueJob(
        id=uuid4(),
        drive_file_id="file123",
        drive_file_name="video.mp4",
        status=JobStatus.PENDING,
        progress=0.0,
        user_id="test_user_123",
        created_at=datetime.now(UTC),
        metadata=VideoMetadata(
            title="Test Video",
            description="Test description",
            privacy_status="private",
        ),
    )


@pytest.mark.unit
class TestQueueStatus:
    """Tests for queue status endpoint."""

    @staticmethod
    def test_get_queue_status_requires_auth(test_client):
        """Test that queue status requires authentication."""
        response = test_client.get("/queue/status")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_get_queue_status_success(mock_queue_repo, test_client_with_mocks):
        """Test getting queue status."""
        response = test_client_with_mocks.get("/queue/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pending_jobs"] == 5
        assert data["completed_jobs"] == 10


@pytest.mark.unit
class TestListJobs:
    """Tests for list jobs endpoint."""

    @staticmethod
    def test_list_jobs_requires_auth(test_client):
        """Test that list jobs requires authentication."""
        response = test_client.get("/queue/jobs")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_list_jobs_success(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test listing user's jobs."""
        mock_queue_repo.get_jobs_by_user = AsyncMock(return_value=[sample_job])

        response = test_client_with_mocks.get("/queue/jobs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1


@pytest.mark.unit
class TestAddJob:
    """Tests for add job endpoint."""

    @staticmethod
    def test_add_job_requires_auth(test_client):
        """Test that add job requires authentication."""
        response = test_client.post(
            "/queue/jobs",
            json={
                "drive_file_id": "file123",
                "drive_file_name": "video.mp4",
                "metadata": {
                    "title": "Test Video",
                    "privacy_status": "private",
                },
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_add_job_success(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test adding job to queue."""
        mock_queue_repo.add_job = AsyncMock(return_value=sample_job)

        response = test_client_with_mocks.post(
            "/queue/jobs",
            json={
                "drive_file_id": "file123",
                "drive_file_name": "video.mp4",
                "metadata": {
                    "title": "Test Video",
                    "description": "Test",
                    "privacy_status": "private",
                },
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "job" in data


@pytest.mark.unit
class TestGetJob:
    """Tests for get job endpoint."""

    @staticmethod
    def test_get_job_requires_auth(test_client, sample_job_id):
        """Test that get job requires authentication."""
        response = test_client.get(f"/queue/jobs/{sample_job_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_get_job_not_found(mock_queue_repo, sample_job_id, test_client_with_mocks):
        """Test getting non-existent job."""
        mock_queue_repo.get_job = AsyncMock(return_value=None)

        response = test_client_with_mocks.get(f"/queue/jobs/{sample_job_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @staticmethod
    def test_get_job_success(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test getting existing job."""
        mock_queue_repo.get_job = AsyncMock(return_value=sample_job)

        response = test_client_with_mocks.get(f"/queue/jobs/{sample_job.id}")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestCancelJob:
    """Tests for cancel job endpoint."""

    @staticmethod
    def test_cancel_job_requires_auth(test_client, sample_job_id):
        """Test that cancel job requires authentication."""
        response = test_client.post(f"/queue/jobs/{sample_job_id}/cancel")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_cancel_job_success(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test cancelling a pending job."""
        mock_queue_repo.get_job = AsyncMock(return_value=sample_job)
        cancelled_job = sample_job.model_copy(update={"status": JobStatus.CANCELLED})
        mock_queue_repo.cancel_job = AsyncMock(return_value=cancelled_job)

        response = test_client_with_mocks.post(f"/queue/jobs/{sample_job.id}/cancel")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job"]["status"] == "cancelled"
        assert data["message"] == "Job cancelled"

    @staticmethod
    def test_cancel_job_downloading_success(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test cancelling a job that is currently downloading."""
        downloading_job = sample_job.model_copy(
            update={"status": JobStatus.DOWNLOADING, "message": "Starting download from Google Drive..."}
        )
        mock_queue_repo.get_job = AsyncMock(return_value=downloading_job)
        cancelled_job = downloading_job.model_copy(
            update={"status": JobStatus.CANCELLED, "message": "Cancelled by user"}
        )
        mock_queue_repo.cancel_job = AsyncMock(return_value=cancelled_job)

        response = test_client_with_mocks.post(f"/queue/jobs/{downloading_job.id}/cancel")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job"]["status"] == "cancelled"

    @staticmethod
    def test_cancel_job_not_found(mock_queue_repo, sample_job_id, test_client_with_mocks):
        """Test cancelling a job that doesn't exist."""
        mock_queue_repo.get_job = AsyncMock(return_value=None)

        response = test_client_with_mocks.post(f"/queue/jobs/{sample_job_id}/cancel")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Job not found"

    @staticmethod
    def test_cancel_job_access_denied(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test cancelling a job that belongs to another user."""
        other_user_job = sample_job.model_copy(update={"user_id": "other_user"})
        mock_queue_repo.get_job = AsyncMock(return_value=other_user_job)

        response = test_client_with_mocks.post(f"/queue/jobs/{other_user_job.id}/cancel")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["detail"] == "Access denied"

    @staticmethod
    def test_cancel_job_uploading_fails(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test that jobs in uploading state cannot be cancelled."""
        uploading_job = sample_job.model_copy(update={"status": JobStatus.UPLOADING})
        mock_queue_repo.get_job = AsyncMock(return_value=uploading_job)
        mock_queue_repo.cancel_job = AsyncMock(return_value=None)  # Repository returns None for non-cancellable

        response = test_client_with_mocks.post(f"/queue/jobs/{uploading_job.id}/cancel")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Job cannot be cancelled"

    @staticmethod
    def test_cancel_job_completed_fails(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test that completed jobs cannot be cancelled."""
        completed_job = sample_job.model_copy(update={"status": JobStatus.COMPLETED})
        mock_queue_repo.get_job = AsyncMock(return_value=completed_job)
        mock_queue_repo.cancel_job = AsyncMock(return_value=None)

        response = test_client_with_mocks.post(f"/queue/jobs/{completed_job.id}/cancel")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Job cannot be cancelled"

    @staticmethod
    def test_cancel_job_failed_fails(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test that failed jobs cannot be cancelled."""
        failed_job = sample_job.model_copy(update={"status": JobStatus.FAILED})
        mock_queue_repo.get_job = AsyncMock(return_value=failed_job)
        mock_queue_repo.cancel_job = AsyncMock(return_value=None)

        response = test_client_with_mocks.post(f"/queue/jobs/{failed_job.id}/cancel")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Job cannot be cancelled"


@pytest.mark.unit
class TestDeleteJob:
    """Tests for delete job endpoint."""

    @staticmethod
    def test_delete_job_requires_auth(test_client, sample_job_id):
        """Test that delete job requires authentication."""
        response = test_client.delete(f"/queue/jobs/{sample_job_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_delete_job_active_fails(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test that active jobs cannot be deleted."""
        active_job = sample_job.model_copy(update={"status": JobStatus.UPLOADING})
        mock_queue_repo.get_job = AsyncMock(return_value=active_job)

        response = test_client_with_mocks.delete(f"/queue/jobs/{active_job.id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @staticmethod
    def test_delete_job_success(mock_queue_repo, sample_job, test_client_with_mocks):
        """Test deleting completed job."""
        completed_job = sample_job.model_copy(update={"status": JobStatus.COMPLETED})
        mock_queue_repo.get_job = AsyncMock(return_value=completed_job)
        mock_queue_repo.delete_job = AsyncMock()

        response = test_client_with_mocks.delete(f"/queue/jobs/{completed_job.id}")

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestClearCompleted:
    """Tests for clear completed endpoint."""

    @staticmethod
    def test_clear_completed_requires_auth(test_client):
        """Test that clear completed requires authentication."""
        response = test_client.post("/queue/clear")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @staticmethod
    def test_clear_completed_success(mock_queue_repo, test_client_with_mocks):
        """Test clearing completed jobs."""
        mock_queue_repo.clear_completed = AsyncMock(return_value=5)

        response = test_client_with_mocks.post("/queue/clear")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["cleared_count"] == 5


