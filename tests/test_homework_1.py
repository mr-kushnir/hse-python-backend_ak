"""Подразумевается, что при запуске тестов локально запущено приложение.

Адрес: localhost:8000
"""

from http import HTTPStatus
from typing import Any

import pytest
import requests

HOST = "localhost"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"


@pytest.fixture(scope="session")
def session():
    with requests.Session() as s:
        yield s


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("GET", "/not_found"),
        ("POST", "/"),
        ("POST", "/not_found"),
    ],
)
def test_not_found(session, method: str, path: str):
    response = session.request(method, BASE_URL + path)
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({"n": ""}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"n": "lol"}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"x": "kek"}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"n": -1}, HTTPStatus.BAD_REQUEST),
        ({"n": 0}, HTTPStatus.OK),
        ({"n": 1}, HTTPStatus.OK),
        ({"n": 10}, HTTPStatus.OK),
    ],
)
def test_factorial(session, query: dict[str, Any], status_code: int):
    response = session.get(BASE_URL + "/factorial", params=query)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        assert "result" in response.json()


@pytest.mark.parametrize(
    ("params", "status_code"),
    [
        ("/lol", HTTPStatus.UNPROCESSABLE_ENTITY),
        ("/-1", HTTPStatus.BAD_REQUEST),
        ("/0", HTTPStatus.OK),
        ("/1", HTTPStatus.OK),
        ("/10", HTTPStatus.OK),
    ],
)
def test_fibonacci(session, params: str, status_code: int):
    response = session.get(BASE_URL + "/fibonacci" + params)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        assert "result" in response.json()


@pytest.mark.parametrize(
    ("json_data", "status_code"),
    [
        (None, HTTPStatus.UNPROCESSABLE_ENTITY),
        ([], HTTPStatus.BAD_REQUEST),
        ([1, 2, 3], HTTPStatus.OK),
        ([1, 2.0, 3.0], HTTPStatus.OK),
        ([1.0, 2.0, 3.0], HTTPStatus.OK),
    ],
)
def test_mean(session, json_data: Any, status_code: int):
    response = session.get(BASE_URL + "/mean", json=json_data)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        assert "result" in response.json()
