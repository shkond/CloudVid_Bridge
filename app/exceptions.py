"""Custom exceptions for CloudVid Bridge.

This module defines application-specific exceptions for better error handling
and clearer error messages throughout the application.
"""


class CloudVidBridgeError(Exception):
    """Base exception for all CloudVid Bridge errors.

    All custom exceptions in this application should inherit from this class
    to allow catching all application-specific errors with a single except clause.
    """
    pass


class QuotaExceededError(CloudVidBridgeError):
    """Raised when YouTube API quota is exceeded.

    This exception is raised when an operation cannot be performed due to
    insufficient YouTube API quota remaining for the day.

    Attributes:
        remaining: The remaining quota units available
        required: The quota units required for the operation
    """
    def __init__(self, remaining: int, required: int):
        self.remaining = remaining
        self.required = required
        super().__init__(
            f"Insufficient quota: remaining={remaining}, required={required}"
        )


class AuthenticationError(CloudVidBridgeError):
    """Raised when authentication fails.

    This exception is raised when a user is not authenticated or when
    authentication credentials are invalid or expired.
    """
    pass


class GoogleAuthenticationError(AuthenticationError):
    """Raised when Google OAuth authentication fails.

    This is a more specific authentication error for Google-related
    authentication issues.
    """
    pass


class UploadError(CloudVidBridgeError):
    """Raised when a video upload fails.

    This exception is raised when an upload operation fails for any reason
    other than quota issues.

    Attributes:
        file_id: The Google Drive file ID that failed to upload
        message: Detailed error message
    """
    def __init__(self, file_id: str, message: str):
        self.file_id = file_id
        self.message = message
        super().__init__(f"Upload failed for file {file_id}: {message}")


class DriveAccessError(CloudVidBridgeError):
    """Raised when Google Drive access fails.

    This exception is raised when accessing a file or folder in Google Drive
    fails due to permissions, file not found, or other Drive-related issues.
    """
    pass


class QueueError(CloudVidBridgeError):
    """Raised when queue operations fail.

    This exception is raised for queue-related errors such as job not found,
    invalid job state transitions, or database errors during queue operations.
    """
    pass


class FileSizeExceededError(CloudVidBridgeError):
    """Raised when a file exceeds the maximum allowed size.

    This exception is raised when attempting to upload a file that exceeds
    the configured maximum file size limit.

    Attributes:
        file_size: The size of the file in bytes
        max_size: The maximum allowed size in bytes
        file_name: Optional name of the file
    """
    def __init__(self, file_size: int, max_size: int, file_name: str = ""):
        self.file_size = file_size
        self.max_size = max_size
        self.file_name = file_name
        size_gb = file_size / (1024 ** 3)
        max_gb = max_size / (1024 ** 3)
        super().__init__(
            f"File size ({size_gb:.2f}GB) exceeds maximum allowed ({max_gb:.1f}GB)"
            + (f": {file_name}" if file_name else "")
        )


class InsufficientDiskSpaceError(CloudVidBridgeError):
    """Raised when there's not enough disk space for temporary file storage.

    This exception is raised when the available disk space is insufficient
    to download and process a file.

    Attributes:
        required: Required disk space in bytes
        available: Available disk space in bytes
    """
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        req_gb = required / (1024 ** 3)
        avail_gb = available / (1024 ** 3)
        super().__init__(
            f"Insufficient disk space: required {req_gb:.2f}GB, available {avail_gb:.2f}GB"
        )
