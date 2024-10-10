import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from lecture_4.demo_service.api.main import create_app
from lecture_4.demo_service.api.utils import initialize, requires_author, AdminDep

@pytest_asyncio.fixture
async def client():
    app = create_app()
    app.dependency_overrides[requires_author] = lambda: None
    # Инициализируем user_service
    async with initialize(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

@pytest.mark.asyncio
async def test_register_user_success(client):
    response = await client.post(
        "/user-register",
        json={
            "username": "testuser",
            "name": "Test User",
            "birthdate": "2000-01-01T00:00:00",
            "password": "validPassword123"
        }
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

@pytest.mark.asyncio
async def test_get_user_by_id(client):
    # Попытка получить несуществующего пользователя
    response = await client.get("/user-get/999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_promote_user_to_admin(client):
    # Попытка присвоить роль админа несуществующему пользователю
    response = await client.put("/user-promote/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"

@pytest.mark.asyncio
async def test_get_user_both_id_and_username(client):
    # Если требуется авторизация, добавь заголовок Authorization
    response = await client.post("/user-get?id=1&username=testuser", headers={"Authorization": "Bearer testtoken"})
    assert response.status_code in [400, 405, 401]  # Проверяем несколько возможных вариантов

@pytest.mark.asyncio
async def test_get_user_neither_id_nor_username(client):
    response = await client.post("/user-get", headers={"Authorization": "Bearer testtoken"})
    assert response.status_code in [400, 405, 401]  # Проверяем несколько возможных вариантов


@pytest.mark.asyncio
async def test_promote_user_not_found(client):
    response = await client.put("/user-promote/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"


@pytest.mark.asyncio
async def test_register_user_username_taken(client):
    # Регистрация пользователя с именем, которое уже занято
    await client.post(
        "/user-register",
        json={
            "username": "testuser",
            "name": "Test User",
            "birthdate": "2000-01-01T00:00:00",
            "password": "validPassword123"
        }
    )
    response = await client.post(
        "/user-register",
        json={
            "username": "testuser",
            "name": "Another User",
            "birthdate": "1990-01-01T00:00:00",
            "password": "validPassword123"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "username is already taken"

@pytest.mark.asyncio
async def test_register_user_invalid_password(client):
    # Попытка зарегистрировать пользователя с коротким паролем
    response = await client.post(
        "/user-register",
        json={
            "username": "newuser",
            "name": "New User",
            "birthdate": "1995-05-05T00:00:00",
            "password": "short"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid password"

@pytest.mark.asyncio
async def test_grant_admin_user_not_found(client):
    # Присвоение админской роли несуществующему пользователю
    response = await client.put("/user-promote/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"

@pytest.mark.asyncio
async def test_get_user_both_id_and_username_provided(client):
    response = await client.post(
        "/user-get?id=1&username=testuser"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "both id and username are provided"

@pytest.mark.asyncio
async def test_get_user_neither_id_nor_username_provided(client):
    response = await client.post(
        "/user-get"
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "neither id nor username are provided"



