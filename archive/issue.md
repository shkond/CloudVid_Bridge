500エラーの原因を特定しました。/drive/filesエンドポイントでは、ユーザーIDが必要ですが、コードに問題があります。

問題点
app/drive/service.pyのget_drive_service()関数を見ると:

python
def get_drive_service() -> DriveService:
    oauth_service = get_oauth_service()
    credentials = oauth_service.get_credentials()  # ← user_idが渡されていない
しかし、oauth.pyのget_credentials()メソッドは必須パラメータとしてuser_idを要求しています:

python
async def get_credentials(self, user_id: str) -> Credentials | None:
解決方法
app/drive/routes.pyのlist_filesエンドポイントを修正する必要があります:

python
@router.get("/files", response_model=list[DriveFile])
async def list_files(
    folder_id: str = Query(default="root", description="Drive folder ID"),
    video_only: bool = Query(default=True, description="Filter to video files only"),
    session_token: str | None = Cookie(None, alias="session"),  # 追加
) -> list[DriveFile]:
    """List files in a Drive folder."""
    try:
        # セッションからuser_idを取得
        session_data = check_app_auth(session_token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        user_id = get_current_user_from_session(session_data)
        
        # user_idを渡してDriveサービスを取得
        oauth_service = get_oauth_service()
        credentials = await oauth_service.get_credentials(user_id)
        if not credentials:
            raise ValueError("Not authenticated with Google")
        
        from app.drive.service import DriveService
        service = DriveService(credentials)
        return service.list_files(folder_id, video_only)

Redefining name 'test_engine' from outer scope (line 32)
tests/conftest.py

Ignore


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        bind=test_engine,
Redefining name 'status' from outer scope (line 5)
app/queue/routes.py

Ignore
    jobs = await QueueManagerDB.get_jobs_by_user(db, user_id)
    # Sort by created_at (newest first)
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    status = await QueueManagerDB.get_status(db, user_id=user_id)
    return QueueListResponse(jobs=jobs, status=status)

Redefining name 'app' from outer scope (line 118)
app/main.py

Ignore
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "FastAPI backend for uploading videos from Google Drive to YouTube. "
Redefining name 'settings' from outer scope (line 123)
app/main.py

Ignore
    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
Redefining name 'settings' from outer scope (line 123)
app/main.py

Ignore
    """
    # Startup
    logger.info("Starting application...")
    settings = get_settings()
    logger.info("App: %s, Environment: %s", settings.app_name, settings.app_env)

    # Initialize database

Redefining name 'app' from outer scope (line 118)
app/main.py

Ignore


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.

    