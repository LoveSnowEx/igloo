"""Igloo 測試共用 fixtures。"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///test_igloo.db"


@pytest.fixture(name="client")
def client_fixture() -> Generator[TestClient]:
    """FastAPI TestClient。"""
    from app.main import app

    with TestClient(app) as c:
        yield c
