"""YouTube routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from google.oauth2.credentials import Credentials

from app.core.dependencies import get_user_credentials, get_youtube_service
from app.youtube.quota import get_quota_tracker
from app.youtube.schemas import UploadRequest, UploadResult, YouTubeVideo
from app.youtube.service import YouTubeService

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/channel")
async def get_channel_info(
    service: YouTubeService = Depends(get_youtube_service),
) -> dict:
    """Get authenticated user's YouTube channel information.

    Args:
        service: YouTubeService (injected via DI)

    Returns:
        Channel information
    """
    try:
        return service.get_channel_info()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channel info: {e!s}",
        ) from e


@router.get("/videos", response_model=list[YouTubeVideo])
async def list_my_videos(
    max_results: int = Query(
        default=25, ge=1, le=50, description="Max videos to return"
    ),
    service: YouTubeService = Depends(get_youtube_service),
) -> list[YouTubeVideo]:
    """List videos uploaded by the authenticated user.

    Args:
        max_results: Maximum number of videos to return
        service: YouTubeService (injected via DI)

    Returns:
        List of YouTube videos
    """
    try:
        items = service.list_my_videos(max_results)
        videos = []
        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = thumbnails.get("default", {}).get("url")

            videos.append(
                YouTubeVideo(
                    id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description"),
                    thumbnail_url=thumbnail_url,
                    channel_id=snippet.get("channelId"),
                    published_at=snippet.get("publishedAt"),
                )
            )
        return videos
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list videos: {e!s}",
        ) from e


@router.post("/upload", response_model=UploadResult)
async def upload_video(
    request: UploadRequest,
    service: YouTubeService = Depends(get_youtube_service),
    credentials: Credentials = Depends(get_user_credentials),
) -> UploadResult:
    """Upload a video from Google Drive to YouTube.

    This is a synchronous upload endpoint. For large files or
    multiple uploads, use the queue system instead.

    Args:
        request: Upload request with Drive file ID and metadata
        service: YouTubeService (injected via DI)
        credentials: User credentials for Drive API

    Returns:
        Upload result with video ID and URL
    """
    try:
        result = await service.upload_from_drive_async(
            drive_file_id=request.drive_file_id,
            metadata=request.metadata,
            drive_credentials=credentials,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {e!s}",
        ) from e


@router.get("/quota")
async def get_quota_status() -> dict:
    """Get current YouTube API quota usage status.

    Returns:
        Quota usage summary including daily usage, remaining quota,
        and breakdown by API operation.
    """
    tracker = get_quota_tracker()
    return tracker.get_usage_summary()


@router.get("/video/{video_id}/exists")
async def check_video_exists(
    video_id: str,
    service: YouTubeService = Depends(get_youtube_service),
) -> dict:
    """Check if a video exists on YouTube.

    This is useful for verifying that previously uploaded videos still exist.
    Costs only 1 quota unit.

    Args:
        video_id: YouTube video ID to check
        service: YouTubeService (injected via DI)

    Returns:
        Dict with exists boolean and video_id
    """
    try:
        exists = service.check_video_exists_on_youtube(video_id)
        return {"video_id": video_id, "exists": exists}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check video: {e!s}",
        ) from e

