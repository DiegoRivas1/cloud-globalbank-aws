import pytest

from db import Database
from main import create_app


@pytest.fixture
def db(tmp_path):
    d = Database(sqlite_path=str(tmp_path / "test.db"))
    d.init_schema()
    return d


@pytest.fixture
def client(db):
    return create_app(db).test_client()
