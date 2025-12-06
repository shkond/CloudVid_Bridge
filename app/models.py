"""Database models for AutoUploader."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UploadHistory(Base):
    """Record of uploaded videos for duplicate detection."""

    __tablename__ = "upload_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    drive_file_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drive_file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    drive_md5_checksum: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    youtube_video_id: Mapped[str] = mapped_column(String(50), nullable=False)
    youtube_video_url: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_path: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed"
    )  # completed, failed
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<UploadHistory(id={self.id}, "
            f"file={self.drive_file_name}, "
            f"youtube={self.youtube_video_id})>"
        )
