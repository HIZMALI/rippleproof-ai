import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from rippleproof.app import create_app
from rippleproof.config import Settings
from rippleproof.errors import DatabaseUnavailable, GraphQueryError
from rippleproof.repository import GraphRepository
from rippleproof.seed_data import build_dataset


@pytest.fixture
def empty_repository():
    # Separate graph per test; never delete or mutate the user's rippleproof graph.
    settings = Settings(graph=f"test_rippleproof_{uuid4().hex}")
    repository = GraphRepository(settings)
    try:
        repository.ready()
    except (DatabaseUnavailable, GraphQueryError) as exc:
        pytest.fail(
            f"Real FalkorDB is required; start docker compose first: {exc!r}", pytrace=False
        )
    try:
        yield repository
    finally:
        assert settings.graph.startswith("test_rippleproof_")
        if os.environ.get("RIPPLEPROOF_RETAIN_TEST_GRAPHS") != "1":
            with repository.connect() as db:
                if settings.graph in db.list_graphs():
                    db.select_graph(settings.graph).delete()


@pytest.fixture
def repository(empty_repository):
    empty_repository.seed(build_dataset())
    return empty_repository


@pytest.fixture
def client(repository):
    with TestClient(create_app(repository.settings)) as client:
        yield client
