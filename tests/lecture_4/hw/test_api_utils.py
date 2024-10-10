import pytest
from http import HTTPStatus
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from lecture_4.demo_service.api.utils import (
    initialize,
    user_service,
    requires_author,
    requires_admin,
    value_error_handler,
)
from lecture_4.demo_service.core.users import UserService, UserInfo, UserRole
from fastapi.security import HTTPBasicCredentials
from datetime import datetime
from starlette.requests import Request
from starlette.responses import JSONResponse

@pytest.fixture
def app():
    app = FastAPI()
    # Инициализируем user_service в app.state
    app.state.user_service = UserService(password_validators=[])
    return app

@pytest.fixture
async def setup_user_service(app: FastAPI):
    async with initialize(app):
        yield

def test_user_service(setup_user_service, app):
    # Создаем объект Request
    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    assert isinstance(service, UserService)

def test_requires_author(setup_user_service, app):
    # Тестируем requires_author
    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    service.register(UserInfo(
        username="user",
        name="User Name",
        birthdate=datetime(2000, 1, 1),
        role=UserRole.USER,
        password="Password123",
    ))
    credentials = HTTPBasicCredentials(username="user", password="Password123")
    user_entity = requires_author(credentials, service)
    assert user_entity.info.username == "user"

    # Проверка неправильного пароля
    credentials = HTTPBasicCredentials(username="user", password="WrongPassword")
    with pytest.raises(HTTPException) as exc_info:
        requires_author(credentials, service)
    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED

    # Проверка несуществующего пользователя
    credentials = HTTPBasicCredentials(username="nonexistent", password="Password123")
    with pytest.raises(HTTPException) as exc_info:
        requires_author(credentials, service)
    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED

def test_requires_admin(setup_user_service, app):
    # Тестируем requires_admin
    request = Request(scope={"type": "http", "app": app})
    service = user_service(request)
    admin_info = UserInfo(
        username="admin",
        name="Admin User",
        birthdate=datetime(1990, 1, 1),
        role=UserRole.ADMIN,
        password="AdminPassword123",
    )
    admin_entity = service.register(admin_info)

    # Проверяем администратора
    admin = requires_admin(admin_entity)
    assert admin.info.username == "admin"

    # Проверка для обычного пользователя
    user_info = UserInfo(
        username="user",
        name="Regular User",
        birthdate=datetime(2000, 1, 1),
        role=UserRole.USER,
        password="UserPassword123",
    )
    user_entity = service.register(user_info)
    with pytest.raises(HTTPException) as exc_info:
        requires_admin(user_entity)
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN

@pytest.mark.asyncio
async def test_value_error_handler():
    app = FastAPI()
    # Создаем объект Request
    request = Request(scope={"type": "http", "method": "GET", "path": "/"})
    response = await value_error_handler(request, ValueError("Test error"))
    assert response.status_code == HTTPStatus.BAD_REQUEST
    # Получаем содержимое ответа
    response_content = response.body.decode()
    assert "Test error" in response_content
