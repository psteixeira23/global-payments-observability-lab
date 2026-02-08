from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient


@contextmanager
def create_test_client(
    app: FastAPI,
    *,
    raise_server_exceptions: bool = True,
) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=raise_server_exceptions) as client:
        yield client
