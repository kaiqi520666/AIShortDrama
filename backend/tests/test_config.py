import pytest

from app.core.config import validate_test_database_url


def test_test_database_url_must_be_isolated():
    primary = "postgresql+asyncpg://user:secret@localhost/app"
    test_url = "postgresql+asyncpg://user:secret@localhost/app_test"

    assert validate_test_database_url(primary, test_url) == test_url

    with pytest.raises(ValueError, match="不能与业务数据库相同"):
        validate_test_database_url(primary, primary)
    with pytest.raises(ValueError, match="必须包含 test"):
        validate_test_database_url(primary, "postgresql+asyncpg://user:secret@localhost/staging")
