"""Queue service layer for business logic.

Provides high-level operations for queue management, using the Repository layer
for database access and implementing business logic like duplicate detection.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.protocols import QueueRepositoryProtocol
from app.queue.repositories import QueueRepository
from app.queue.schemas import JobStatus, QueueJob, QueueJobCreate, QueueStatus

logger = logging.getLogger(__name__)


class QueueService:
    """Service for queue management business logic.

    Uses QueueRepository for database access and implements business logic
    like duplicate detection, batch management, and status updates.
    """

    def __init__(
        self,
        repository: QueueRepositoryProtocol | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        """Initialize Queue service.

        Args:
            repository: Optional repository for testing/DI. If not provided,
                        db must be provided to create a default repository.
            db: Database session (used if repository not provided)

        Raises:
            ValueError: If neither repository nor db are provided
        """
        if repository is not None:
            self._repository = repository
        elif db is not None:
            self._repository = QueueRepository(db)
        else:
            raise ValueError("Either repository or db must be provided")

    @property
    def repository(self) -> QueueRepositoryProtocol:
        """Get the underlying repository."""
        return self._repository

    async def add_job(
        self,
        job_create: QueueJobCreate,
        user_id: str,
        check_duplicates: bool = True,
    ) -> tuple[QueueJob | None, str | None]:
        """Add a new job to the queue with optional duplicate detection.

        Args:
            job_create: Job creation request
            user_id: User ID who created this job
            check_duplicates: Whether to check for duplicates

        Returns:
            Tuple of (created job or None, error message or None)
        """
        if check_duplicates:
            # Check by file ID
            if await self._repository.is_file_id_in_queue(job_create.drive_file_id):
                return None, "File is already in the queue"

            # Check by MD5
            if job_create.drive_md5_checksum:
                if await self._repository.is_md5_in_queue(
                    job_create.drive_md5_checksum
                ):
                    return None, "A file with the same content is already in the queue"

        job = await self._repository.add_job(job_create, user_id)
        return job, None

    async def get_job(self, job_id: UUID) -> QueueJob | None:
        """Get a job by ID.

        Args:
            job_id: Job UUID

        Returns:
            QueueJob or None if not found
        """
        return await self._repository.get_job(job_id)

    async def update_job(
        self,
        job_id: UUID,
        status: JobStatus | None = None,
        progress: float | None = None,
        message: str | None = None,
        video_id: str | None = None,
        video_url: str | None = None,
        error: str | None = None,
    ) -> QueueJob | None:
        """Update a job's status and progress.

        Args:
            job_id: Job UUID
            status: New status (optional)
            progress: New progress (optional)
            message: Status message (optional)
            video_id: YouTube video ID (optional)
            video_url: YouTube video URL (optional)
            error: Error message (optional)

        Returns:
            Updated QueueJob or None if not found
        """
        return await self._repository.update_job(
            job_id, status, progress, message, video_id, video_url, error
        )

    async def cancel_job(self, job_id: UUID) -> QueueJob | None:
        """Cancel a pending or downloading job.

        Args:
            job_id: Job UUID

        Returns:
            Cancelled QueueJob or None if not found or not cancellable
        """
        return await self._repository.cancel_job(job_id)

    async def delete_job(self, job_id: UUID) -> bool:
        """Delete a job from the queue.

        Args:
            job_id: Job UUID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete_job(job_id)

    async def get_all_jobs(self) -> list[QueueJob]:
        """Get all jobs in the queue.

        Returns:
            List of all QueueJobs
        """
        return await self._repository.get_all_jobs()

    async def get_jobs_by_user(self, user_id: str) -> list[QueueJob]:
        """Get all jobs for a specific user.

        Args:
            user_id: User identifier

        Returns:
            List of QueueJobs belonging to the user
        """
        return await self._repository.get_jobs_by_user(user_id)

    async def get_pending_jobs(self) -> list[QueueJob]:
        """Get all pending jobs.

        Returns:
            List of pending QueueJobs
        """
        return await self._repository.get_pending_jobs()

    async def get_next_pending_job(self) -> QueueJob | None:
        """Get the next pending job in queue order (FIFO).

        Returns:
            Next pending QueueJob or None
        """
        return await self._repository.get_next_pending_job()

    async def get_active_jobs(self) -> list[QueueJob]:
        """Get all active (downloading/uploading) jobs.

        Returns:
            List of active QueueJobs
        """
        return await self._repository.get_active_jobs()

    async def get_status(self, user_id: str | None = None) -> QueueStatus:
        """Get overall queue status, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            QueueStatus summary
        """
        return await self._repository.get_status(user_id)

    async def clear_completed(self, user_id: str | None = None) -> int:
        """Clear all completed jobs from the queue.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Number of jobs cleared
        """
        return await self._repository.clear_completed(user_id)

    async def is_file_id_in_queue(self, drive_file_id: str) -> bool:
        """Check if a file ID is already in the queue.

        Args:
            drive_file_id: Google Drive file ID

        Returns:
            True if file is already in queue
        """
        return await self._repository.is_file_id_in_queue(drive_file_id)

    async def is_md5_in_queue(self, md5_checksum: str) -> bool:
        """Check if a file with given MD5 is already in the queue.

        Args:
            md5_checksum: MD5 checksum of the file

        Returns:
            True if file with same MD5 is in queue
        """
        return await self._repository.is_md5_in_queue(md5_checksum)

    async def get_jobs_for_batch(self, batch_id: str) -> list[QueueJob]:
        """Get all jobs for a specific batch.

        Args:
            batch_id: Batch identifier

        Returns:
            List of QueueJobs in the batch
        """
        return await self._repository.get_jobs_for_batch(batch_id)

    async def mark_job_started(self, job_id: UUID) -> QueueJob | None:
        """Mark a job as started (downloading).

        Args:
            job_id: Job UUID

        Returns:
            Updated QueueJob or None if not found
        """
        return await self._repository.update_job(
            job_id,
            status=JobStatus.DOWNLOADING,
            progress=0.0,
            message="Starting download...",
        )

    async def mark_job_uploading(
        self, job_id: UUID, progress: float = 0.0
    ) -> QueueJob | None:
        """Mark a job as uploading.

        Args:
            job_id: Job UUID
            progress: Current progress (0.0-100.0)

        Returns:
            Updated QueueJob or None if not found
        """
        return await self._repository.update_job(
            job_id,
            status=JobStatus.UPLOADING,
            progress=progress,
            message="Uploading to YouTube...",
        )

    async def mark_job_completed(
        self, job_id: UUID, video_id: str, video_url: str
    ) -> QueueJob | None:
        """Mark a job as completed.

        Args:
            job_id: Job UUID
            video_id: YouTube video ID
            video_url: YouTube video URL

        Returns:
            Updated QueueJob or None if not found
        """
        return await self._repository.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100.0,
            message="Upload complete",
            video_id=video_id,
            video_url=video_url,
        )

    async def mark_job_failed(self, job_id: UUID, error: str) -> QueueJob | None:
        """Mark a job as failed.

        Args:
            job_id: Job UUID
            error: Error message

        Returns:
            Updated QueueJob or None if not found
        """
        return await self._repository.update_job(
            job_id,
            status=JobStatus.FAILED,
            message="Upload failed",
            error=error,
        )

    async def retry_job(self, job_id: UUID) -> tuple[QueueJob | None, str | None]:
        """Retry a failed job if under max retries.

        Args:
            job_id: Job UUID

        Returns:
            Tuple of (updated job or None, error message or None)
        """
        job = await self._repository.get_job(job_id)
        if not job:
            return None, "Job not found"

        if job.status != JobStatus.FAILED:
            return None, "Job is not in failed status"

        if job.retry_count >= job.max_retries:
            return None, "Maximum retries exceeded"

        # Increment retry count
        await self._repository.increment_retry_count(job_id)

        # Reset to pending
        updated_job = await self._repository.update_job(
            job_id,
            status=JobStatus.PENDING,
            progress=0.0,
            message="Queued for retry",
            error=None,
        )

        return updated_job, None
