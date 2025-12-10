"""YouTube Data API repository layer.

Provides low-level API access abstraction for YouTube operations.
This layer handles direct API calls while the Service layer handles business logic.
"""

import io
import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from app.config import get_settings
from app.core.protocols import YouTubeRepositoryProtocol
from app.youtube.schemas import UploadResult, VideoMetadata

logger = logging.getLogger(__name__)


class YouTubeRepository(YouTubeRepositoryProtocol):
    """Repository for YouTube Data API operations.

    Implements YouTubeRepositoryProtocol to provide a clean abstraction
    over the YouTube API. Handles API calls only, no business logic.
    """

    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    def __init__(self, credentials: Credentials) -> None:
        """Initialize YouTube repository with credentials.

        Args:
            credentials: Google OAuth credentials
        """
        self._credentials = credentials
        self._service = build(
            self.YOUTUBE_API_SERVICE_NAME,
            self.YOUTUBE_API_VERSION,
            credentials=credentials,
        )
        self._settings = get_settings()
        self._uploads_playlist_cache: str | None = None

    @property
    def service(self):
        """Get the underlying API service."""
        return self._service

    @property
    def settings(self):
        """Get application settings."""
        return self._settings

    async def upload_video(
        self,
        file_stream: io.BytesIO,
        metadata: VideoMetadata,
        file_size: int,
        mime_type: str = "video/mp4",
    ) -> UploadResult:
        """Upload a video to YouTube.

        Args:
            file_stream: BytesIO stream containing video data
            metadata: Video metadata
            file_size: Size of the video file in bytes
            mime_type: Video MIME type

        Returns:
            UploadResult with video ID and URL
        """
        import asyncio

        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": metadata.category_id,
            },
            "status": {
                "privacyStatus": metadata.privacy_status.value,
                "selfDeclaredMadeForKids": metadata.made_for_kids,
            },
        }

        media = MediaIoBaseUpload(
            file_stream,
            mimetype=mime_type,
            chunksize=self._settings.upload_chunk_size,
            resumable=True,
        )

        try:
            request = self._service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
                notifySubscribers=metadata.notify_subscribers,
            )

            response = None
            while response is None:
                _, response = await asyncio.get_event_loop().run_in_executor(
                    None, request.next_chunk
                )

            video_id = response.get("id")
            return UploadResult(
                success=True,
                video_id=video_id,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                message="Upload completed successfully",
            )

        except HttpError as e:
            logger.exception("YouTube upload failed")
            return UploadResult(
                success=False,
                message="Upload failed",
                error=str(e),
            )

    async def upload_from_file(
        self,
        file_path: str,
        metadata: VideoMetadata,
        file_size: int,
        mime_type: str = "video/mp4",
    ) -> UploadResult:
        """Upload a video file to YouTube.

        Args:
            file_path: Path to the video file on disk
            metadata: Video metadata
            file_size: Size of the video file in bytes
            mime_type: Video MIME type

        Returns:
            UploadResult with video ID and URL
        """
        import asyncio

        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": metadata.category_id,
            },
            "status": {
                "privacyStatus": metadata.privacy_status.value,
                "selfDeclaredMadeForKids": metadata.made_for_kids,
            },
        }

        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            chunksize=self._settings.upload_chunk_size,
            resumable=True,
        )

        try:
            request = self._service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
                notifySubscribers=metadata.notify_subscribers,
            )

            response = None
            while response is None:
                _, response = await asyncio.get_event_loop().run_in_executor(
                    None, request.next_chunk
                )

            video_id = response.get("id")
            return UploadResult(
                success=True,
                video_id=video_id,
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                message="Upload completed successfully",
            )

        except HttpError as e:
            logger.exception("YouTube upload failed")
            return UploadResult(
                success=False,
                message="Upload failed",
                error=str(e),
            )

    async def get_channel_info(self) -> dict[str, Any]:
        """Get authenticated user's YouTube channel information.

        Returns:
            Channel information dict
        """
        import asyncio

        def _get_channel():
            return (
                self._service.channels()
                .list(part="snippet,statistics", mine=True)
                .execute()
            )

        response = await asyncio.get_event_loop().run_in_executor(None, _get_channel)
        items = response.get("items", [])
        return items[0] if items else {}

    async def list_videos(self, max_results: int = 25) -> list[dict[str, Any]]:
        """List videos using playlistItems API (optimized version).

        Args:
            max_results: Maximum number of videos to return

        Returns:
            List of video information dicts
        """
        import asyncio

        playlist_id = await self._get_uploads_playlist_id()
        if not playlist_id:
            return []

        def _list_videos():
            return (
                self._service.playlistItems()
                .list(
                    part="snippet,contentDetails",
                    playlistId=playlist_id,
                    maxResults=max_results,
                )
                .execute()
            )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, _list_videos
            )
            return response.get("items", [])
        except HttpError as e:
            logger.warning("Failed to list playlist items: %s", e)
            return []

    async def check_video_exists(self, video_id: str) -> bool:
        """Check if a video exists on YouTube.

        Args:
            video_id: YouTube video ID to check

        Returns:
            True if video exists, False otherwise
        """
        import asyncio

        def _check():
            return (
                self._service.videos()
                .list(
                    part="id",
                    id=video_id,
                )
                .execute()
            )

        try:
            response = await asyncio.get_event_loop().run_in_executor(None, _check)
            return len(response.get("items", [])) > 0
        except HttpError as e:
            logger.warning("Failed to check video %s: %s", video_id, e)
            return False

    async def get_videos_batch(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Get information for multiple videos in a single request.

        Args:
            video_ids: List of YouTube video IDs (max 50)

        Returns:
            List of video information dicts
        """
        import asyncio

        if not video_ids:
            return []

        batch_ids = video_ids[:50]

        def _get_batch():
            return (
                self._service.videos()
                .list(
                    part="snippet,contentDetails,status",
                    id=",".join(batch_ids),
                )
                .execute()
            )

        try:
            response = await asyncio.get_event_loop().run_in_executor(None, _get_batch)
            return response.get("items", [])
        except HttpError as e:
            logger.warning("Failed to get videos batch: %s", e)
            return []

    async def _get_uploads_playlist_id(self) -> str | None:
        """Get the uploads playlist ID for the authenticated channel.

        Returns:
            Uploads playlist ID or None if not found
        """
        import asyncio

        if self._uploads_playlist_cache is not None:
            return self._uploads_playlist_cache

        def _get_playlist():
            return (
                self._service.channels()
                .list(
                    part="contentDetails",
                    mine=True,
                )
                .execute()
            )

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, _get_playlist
            )
            items = response.get("items", [])
            if not items:
                return None

            playlist_id = (
                items[0]
                .get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )
            self._uploads_playlist_cache = playlist_id
            return playlist_id
        except HttpError as e:
            logger.warning("Failed to get uploads playlist: %s", e)
            return None
