# Architecture

## Layered Architecture

The application follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                      Routes Layer                           │
│    (app/*/routes.py - FastAPI route handlers)               │
├─────────────────────────────────────────────────────────────┤
│                     Service Layer                           │
│    (app/*/service.py - Business logic)                      │
├─────────────────────────────────────────────────────────────┤
│                   Repository Layer                          │
│    (app/*/repositories.py - Data access)                    │
├─────────────────────────────────────────────────────────────┤
│                     Model Layer                             │
│    (app/models.py - SQLAlchemy ORM models)                  │
├─────────────────────────────────────────────────────────────┤
│                   Database Layer                            │
│    (app/database.py - SQLAlchemy async engine)              │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### Routes Layer (`app/*/routes.py`)
- HTTP request/response handling
- Input validation via Pydantic schemas
- Dependency injection via FastAPI `Depends()`
- No business logic

### Service Layer (`app/*/service.py`, `app/*/services.py`)
- Business logic implementation
- Coordination between repositories
- External API interactions (Google APIs)
- Transaction management

### Repository Layer (`app/*/repositories.py`)
- Data access abstraction
- Database CRUD operations
- External API calls (wrapped)
- Implements protocols from `app/core/protocols.py`

### Model Layer (`app/models.py`)
- SQLAlchemy ORM model definitions
- Database schema
- No business logic

## Protocol-Based Design

Repository interfaces are defined as Protocols in `app/core/protocols.py`:

```python
# Example from protocols.py
class DriveRepositoryProtocol(Protocol):
    async def list_files(self, folder_id: str = "root", ...) -> list["DriveFile"]: ...
    async def get_file_metadata(self, file_id: str) -> dict[str, Any]: ...
    async def scan_folder(self, folder_id: str = "root", ...) -> "DriveFolder": ...

class YouTubeRepositoryProtocol(Protocol):
    def upload_video(self, file_stream, metadata, ...) -> "UploadResult": ...
    def get_channel_info(self) -> dict[str, Any]: ...
    def check_video_exists(self, video_id: str) -> bool: ...

class QueueRepositoryProtocol(Protocol):
    async def add_job(self, job_create, user_id) -> "QueueJob": ...
    async def get_job(self, job_id) -> "QueueJob | None": ...
    async def update_job_status(self, job_id, status, ...) -> "QueueJob | None": ...
```

## Dependency Injection

Dependencies are configured in `app/core/dependencies.py`:

```python
# Credential dependencies
def get_user_credentials(...) -> Credentials     # Requires auth
def get_optional_credentials(...) -> Credentials | None

# Service dependencies
def get_drive_service(credentials) -> DriveService
def get_youtube_service(credentials) -> YouTubeService

# Repository dependencies
def get_queue_repository(db: AsyncSession) -> QueueRepository
def get_queue_service(db: AsyncSession) -> QueueService

# Session dependencies
def get_session_data(...) -> dict | None
def require_session(...) -> dict  # Raises HTTPException
def get_user_id_from_session(...) -> str
```

## Authentication Flow

```
┌───────────┐     ┌─────────────┐     ┌────────────────┐     ┌─────────────┐
│   User    │────▶│ /auth/login │────▶│ Simple Auth    │────▶│   Session   │
│           │     │             │     │ (username/pwd) │     │   Cookie    │
└───────────┘     └─────────────┘     └────────────────┘     └──────┬──────┘
                                                                     │
                                                                     ▼
┌───────────┐     ┌───────────────┐     ┌────────────────┐     ┌───────────┐
│  Google   │◀────│ /auth/google  │◀────│   Dashboard    │◀────│ Protected │
│   OAuth   │     │               │     │   Page         │     │   Route   │
└─────┬─────┘     └───────────────┘     └────────────────┘     └───────────┘
      │
      ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ /auth/callback  │────▶│ OAuthService    │────▶│ Database        │
│                 │     │ save_token()    │     │ (encrypted)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Two-Phase Authentication

1. **App Authentication** (Simple Auth)
   - Username/password login
   - Creates session cookie
   - Grants access to dashboard

2. **Google OAuth** (for API access)
   - Initiated from dashboard
   - Stores encrypted tokens in database
   - Enables Drive/YouTube operations

## Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│                       OAuthToken                            │
├─────────────────────────────────────────────────────────────┤
│ id              │ INTEGER      │ Primary Key                │
│ user_id         │ VARCHAR(100) │ Unique, Indexed            │
│ encrypted_access_token  │ TEXT │ Fernet encrypted           │
│ encrypted_refresh_token │ TEXT │ Fernet encrypted           │
│ token_uri       │ VARCHAR(255) │ OAuth token endpoint       │
│ scopes          │ TEXT         │ JSON array                 │
│ expires_at      │ DATETIME     │ Token expiration           │
│ created_at      │ DATETIME     │ Auto-set                   │
│ updated_at      │ DATETIME     │ Auto-updated               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       QueueJobModel                         │
├─────────────────────────────────────────────────────────────┤
│ id              │ VARCHAR(36)  │ UUID Primary Key           │
│ user_id         │ VARCHAR(255) │ Owner, Indexed             │
│ drive_file_id   │ VARCHAR(255) │ Source file ID             │
│ drive_file_name │ VARCHAR(500) │ Display name               │
│ drive_md5_checksum │ VARCHAR(32) │ Duplicate detection      │
│ metadata_json   │ TEXT         │ VideoMetadata as JSON      │
│ status          │ VARCHAR(20)  │ Job status, Indexed        │
│ progress        │ FLOAT        │ 0.0 - 100.0                │
│ message         │ TEXT         │ Status message             │
│ video_id        │ VARCHAR(50)  │ Result YouTube ID          │
│ video_url       │ VARCHAR(255) │ Result YouTube URL         │
│ error           │ TEXT         │ Error message if failed    │
│ retry_count     │ INTEGER      │ Current retry count        │
│ max_retries     │ INTEGER      │ Max retry limit            │
│ created_at      │ DATETIME     │ Job creation time          │
│ started_at      │ DATETIME     │ Processing start           │
│ completed_at    │ DATETIME     │ Processing end             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                       UploadHistory                         │
├─────────────────────────────────────────────────────────────┤
│ id              │ INTEGER      │ Primary Key                │
│ drive_file_id   │ VARCHAR(255) │ Indexed                    │
│ drive_file_name │ VARCHAR(500) │ Original filename          │
│ drive_md5_checksum │ VARCHAR(32) │ Indexed, for dedup       │
│ youtube_video_id │ VARCHAR(50) │ Uploaded video ID          │
│ youtube_video_url │ VARCHAR(255) │ Video URL                │
│ youtube_etag    │ VARCHAR(100) │ For change detection       │
│ last_verified_at │ DATETIME    │ Last YouTube check         │
│ folder_path     │ TEXT         │ Source folder path         │
│ status          │ VARCHAR(20)  │ completed/failed           │
│ uploaded_at     │ DATETIME     │ Upload timestamp           │
│ created_at      │ DATETIME     │ Record creation            │
└─────────────────────────────────────────────────────────────┘
```

## Web and Worker Process Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              Web Process                                  │
│                         (uvicorn app.main:app)                           │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Auth Routes │  │ Drive Routes│  │YouTube Routes│  │ Queue Routes│     │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                             │            │
│                                                             ▼            │
│                                                    ┌─────────────────┐   │
│                                                    │    Database     │   │
│                                                    │ (queue_jobs)    │   │
│                                                    └────────┬────────┘   │
└─────────────────────────────────────────────────────────────┼────────────┘
                                                              │
                               Polls for pending jobs         │
                                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            Worker Process                                 │
│                     (python -m app.queue.worker)                         │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        QueueWorker                               │    │
│  │  ┌──────────────┐  ┌───────────────┐  ┌───────────────────┐    │    │
│  │  │ Poll DB Loop │─▶│ Process Job   │─▶│ Update Job Status │    │    │
│  │  └──────────────┘  └───────┬───────┘  └───────────────────┘    │    │
│  │                            │                                     │    │
│  │                   ┌────────┴────────┐                           │    │
│  │                   ▼                 ▼                           │    │
│  │          ┌─────────────┐   ┌─────────────┐                     │    │
│  │          │DriveService │   │YouTubeService                     │    │
│  │          │(download)   │   │(upload)     │                     │    │
│  │          └─────────────┘   └─────────────┘                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```
