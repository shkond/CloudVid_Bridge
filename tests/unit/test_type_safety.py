"""Tests for type safety and correct argument usage.

These tests prevent regressions for:
1. UUID type mismatch between PostgreSQL and SQLAlchemy
2. DriveService incorrect argument passing
"""

import inspect
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import String
from sqlalchemy.dialects import postgresql, sqlite


class TestGUIDTypeCrossDatabase:
    """Test GUID type works correctly across databases."""

    def test_guid_type_exists(self):
        """Verify GUID type is properly defined."""
        from app.types import GUID

        guid = GUID()
        assert guid is not None
        assert guid.cache_ok is True

    def test_guid_uses_native_uuid_for_postgresql(self):
        """GUID should use native UUID type for PostgreSQL.

        This prevents: 'operator does not exist: uuid = character varying'
        """
        from app.types import GUID

        guid = GUID()
        pg_dialect = postgresql.dialect()
        impl = guid.load_dialect_impl(pg_dialect)

        # The implementation should be PostgreSQL's UUID type
        assert impl is not None
        # Check it's using the PostgreSQL UUID type descriptor
        assert "UUID" in str(type(impl).__name__).upper()

    def test_guid_uses_string_for_sqlite(self):
        """GUID should use String(36) for SQLite."""
        from app.types import GUID

        guid = GUID()
        sqlite_dialect = sqlite.dialect()
        impl = guid.load_dialect_impl(sqlite_dialect)

        # The implementation should be String for SQLite
        assert impl is not None
        assert isinstance(impl, String) or "VARCHAR" in str(impl).upper()

    def test_guid_processes_uuid_to_string(self):
        """GUID should convert UUID objects to strings."""
        from app.types import GUID

        guid = GUID()
        test_uuid = uuid.uuid4()

        # Bind param should convert to string
        result = guid.process_bind_param(test_uuid, None)
        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_guid_processes_string_passthrough(self):
        """GUID should pass through string values."""
        from app.types import GUID

        guid = GUID()
        test_str = "550e8400-e29b-41d4-a716-446655440000"

        result = guid.process_bind_param(test_str, None)
        assert result == test_str

    def test_guid_processes_none(self):
        """GUID should handle None values."""
        from app.types import GUID

        guid = GUID()

        result = guid.process_bind_param(None, None)
        assert result is None

    def test_guid_result_always_string(self):
        """GUID result should always be string for consistency."""
        from app.types import GUID

        guid = GUID()

        # From string
        result1 = guid.process_result_value("test-uuid", None)
        assert isinstance(result1, str)

        # From UUID object
        test_uuid = uuid.uuid4()
        result2 = guid.process_result_value(test_uuid, None)
        assert isinstance(result2, str)

        # None stays None
        result3 = guid.process_result_value(None, None)
        assert result3 is None


class TestQueueJobModelUsesGUID:
    """Test QueueJobModel correctly uses GUID type."""

    def test_queue_job_model_id_uses_guid(self):
        """QueueJobModel.id should use GUID type, not String."""
        from app.models import QueueJobModel
        from app.types import GUID

        # Get the id column type
        id_column = QueueJobModel.__table__.columns["id"]

        # Should be using GUID type
        assert isinstance(id_column.type, GUID), (
            f"QueueJobModel.id should use GUID type, not {type(id_column.type)}. "
            "This causes 'uuid = character varying' error in PostgreSQL."
        )


class TestDriveServiceInitialization:
    """Test DriveService is initialized correctly.

    Prevents regression where credentials is passed as first positional
    argument and interpreted as repository.
    """

    def test_drive_service_constructor_signature(self):
        """Verify DriveService constructor has correct parameter order."""
        from app.drive.services import DriveService

        sig = inspect.signature(DriveService.__init__)
        params = list(sig.parameters.keys())

        # Should be: self, repository, credentials
        assert params[0] == "self"
        assert params[1] == "repository", (
            "First parameter after self should be 'repository'. "
            "This ensures named argument is required for credentials."
        )
        assert params[2] == "credentials"

    def test_drive_service_with_credentials_keyword(self):
        """DriveService should work with credentials as keyword argument."""
        from app.drive.services import DriveService

        mock_credentials = MagicMock()
        mock_credentials.token = "test_token"

        # This should work - using keyword argument
        service = DriveService(credentials=mock_credentials)

        assert service is not None
        # Repository should be DriveRepository, not the credentials
        assert hasattr(service._repository, "get_file_metadata"), (
            "_repository should have get_file_metadata method. "
            "If it's a Credentials object, this assertion fails."
        )

    def test_drive_service_with_repository(self):
        """DriveService should work with explicit repository."""
        from app.drive.services import DriveService

        mock_repo = MagicMock()

        service = DriveService(repository=mock_repo)

        assert service._repository is mock_repo

    def test_drive_service_requires_either_arg(self):
        """DriveService should require either repository or credentials."""
        from app.drive.services import DriveService

        with pytest.raises(ValueError, match="Either repository or credentials"):
            DriveService()


class TestWorkerDriveServiceUsage:
    """Test worker.py uses DriveService correctly."""

    def test_worker_uses_keyword_argument_for_drive_service(self):
        """Verify worker.py uses credentials= keyword argument."""
        from pathlib import Path

        worker_path = Path(__file__).parent.parent.parent / "app" / "queue" / "worker.py"
        content = worker_path.read_text()

        # Should use keyword argument
        assert "DriveService(credentials=credentials)" in content, (
            "worker.py should call DriveService(credentials=credentials), "
            "not DriveService(credentials) which passes credentials as repository."
        )

        # Should NOT have the buggy pattern (unless commented)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            # Skip comments
            if line.strip().startswith("#"):
                continue
            # Check for buggy pattern
            if "DriveService(credentials)" in line and "credentials=" not in line:
                pytest.fail(
                    f"Line {i+1}: Found 'DriveService(credentials)' without keyword. "
                    "This passes credentials as repository argument."
                )


class TestDependenciesDriveServiceUsage:
    """Test dependencies.py uses DriveService correctly."""

    def test_dependencies_uses_keyword_argument(self):
        """Verify dependencies.py uses credentials= keyword argument."""
        from pathlib import Path

        deps_path = Path(__file__).parent.parent.parent / "app" / "core" / "dependencies.py"
        content = deps_path.read_text()

        # Count correct vs incorrect usages
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("#"):
                continue
            if "DriveService(credentials)" in line and "credentials=" not in line:
                pytest.fail(
                    f"Line {i+1}: Found 'DriveService(credentials)' without keyword. "
                    "This passes credentials as repository argument."
                )
