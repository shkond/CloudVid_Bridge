---
trigger: always_on
---

# CloudVid Bridge

## WHAT (Technology & Structure)

**Stack**: Python 3.12 | FastAPI (async) | SQLAlchemy | SQLite/PostgreSQL | Google OAuth 2.0

**Key Directories**:
```
app/
├── main.py          # FastAPI entry point
├── config.py        # Settings (Pydantic)
├── models.py        # ORM models: QueueJobModel, OAuthToken, UploadHistory
├── core/            # DI (dependencies.py), Protocols (protocols.py)
├── auth/            # OAuth + session auth
├── drive/           # Google Drive API integration
├── youtube/         # YouTube upload + quota tracking
└── queue/           # Background worker + job queue
tests/               # pytest tests
docs/                # AI-readable documentation (see below)
```

**Database Tables**: `queue_jobs`, `oauth_tokens`, `upload_history`

---

## WHY (Purpose)

Upload videos from Google Drive to YouTube with:
- Persistent queue (survives restarts)
- Resumable uploads (large files)
- Duplicate detection (MD5-based)
- Multi-user support (per-user tokens)
- Background worker (separate process)

---

## HOW (Tests)

### Run Tests
```bash
pytest tests/ -v                          # All tests
pytest tests/ -v --cov=app               # With coverage
pytest tests/unit/ -v                     # Unit tests only
pytest tests/integration/ -v              # Integration tests only
```

### Lint & Format
```bash
ruff check app/
ruff format app/
```

---

## Documentation Pointers

For detailed information, read these files:

| File | Content |
|------|---------|
| [00_project_overview.md](./00_project_overview.md) | Full project structure, env vars, entry points |
| [01_architecture.md](./01_architecture.md) | Layered architecture, DB schema, auth flow diagrams |
| [02_modules.md](./02_modules.md) | All modules/classes/methods reference |
| [03_data_flow.md](./03_data_flow.md) | Upload pipeline, state machine, error handling |
| [04_conventions.md](./04_conventions.md) | Async patterns, DI, naming conventions, code examples |

---

## Quick Reference

**Key Dependencies (DI)**:
- `get_user_credentials()` → Google OAuth credentials
- `get_drive_service()` → DriveService instance
- `get_youtube_service()` → YouTubeService instance
- `get_queue_repository()` → QueueRepository with DB session

**Job Status Flow**: `pending` → `downloading` → `uploading` → `completed` (or `failed`/`cancelled`)

**Environment Variables**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`, `DATABASE_URL`, `AUTH_USERNAME`, `AUTH_PASSWORD`
