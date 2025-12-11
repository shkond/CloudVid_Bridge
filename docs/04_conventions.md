# Coding Conventions

## General Guidelines

This document describes coding patterns and conventions used throughout the codebase.

---

## Async/Await Patterns

### Route Handlers

All route handlers are `async def`:

```python
@router.get("/files")
async def list_files(
    folder_id: str = "root",
    drive_service: DriveService = Depends(get_drive_service),
) -> list[DriveFile]:
    return await drive_service.list_files(folder_id)
```

### Service Methods

Services use async methods with `anyio` for blocking operations:

```python
import anyio

class DriveService:
    async def list_files(self, folder_id: str = "root") -> list[DriveFile]:
        # Wrap blocking Google API call
        def _list_files() -> list[dict]:
            return self.service.files().list(...).execute()
        
        result = await anyio.to_thread.run_sync(_list_files, cancellable=True)
        return [DriveFile(**f) for f in result.get("files", [])]
```

### Worker Processing

Worker uses async for database operations but wraps sync API calls:

```python
async def _process_job(self, job_id: str) -> None:
    async with get_async_session() as session:
        # Async database operations
        repo = QueueRepository(session)
        job = await repo.get_job(job_id)
        
        # Sync upload wrapped in run_sync
        result = await youtube_service.upload_from_drive_async(...)
```

---

## Dependency Injection Patterns

### Standard Pattern

```python
from fastapi import Depends
from app.core.dependencies import get_drive_service, get_user_id_from_session

@router.get("/files")
async def list_files(
    drive_service: DriveService = Depends(get_drive_service),
    user_id: str = Depends(get_user_id_from_session),
) -> list[DriveFile]:
    ...
```

### Chained Dependencies

Dependencies can depend on other dependencies:

```python
# In dependencies.py
def get_drive_service(
    credentials: Credentials = Depends(get_user_credentials),
) -> DriveService:
    return DriveService(credentials)

# get_user_credentials internally depends on session token
def get_user_credentials(
    session_token: str | None = Cookie(None, alias="session"),
) -> Credentials:
    ...
```

### Database Session Pattern

```python
from app.database import get_db

@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user_id_from_session),
) -> list[QueueJob]:
    repo = QueueRepository(db)
    return await repo.get_jobs_by_user(user_id)
```

---

## Repository Pattern

### Interface Definition (Protocol)

```python
# app/core/protocols.py
class QueueRepositoryProtocol(Protocol):
    async def add_job(self, job_create: "QueueJobCreate", user_id: str) -> "QueueJob":
        ...
    
    async def get_job(self, job_id: "UUID") -> "QueueJob | None":
        ...
```

### Implementation

```python
# app/queue/repositories.py
class QueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def add_job(self, job_create: QueueJobCreate, user_id: str) -> QueueJob:
        model = QueueJobModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            ...
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_schema(model)
    
    def _to_schema(self, model: QueueJobModel) -> QueueJob:
        return QueueJob(
            id=UUID(model.id),
            user_id=model.user_id,
            ...
        )
```

---

## Pydantic Schema Patterns

### Request/Response Schemas

```python
# app/queue/schemas.py
from pydantic import BaseModel, Field

class QueueJobCreate(BaseModel):
    """Request schema for creating a job."""
    drive_file_id: str = Field(..., description="Google Drive file ID")
    drive_file_name: str = Field(..., description="Display name")
    metadata: VideoMetadata = Field(..., description="YouTube metadata")

class QueueJob(BaseModel):
    """Response schema for a job."""
    id: UUID
    user_id: str
    status: JobStatus
    progress: float = Field(ge=0.0, le=100.0)
    # ...
    
    model_config = {"from_attributes": True}
```

### Enum Usage

```python
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

---

## Error Handling Patterns

### Custom Exceptions

```python
# app/exceptions.py
class CloudVidBridgeError(Exception):
    """Base exception for all app errors."""
    pass

class AuthenticationError(CloudVidBridgeError):
    """Raised when authentication fails."""
    pass

class QuotaExceededError(CloudVidBridgeError):
    """Raised when YouTube API quota is exceeded."""
    pass
```

### Route Error Handling

```python
from fastapi import HTTPException

@router.get("/file/{file_id}")
async def get_file(
    file_id: str,
    drive_service: DriveService = Depends(get_drive_service),
) -> DriveFile:
    try:
        return await drive_service.get_file_metadata(file_id)
    except DriveAPIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Not authenticated")
```

### Service Error Handling

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class YouTubeService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception(_is_retryable_error),
    )
    async def upload_video_async(self, ...):
        ...
```

---

## Singleton Patterns

### Module-Level Singleton

```python
# app/auth/oauth.py
_oauth_service: OAuthService | None = None

def get_oauth_service() -> OAuthService:
    """Get or create OAuthService singleton."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service
```

### Thread-Safe Singleton (with Lock)

```python
# app/youtube/quota.py
import threading

_quota_tracker: QuotaTracker | None = None
_lock = threading.Lock()

def get_quota_tracker() -> QuotaTracker:
    global _quota_tracker
    if _quota_tracker is None:
        with _lock:
            if _quota_tracker is None:
                _quota_tracker = QuotaTracker()
    return _quota_tracker
```

---

## Database Patterns

### Async Session Context

```python
from app.database import get_async_session

async with get_async_session() as session:
    repo = QueueRepository(session)
    job = await repo.get_job(job_id)
    # Session auto-closes after context
```

### Transaction Handling

```python
async def add_job(self, job_create: QueueJobCreate, user_id: str) -> QueueJob:
    try:
        model = QueueJobModel(...)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_schema(model)
    except Exception:
        await self.session.rollback()
        raise
```

### Query Patterns

```python
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

# Select with filter
stmt = select(QueueJobModel).where(
    QueueJobModel.user_id == user_id,
    QueueJobModel.status == "pending",
).order_by(QueueJobModel.created_at)
result = await self.session.execute(stmt)
jobs = result.scalars().all()

# Update with returning
stmt = (
    update(QueueJobModel)
    .where(QueueJobModel.id == job_id)
    .values(status=status, progress=progress)
    .returning(QueueJobModel)
)
result = await self.session.execute(stmt)
await self.session.commit()
```

---

## Naming Conventions

### Files

| Type | Pattern | Example |
|------|---------|---------|
| Routes | `routes.py` | `app/queue/routes.py` |
| Services | `service.py` or `services.py` | `app/youtube/service.py` |
| Repositories | `repositories.py` | `app/drive/repositories.py` |
| Schemas | `schemas.py` | `app/queue/schemas.py` |
| Dependencies | `dependencies.py` | `app/core/dependencies.py` |

### Classes

| Type | Pattern | Example |
|------|---------|---------|
| Service | `{Name}Service` | `DriveService`, `YouTubeService` |
| Repository | `{Name}Repository` | `QueueRepository` |
| Model (ORM) | `{Name}Model` or `{Name}` | `QueueJobModel`, `UploadHistory` |
| Schema | `{Name}`, `{Name}Create`, `{Name}Response` | `QueueJob`, `QueueJobCreate` |

### Functions

| Type | Pattern | Example |
|------|---------|---------|
| Dependency | `get_{name}` | `get_drive_service()`, `get_db()` |
| Route handler | Verb-based | `list_files()`, `create_job()` |
| Private method | `_method_name` | `_process_job()`, `_to_schema()` |

---

## Import Organization

```python
# Standard library
import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

# Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from pydantic import BaseModel

# Local application
from app.config import get_settings
from app.database import get_db
from app.core.dependencies import get_user_credentials
from app.queue.schemas import QueueJob, QueueJobCreate

# Type checking only imports
if TYPE_CHECKING:
    from app.youtube.service import YouTubeService
```

---

## Testing Patterns

### Async Test Functions

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_list_files():
    mock_drive = MagicMock(spec=DriveService)
    mock_drive.list_files = AsyncMock(return_value=[...])
    
    result = await mock_drive.list_files("folder_id")
    assert len(result) == 1
```

### Fixture Examples

```python
@pytest.fixture
def mock_credentials():
    return MagicMock(spec=Credentials)

@pytest.fixture
async def db_session():
    async with get_async_session() as session:
        yield session
        await session.rollback()
```
