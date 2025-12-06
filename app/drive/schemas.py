"""Pydantic schemas for Google Drive."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FileType(str, Enum):
    """File type enum."""

    VIDEO = "video"
    FOLDER = "folder"
    OTHER = "other"


class DriveFile(BaseModel):
    """Google Drive file information."""

    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    size: int | None = None
    created_time: datetime | None = Field(None, alias="createdTime")
    modified_time: datetime | None = Field(None, alias="modifiedTime")
    file_type: FileType = FileType.OTHER
    parent_id: str | None = None
    thumbnail_link: str | None = Field(None, alias="thumbnailLink")
    web_view_link: str | None = Field(None, alias="webViewLink")

    model_config = {"populate_by_name": True}


class DriveFolder(BaseModel):
    """Google Drive folder information."""

    id: str
    name: str
    files: list[DriveFile] = Field(default_factory=list)
    subfolders: list["DriveFolder"] = Field(default_factory=list)
    total_videos: int = 0


class FolderScanRequest(BaseModel):
    """Request to scan a Drive folder."""

    folder_id: str = Field(..., description="Google Drive folder ID")
    recursive: bool = Field(
        default=False, description="Whether to scan subfolders recursively"
    )
    video_only: bool = Field(
        default=True, description="Filter to show only video files"
    )


class FolderScanResponse(BaseModel):
    """Response from folder scan."""

    folder: DriveFolder
    message: str = "Scan completed"


class FolderUploadSettings(BaseModel):
    """Default settings for video uploads from a folder."""

    title_template: str = Field(
        default="{filename}",
        description=(
            "Template for video title. "
            "Placeholders: {filename}, {folder}, {folder_path}, {upload_date}"
        ),
    )
    description_template: str = Field(
        default="",
        description=(
            "Template for video description. "
            "Placeholders: {filename}, {folder}, {folder_path}, {upload_date}"
        ),
    )
    include_md5_hash: bool = Field(
        default=True, description="Include MD5 hash in description for duplicate detection"
    )
    default_privacy: str = Field(
        default="private", description="Default privacy status (public, private, unlisted)"
    )
    default_category_id: str = Field(
        default="24", description="YouTube category ID (24=Entertainment)"
    )
    default_tags: list[str] = Field(
        default_factory=list, description="Default tags for videos"
    )
    made_for_kids: bool = Field(
        default=False, description="Whether videos are made for kids"
    )


class FolderUploadRequest(BaseModel):
    """Request to upload all videos from a Drive folder."""

    folder_id: str = Field(..., description="Google Drive folder ID")
    recursive: bool = Field(
        default=False, description="Whether to include subfolders"
    )
    max_files: int = Field(
        default=100, ge=1, le=500, description="Maximum number of files to upload"
    )
    skip_duplicates: bool = Field(
        default=True, description="Skip files already uploaded (based on MD5 hash)"
    )
    settings: FolderUploadSettings = Field(
        default_factory=FolderUploadSettings,
        description="Upload settings for videos",
    )


class SkippedFile(BaseModel):
    """Information about a skipped file."""

    file_id: str
    file_name: str
    reason: str  # "duplicate", "already_in_queue", etc.


class FolderUploadResponse(BaseModel):
    """Response from folder upload request."""

    folder_name: str
    batch_id: str
    added_count: int
    skipped_count: int = 0
    skipped_files: list[SkippedFile] = Field(default_factory=list)
    message: str = ""


# Update forward references
DriveFolder.model_rebuild()

