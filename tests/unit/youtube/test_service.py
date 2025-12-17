"""Unit tests for YouTubeService."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.youtube.service import YouTubeService
from app.youtube.schemas import VideoMetadata


class TestUploadFromDriveAsync:
    """Tests for upload_from_drive_async method."""

    @pytest.mark.asyncio
    async def test_drive_service_initialized_with_credentials_keyword_arg(self):
        """Test that DriveService is initialized correctly with credentials keyword argument.
        
        This test verifies the fix for a bug where DriveService was initialized with
        credentials as a positional argument, causing it to be assigned to the 
        repository parameter instead.
        
        Bug: DriveService(drive_credentials)  # Credentials -> repository
        Fix: DriveService(credentials=drive_credentials)  # Credentials -> credentials
        """
        # Mock credentials
        mock_credentials = Mock()
        mock_drive_credentials = Mock()
        
        # Create service
        youtube_service = YouTubeService(mock_credentials)
        
        # Mock DriveService constructor to verify correct parameter usage
        with patch('app.youtube.service.DriveService') as mock_drive_service_class:
            mock_drive_instance = Mock()
            mock_drive_service_class.return_value = mock_drive_instance
            
            # Mock get_file_metadata to return valid data
            mock_drive_instance.get_file_metadata = AsyncMock(return_value={
                "size": "1000000",
                "mimeType": "video/mp4",
                "name": "test.mp4"
            })
            
            # Mock download_to_file to avoid actual download
            mock_drive_instance.download_to_file = Mock()
            
            try:
                await youtube_service.upload_from_drive_async(
                    drive_file_id="test_id",
                    metadata=VideoMetadata(title="Test"),
                    drive_credentials=mock_drive_credentials
                )
            except Exception:
                pass  # Expected to fail on actual upload, we only care about DriveService init
            
            # Verify DriveService was called with credentials as keyword argument
            mock_drive_service_class.assert_called_once_with(
                credentials=mock_drive_credentials
            )

