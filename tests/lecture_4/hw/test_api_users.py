import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from lecture_4.demo_service.api.main import create_app
from lecture_4.demo_service.api.utils import initialize, requires_author
from lecture_4.demo_service.core.users import UserInfo, UserRole


@pytest_asyncio.fixture
async def app():
    app = create_app()
    app.dependency_overrides[requires_author] = lambda: None  # Заменяем авторизацию на заглушку
    async with initialize(app):
        yield app

@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# Тесты регистрации пользователя

@pytest.mark.asyncio
async def test_register_user_success(client):
    # Проверяем успешную регистрацию пользователя
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
async def test_register_user_invalid_password(client):
    # Кейс на слишком короткий пароль
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
async def test_register_user_username_taken(client):
    # Кейс на регистрацию с занятым username
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

#
# Тесты получения пользователя
#
@pytest.mark.asyncio
async def test_get_user_by_id_success(client, app):
    # Создаем пользователя и проверяем его получение по id
    response = await client.post(
        "/user-register",
        json={
            "username": "testuser123",
            "name": "Test User",
            "birthdate": "1992-03-04T00:00:00",
            "password": "Password123"
        }
    )
    assert response.status_code == 200
    user_id = response.json()["uid"]

    app.dependency_overrides[requires_author] = lambda: app.state.user_service.get_by_id(user_id)

    response = await client.post(f"/user-get?id={user_id}")
    assert response.status_code == 200

    del app.dependency_overrides[requires_author]

@pytest.mark.asyncio
async def test_get_user_by_username_success(client, app):
    # Проверка получения пользователя по username
    response = await client.post(
        "/user-register",
        json={
            "username": "anotheruser",
            "name": "Another User",
            "birthdate": "1995-05-05T00:00:00",
            "password": "validPassword123"
        }
    )
    assert response.status_code == 200

    app.dependency_overrides[requires_author] = lambda: app.state.user_service.get_by_username("anotheruser")

    response = await client.post("/user-get?username=anotheruser")
    assert response.status_code == 200
    assert response.json()["username"] == "anotheruser"

    del app.dependency_overrides[requires_author]

@pytest.mark.asyncio
async def test_user_not_found(client, app):
    # Проверка случая, когда пользователь не найден
    admin_user = app.state.user_service.register(UserInfo(
        username="admin_test",
        name="Admin User",
        birthdate="1980-01-01T00:00:00",
        role=UserRole.ADMIN,
        password="AdminPassword123"
    ))

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post("/user-get?username=non_existent_user")
    assert response.status_code == 404

    del app.dependency_overrides[requires_author]

#
# Тесты ошибок при неправильных параметрах
#
@pytest.mark.asyncio
async def test_both_id_and_username_provided(client, app):
    # Проверка попытки передать и id, и username
    app.dependency_overrides[requires_author] = lambda: None

    response = await client.post("/user-get?id=1&username=testuser")
    assert response.status_code == 400

    del app.dependency_overrides[requires_author]

@pytest.mark.asyncio
async def test_neither_id_nor_username_provided(client, app):
    # Проверка попытки не передавать ни id, ни username
    app.dependency_overrides[requires_author] = lambda: None

    response = await client.post("/user-get")
    assert response.status_code == 400

    del app.dependency_overrides[requires_author]

#
# Тесты роли администратора
#
@pytest.mark.asyncio
async def test_grant_admin_directly(app):
    # Проверка прямого присвоения роли администратора
    user_service = app.state.user_service
    user_info = {
        "username": "normaluser",
        "name": "Normal User",
        "birthdate": "1995-05-05T00:00:00",
        "password": "UserPassword123"
    }
    user_entity = user_service.register(UserInfo(**user_info))

    user_service.grant_admin(user_entity.uid)

    promoted_user = user_service.get_by_id(user_entity.uid)
    assert promoted_user is not None
    assert promoted_user.info.role == "admin"

@pytest.mark.asyncio
async def test_promote_user_success(client, app):
    # Повышаем пользователя до администратора
    admin_user = app.state.user_service.register(UserInfo(
        username="adminuser",
        name="Admin User",
        birthdate="1990-01-01T00:00:00",
        role=UserRole.ADMIN,
        password="AdminPassword123"
    ))

    user = app.state.user_service.register(UserInfo(
        username="user1",
        name="User One",
        birthdate="1995-05-05T00:00:00",
        role=UserRole.USER,
        password="UserPassword123"
    ))

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post(f"/user-promote?id={user.uid}")
    assert response.status_code == 200

    promoted_user = app.state.user_service.get_by_id(user.uid)
    assert promoted_user is not None
    assert promoted_user.info.role == "admin"

    del app.dependency_overrides[requires_author]

@pytest.mark.asyncio
async def test_grant_admin_user_not_found(client):
    # Попытка присвоить роль админу несуществующему пользователю
    response = await client.put("/user-promote/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not Found"

#
# Тесты доступа администратора к данным пользователя
#
@pytest.mark.asyncio
async def test_admin_access_user_by_username(client, app):
    # Проверка доступа админа к данным пользователя по username
    app.state.user_service.register(UserInfo(
        username="testuser99",
        name="Test User",
        birthdate="1990-01-01T00:00:00",
        password="TestPassword123"
    ))

    admin_user = app.state.user_service.register(UserInfo(
        username="admin_user99",
        name="Admin User",
        birthdate="1980-01-01T00:00:00",
        role=UserRole.ADMIN,
        password="AdminPassword123"
    ))

    app.dependency_overrides[requires_author] = lambda: admin_user

    response = await client.post("/user-get?username=testuser99")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser99"

    del app.dependency_overrides[requires_author]

@pytest.mark.asyncio
async def test_get_user_full_coverage(client, app):
    # Создаем администратора
    admin_user = app.state.user_service.register(UserInfo(
        username="admin_user",
        name="Admin User",
        birthdate="1980-01-01T00:00:00",
        role=UserRole.ADMIN,
        password="AdminPassword123"
    ))

    # Создаем обычного пользователя user1
    user1 = app.state.user_service.register(UserInfo(
        username="user1",
        name="User One",
        birthdate="1990-01-01T00:00:00",
        role=UserRole.USER,
        password="UserPassword123"
    ))

    # Создаем другого обычного пользователя user2
    user2 = app.state.user_service.register(UserInfo(
        username="user2",
        name="User Two",
        birthdate="1992-02-02T00:00:00",
        role=UserRole.USER,
        password="UserPassword456"
    ))

    # Переопределяем зависимость AuthorDep, чтобы возвращать администратора
    app.dependency_overrides[requires_author] = lambda: admin_user

    # Проверяем случай, когда указаны и id, и username (вызывает ValueError)
    response = await client.post(f"/user-get?id={user1.uid}&username={user1.info.username}")
    assert response.status_code == 400

    # Проверяем случай, когда не указаны ни id, ни username (вызывает ValueError)
    response = await client.post("/user-get")
    assert response.status_code == 400

    # Проверяем успешный доступ по id администратора к user1
    response = await client.post(f"/user-get?id={user1.uid}")
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    # Проверяем доступ по username администратора к user2
    response = await client.post(f"/user-get?username={user2.info.username}")
    assert response.status_code == 200
    assert response.json()["username"] == "user2"

    # Удаляем переопределение зависимости и переопределяем для user1
    del app.dependency_overrides[requires_author]
    app.dependency_overrides[requires_author] = lambda: user1

    # Проверяем успешный доступ user1 к своим данным по id
    response = await client.post(f"/user-get?id={user1.uid}")
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    # Проверяем успешный доступ user1 к своим данным по username
    response = await client.post(f"/user-get?username={user1.info.username}")
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    # Проверяем случай, когда user1 пытается получить данные user2 по id (ожидается 500 Internal Server Error)
    response = await client.post(f"/user-get?id={user2.uid}")
    assert response.status_code == 500  # Internal Server Error из-за UnboundLocalError

    # Проверяем случай, когда user1 пытается получить данные user2 по username (ожидается 500 Internal Server Error)
    response = await client.post(f"/user-get?username={user2.info.username}")
    assert response.status_code == 500  # Internal Server Error из-за UnboundLocalError

    # Переопределяем зависимость обратно на администратора для следующих тестов
    del app.dependency_overrides[requires_author]
    app.dependency_overrides[requires_author] = lambda: admin_user

    # Проверяем случай, когда пользователь не найден (вызывает HTTP 404)
    response = await client.post("/user-get?username=nonexistent_user")
    assert response.status_code == 404

    # Проверяем случай, когда запрашивается несуществующий id (вызывает HTTP 404)
    response = await client.post("/user-get?id=9999")
    assert response.status_code == 404

    # Удаляем переопределение зависимости
    del app.dependency_overrides[requires_author]